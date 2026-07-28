import json
import random
import time
from pathlib import Path

import discord
from redbot.core import Config, commands
from redbot.core.bot import Red

PAGE_SIZE = 25
FALLBACK_COLOR = 0x2F3136
VALID_PAGE_IMAGE_KEYS = {
    "menu", "fish", "travel", "shop", "leaderboard",
    "fishpedia", "quests", "inventory", "profile",
}


async def finish_transition(interaction: discord.Interaction, item: discord.ui.Item, embed: discord.Embed, view: discord.ui.View):
    await interaction.response.edit_message(embed=embed, view=view)
    view.message = interaction.message
    old_view = item.view
    if old_view is not None and old_view is not view:
        old_view.stop()


class DataManager:
    def __init__(self, data_path: Path):
        self.data_path = data_path
        self.rarities = {}
        self.areas = {}
        self.boats = {}
        self.items = {}
        self.fish = {}
        self.quests = {}
        self.reload()

    def reload(self):
        self.rarities = self._load("rarities.json")
        self.areas = self._load("areas.json")
        self.boats = self._load("boats.json")
        self.items = self._load("items.json")
        self.fish = self._load("fish.json")
        self.quests = self._load("quests.json")

    def _load(self, filename):
        path = self.data_path / filename
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
        return {entry["id"]: entry for entry in raw}

    def sorted_areas(self):
        return sorted(self.areas.values(), key=lambda a: a.get("order", 0))

    def area_fish(self, area_id):
        return [f for f in self.fish.values() if area_id in f.get("areas", [])]

    def roll_fish(self, area_id, luck_boost=0.0):
        candidates = self.area_fish(area_id)
        if not candidates:
            return None
        weights = []
        for entry in candidates:
            rarity = self.rarities.get(entry["rarity"], {"weight": 1})
            weight = rarity.get("weight", 1)
            if luck_boost and weight <= 25:
                weight = weight * (1 + luck_boost)
            weights.append(max(weight, 0.01))
        return random.choices(candidates, weights=weights, k=1)[0]

    def rarity_color(self, rarity_id):
        rarity = self.rarities.get(rarity_id)
        if not rarity:
            return FALLBACK_COLOR
        return rarity.get("color", FALLBACK_COLOR)

    def rarity_name(self, rarity_id):
        rarity = self.rarities.get(rarity_id)
        if not rarity:
            return str(rarity_id).title()
        return rarity.get("name", str(rarity_id).title())

    def rarity_emoji(self, rarity_id):
        rarity = self.rarities.get(rarity_id)
        if not rarity:
            return ""
        return rarity.get("emoji", "")


class BaseFishView(discord.ui.View):
    def __init__(self, cog, member, timeout=180):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.member = member
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.member.id:
            await interaction.response.send_message(
                "This menu isn't for you. Run the command yourself to get your own!",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self):
        if self.message is None:
            return
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.HTTPException:
            pass


class BackButton(discord.ui.Button):
    def __init__(self, target_builder, label="Back", row=4):
        super().__init__(label=label, style=discord.ButtonStyle.grey, emoji="↩️", row=row)
        self.target_builder = target_builder

    async def callback(self, interaction: discord.Interaction):
        embed, view = await self.target_builder()
        await finish_transition(interaction, self, embed, view)


class PageNavButton(discord.ui.Button):
    def __init__(self, builder, page, total_pages, delta, row=3):
        target = page + delta
        label = "◀ Prev" if delta < 0 else "Next ▶"
        disabled = target < 0 or target >= total_pages
        super().__init__(label=label, style=discord.ButtonStyle.blurple, disabled=disabled, row=row)
        self.builder = builder
        self.target = target

    async def callback(self, interaction: discord.Interaction):
        embed, view = await self.builder(self.target)
        await finish_transition(interaction, self, embed, view)


class SimplePagedView(BaseFishView):
    def __init__(self, cog, member, back_to, page, total_pages, builder):
        super().__init__(cog, member)
        if total_pages > 1:
            self.add_item(PageNavButton(builder, page, total_pages, -1))
            self.add_item(PageNavButton(builder, page, total_pages, 1))
        self.add_item(BackButton(back_to))


class MainMenuSelect(discord.ui.Select):
    def __init__(self, cog):
        options = [
            discord.SelectOption(label="Fish", value="fish", emoji="🎣", description="Cast your line and try to catch something"),
            discord.SelectOption(label="Travel", value="travel", emoji="🧭", description="Sail to a different fishing area"),
            discord.SelectOption(label="Shop", value="shop", emoji="🛒", description="Buy boats and items, or sell fish"),
            discord.SelectOption(label="Leaderboard", value="leaderboard", emoji="🏆", description="See the top anglers"),
            discord.SelectOption(label="Fishpedia", value="fishpedia", emoji="📖", description="Browse every fish and your catches"),
            discord.SelectOption(label="Quests", value="quests", emoji="📜", description="Take on quests from local NPCs"),
            discord.SelectOption(label="Inventory", value="inventory", emoji="🎒", description="View your fish, items and boats"),
            discord.SelectOption(label="Profile", value="profile", emoji="👤", description="View your angler profile"),
        ]
        super().__init__(placeholder="What would you like to do?", options=options, min_values=1, max_values=1, row=0)
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        await self.cog.dispatch_menu(interaction, self.values[0], self)


class MainMenuView(BaseFishView):
    def __init__(self, cog, member):
        super().__init__(cog, member)
        self.add_item(MainMenuSelect(cog))


class FishAgainButton(discord.ui.Button):
    def __init__(self, cog, member, back_to):
        super().__init__(label="Fish Again", style=discord.ButtonStyle.green, emoji="🎣", row=0)
        self.cog = cog
        self.member = member
        self.back_to = back_to

    async def callback(self, interaction: discord.Interaction):
        embed, view = await self.cog.build_fish_page(self.member, interaction.guild, back_to=self.back_to)
        await finish_transition(interaction, self, embed, view)


class FishActionView(BaseFishView):
    def __init__(self, cog, member, back_to):
        super().__init__(cog, member)
        self.add_item(FishAgainButton(cog, member, back_to))
        self.add_item(BackButton(back_to))


class TravelSelect(discord.ui.Select):
    def __init__(self, cog, member, guild, areas_chunk, page, back_to):
        options = []
        for area in areas_chunk:
            description = (area.get("description") or "")[:95] or None
            options.append(discord.SelectOption(label=area["name"][:100], value=area["id"], description=description))
        super().__init__(placeholder="Choose an area to travel to...", options=options, min_values=1, max_values=1, row=0)
        self.cog = cog
        self.member = member
        self.guild = guild
        self.page = page
        self.back_to = back_to

    async def callback(self, interaction: discord.Interaction):
        area_id = self.values[0]
        result_message = await self.cog.travel_to(self.member, area_id)
        embed, view = await self.cog.build_travel_page(self.member, self.guild, page=self.page, back_to=self.back_to)
        embed.insert_field_at(0, name="Travel Result", value=result_message, inline=False)
        await finish_transition(interaction, self, embed, view)


class TravelView(BaseFishView):
    def __init__(self, cog, member, guild, chunk, page, total_pages, back_to):
        super().__init__(cog, member)
        if chunk:
            self.add_item(TravelSelect(cog, member, guild, chunk, page, back_to))

        if total_pages > 1:
            def builder(new_page):
                return cog.build_travel_page(member, guild, page=new_page, back_to=back_to)

            self.add_item(PageNavButton(builder, page, total_pages, -1))
            self.add_item(PageNavButton(builder, page, total_pages, 1))
        self.add_item(BackButton(back_to))


class ShopHomeSelect(discord.ui.Select):
    def __init__(self, cog, member, guild, back_to):
        options = [
            discord.SelectOption(label="Buy Boats", value="boats", emoji="⛵"),
            discord.SelectOption(label="Buy Items", value="items", emoji="🎒"),
            discord.SelectOption(label="Sell Fish", value="sell", emoji="💰"),
        ]
        super().__init__(placeholder="Choose a shop category...", options=options, min_values=1, max_values=1, row=0)
        self.cog = cog
        self.member = member
        self.guild = guild
        self.back_to = back_to

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]

        def home_back():
            return self.cog.build_shop_home(self.member, self.guild, back_to=self.back_to)

        embed, view = await self.cog.build_shop_list(self.member, self.guild, category, page=0, back_to=home_back)
        await finish_transition(interaction, self, embed, view)


class ShopHomeView(BaseFishView):
    def __init__(self, cog, member, guild, back_to):
        super().__init__(cog, member)
        self.add_item(ShopHomeSelect(cog, member, guild, back_to))
        self.add_item(BackButton(back_to))


class ShopSelect(discord.ui.Select):
    def __init__(self, cog, member, guild, category, chunk, page, back_to):
        options = []
        for entry in chunk:
            if category == "sell":
                price = entry.get("value", 0)
                description = f"Sells for {price} FishCoins each"
            else:
                price = entry.get("price", 0)
                description = f"{price} FishCoins"
            options.append(discord.SelectOption(label=entry["name"][:100], value=entry["id"], description=description[:95]))
        super().__init__(placeholder="Select an item...", options=options, min_values=1, max_values=1, row=0)
        self.cog = cog
        self.member = member
        self.guild = guild
        self.category = category
        self.page = page
        self.back_to = back_to

    async def callback(self, interaction: discord.Interaction):
        entry_id = self.values[0]

        def list_back():
            return self.cog.build_shop_list(self.member, self.guild, self.category, page=self.page, back_to=self.back_to)

        embed, view = await self.cog.build_shop_detail(self.member, self.guild, self.category, entry_id, back_to=list_back)
        await finish_transition(interaction, self, embed, view)


class ShopListView(BaseFishView):
    def __init__(self, cog, member, guild, category, chunk, page, total_pages, back_to):
        super().__init__(cog, member)
        if chunk:
            self.add_item(ShopSelect(cog, member, guild, category, chunk, page, back_to))

        if total_pages > 1:
            def builder(new_page):
                return cog.build_shop_list(member, guild, category, page=new_page, back_to=back_to)

            self.add_item(PageNavButton(builder, page, total_pages, -1))
            self.add_item(PageNavButton(builder, page, total_pages, 1))
        self.add_item(BackButton(back_to))


class BuyBoatButton(discord.ui.Button):
    def __init__(self, cog, member, guild, boat, back_to):
        super().__init__(label=f"Buy {boat['name']}"[:80], style=discord.ButtonStyle.green, emoji="🪙", row=0)
        self.cog = cog
        self.member = member
        self.guild = guild
        self.boat = boat
        self.back_to = back_to

    async def callback(self, interaction: discord.Interaction):
        success, message = await self.cog.buy_boat(self.member, self.boat["id"])
        embed, view = await self.cog.build_shop_detail(self.member, self.guild, "boats", self.boat["id"], back_to=self.back_to)
        embed.insert_field_at(0, name="Result", value=message, inline=False)
        await finish_transition(interaction, self, embed, view)


class BuyItemButton(discord.ui.Button):
    def __init__(self, cog, member, guild, item, back_to):
        super().__init__(label=f"Buy {item['name']}"[:80], style=discord.ButtonStyle.green, emoji="🪙", row=0)
        self.cog = cog
        self.member = member
        self.guild = guild
        self.item = item
        self.back_to = back_to

    async def callback(self, interaction: discord.Interaction):
        success, message = await self.cog.buy_item(self.member, self.item["id"])
        embed, view = await self.cog.build_shop_detail(self.member, self.guild, "items", self.item["id"], back_to=self.back_to)
        embed.insert_field_at(0, name="Result", value=message, inline=False)
        await finish_transition(interaction, self, embed, view)


class SellFishButton(discord.ui.Button):
    def __init__(self, cog, member, guild, fish, back_to, all_fish):
        label = "Sell All" if all_fish else "Sell 1"
        style = discord.ButtonStyle.blurple if all_fish else discord.ButtonStyle.green
        super().__init__(label=label, style=style, emoji="💰", row=0)
        self.cog = cog
        self.member = member
        self.guild = guild
        self.fish = fish
        self.back_to = back_to
        self.all_fish = all_fish

    async def callback(self, interaction: discord.Interaction):
        user_conf = self.cog.config.user(self.member)
        inventory = await user_conf.inventory_fish()
        owned = inventory.get(self.fish["id"], 0)
        amount = owned if self.all_fish else 1
        total = await self.cog.sell_fish(self.member, self.fish["id"], amount)
        embed, view = await self.cog.build_shop_detail(self.member, self.guild, "sell", self.fish["id"], back_to=self.back_to)
        if total > 0:
            result = f"Sold {amount}x {self.fish['name']} for {self.cog.format_currency(total)}."
        else:
            result = f"You don't have any {self.fish['name']} to sell."
        embed.insert_field_at(0, name="Result", value=result, inline=False)
        await finish_transition(interaction, self, embed, view)


class ShopDetailView(BaseFishView):
    def __init__(self, cog, member, guild, category, entry, back_to, owned=False):
        super().__init__(cog, member)
        if category == "boats":
            if not owned:
                self.add_item(BuyBoatButton(cog, member, guild, entry, back_to))
        elif category == "items":
            self.add_item(BuyItemButton(cog, member, guild, entry, back_to))
        else:
            self.add_item(SellFishButton(cog, member, guild, entry, back_to, all_fish=False))
            self.add_item(SellFishButton(cog, member, guild, entry, back_to, all_fish=True))
        self.add_item(BackButton(back_to))


class FishpediaSelect(discord.ui.Select):
    def __init__(self, cog, member, guild, chunk, page, back_to):
        options = []
        for fish in chunk:
            description = (fish.get("description") or "")[:95] or None
            options.append(discord.SelectOption(label=fish["name"][:100], value=fish["id"], description=description))
        super().__init__(placeholder="View a fish...", options=options, min_values=1, max_values=1, row=0)
        self.cog = cog
        self.member = member
        self.guild = guild
        self.page = page
        self.back_to = back_to

    async def callback(self, interaction: discord.Interaction):
        fish_id = self.values[0]

        def list_back():
            return self.cog.build_fishpedia_list(self.member, self.guild, page=self.page, back_to=self.back_to)

        embed, view = await self.cog.build_fishpedia_detail(self.member, self.guild, fish_id, back_to=list_back)
        await finish_transition(interaction, self, embed, view)


class FishpediaListView(BaseFishView):
    def __init__(self, cog, member, guild, chunk, page, total_pages, back_to):
        super().__init__(cog, member)
        if chunk:
            self.add_item(FishpediaSelect(cog, member, guild, chunk, page, back_to))

        if total_pages > 1:
            def builder(new_page):
                return cog.build_fishpedia_list(member, guild, page=new_page, back_to=back_to)

            self.add_item(PageNavButton(builder, page, total_pages, -1))
            self.add_item(PageNavButton(builder, page, total_pages, 1))
        self.add_item(BackButton(back_to))


class QuestToggleButton(discord.ui.Button):
    def __init__(self, cog, member, guild, back_to, mine, row=3):
        label = "Area Quests" if mine else "My Quests"
        super().__init__(label=label, style=discord.ButtonStyle.grey, emoji="📌", row=row)
        self.cog = cog
        self.member = member
        self.guild = guild
        self.back_to = back_to
        self.mine = mine

    async def callback(self, interaction: discord.Interaction):
        embed, view = await self.cog.build_quests_list(self.member, self.guild, page=0, back_to=self.back_to, mine=not self.mine)
        await finish_transition(interaction, self, embed, view)


class QuestSelect(discord.ui.Select):
    def __init__(self, cog, member, guild, chunk, page, back_to, mine):
        options = []
        for quest in chunk:
            description = (quest.get("description") or "")[:95] or None
            options.append(discord.SelectOption(label=quest["name"][:100], value=quest["id"], description=description))
        super().__init__(placeholder="View a quest...", options=options, min_values=1, max_values=1, row=0)
        self.cog = cog
        self.member = member
        self.guild = guild
        self.page = page
        self.back_to = back_to
        self.mine = mine

    async def callback(self, interaction: discord.Interaction):
        quest_id = self.values[0]

        def list_back():
            return self.cog.build_quests_list(self.member, self.guild, page=self.page, back_to=self.back_to, mine=self.mine)

        embed, view = await self.cog.build_quest_detail(self.member, self.guild, quest_id, back_to=list_back)
        await finish_transition(interaction, self, embed, view)


class QuestsListView(BaseFishView):
    def __init__(self, cog, member, guild, chunk, page, total_pages, back_to, mine):
        super().__init__(cog, member)
        if chunk:
            self.add_item(QuestSelect(cog, member, guild, chunk, page, back_to, mine))

        if total_pages > 1:
            def builder(new_page):
                return cog.build_quests_list(member, guild, page=new_page, back_to=back_to, mine=mine)

            self.add_item(PageNavButton(builder, page, total_pages, -1))
            self.add_item(PageNavButton(builder, page, total_pages, 1))
        self.add_item(QuestToggleButton(cog, member, guild, back_to, mine))
        self.add_item(BackButton(back_to))


class AcceptQuestButton(discord.ui.Button):
    def __init__(self, cog, member, guild, quest, back_to):
        super().__init__(label="Accept Quest", style=discord.ButtonStyle.green, emoji="✅", row=0)
        self.cog = cog
        self.member = member
        self.guild = guild
        self.quest = quest
        self.back_to = back_to

    async def callback(self, interaction: discord.Interaction):
        user_conf = self.cog.config.user(self.member)
        async with user_conf.active_quests() as active:
            active[self.quest["id"]] = {"progress": 0}
        embed, view = await self.cog.build_quest_detail(self.member, self.guild, self.quest["id"], back_to=self.back_to)
        embed.insert_field_at(0, name="Result", value="Quest accepted!", inline=False)
        await finish_transition(interaction, self, embed, view)


class TurnInQuestButton(discord.ui.Button):
    def __init__(self, cog, member, guild, quest, back_to):
        super().__init__(label="Turn In", style=discord.ButtonStyle.blurple, emoji="🎁", row=0)
        self.cog = cog
        self.member = member
        self.guild = guild
        self.quest = quest
        self.back_to = back_to

    async def callback(self, interaction: discord.Interaction):
        message = await self.cog.turn_in_quest(self.member, self.quest["id"])
        embed, view = await self.cog.build_quest_detail(self.member, self.guild, self.quest["id"], back_to=self.back_to)
        embed.insert_field_at(0, name="Result", value=message, inline=False)
        await finish_transition(interaction, self, embed, view)


class QuestDetailView(BaseFishView):
    def __init__(self, cog, member, guild, quest, state, completed, back_to):
        super().__init__(cog, member)
        if state and state["progress"] >= quest["amount"]:
            self.add_item(TurnInQuestButton(cog, member, guild, quest, back_to))
        elif not state and (quest["id"] not in completed or quest.get("repeatable")):
            self.add_item(AcceptQuestButton(cog, member, guild, quest, back_to))
        self.add_item(BackButton(back_to))


class EquipSelect(discord.ui.Select):
    def __init__(self, cog, member, guild, equip_options, back_to, page, builder):
        options = [discord.SelectOption(label="Unequip current item", value="__unequip__", emoji="🚫")]
        for item_id, item in equip_options:
            options.append(discord.SelectOption(label=f"Equip {item['name']}"[:100], value=item_id, emoji="🎒"))
        super().__init__(placeholder="Equip or unequip an item...", options=options[:25], min_values=1, max_values=1, row=0)
        self.cog = cog
        self.member = member
        self.guild = guild
        self.back_to = back_to
        self.page = page
        self.builder = builder

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        user_conf = self.cog.config.user(self.member)
        if value == "__unequip__":
            await user_conf.equipped_item.set(None)
        else:
            await user_conf.equipped_item.set(value)
        embed, view = await self.builder(self.page)
        await finish_transition(interaction, self, embed, view)


class InventoryView(BaseFishView):
    def __init__(self, cog, member, guild, back_to, page, total_pages, builder, equip_options):
        super().__init__(cog, member)
        if equip_options:
            self.add_item(EquipSelect(cog, member, guild, equip_options, back_to, page, builder))

        if total_pages > 1:
            self.add_item(PageNavButton(builder, page, total_pages, -1))
            self.add_item(PageNavButton(builder, page, total_pages, 1))
        self.add_item(BackButton(back_to))


class FishRPG(commands.Cog):
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=847291035712, force_registration=True)
        self.config.register_user(
            currency=0,
            xp=0,
            current_area="harbor",
            last_fish=0.0,
            inventory_fish={},
            inventory_items={},
            boats=[],
            caught_counts={},
            active_quests={},
            completed_quests=[],
            equipped_item=None,
        )
        self.config.register_guild(
            cooldown=60,
            page_images={},
            starting_area="harbor",
        )
        self.data_path = Path(__file__).parent / "data"
        self.data = DataManager(self.data_path)

    async def cog_check(self, ctx: commands.Context) -> bool:
        if ctx.guild is None:
            raise commands.NoPrivateMessage()
        return True

    @staticmethod
    def format_currency(amount):
        return f"{amount:,} 🪙"

    @staticmethod
    def level_from_xp(xp):
        level = 1
        needed = 100
        remaining = xp
        while remaining >= needed:
            remaining -= needed
            level += 1
            needed = int(needed * 1.25)
        return level, remaining, needed

    def base_embed(self, title, description=None, color=FALLBACK_COLOR):
        return discord.Embed(title=title, description=description, color=color)

    def default_back(self, member, guild):
        return lambda: self.build_main_menu(member, guild)

    async def page_image(self, guild, key):
        images = await self.config.guild(guild).page_images()
        return images.get(key) or None

    def find_fish_by_name(self, name):
        name = name.lower().strip()
        for fish in self.data.fish.values():
            if fish["id"].lower() == name or fish["name"].lower() == name:
                return fish
        return None

    def find_item_by_name(self, name):
        name = name.lower().strip()
        for item in self.data.items.values():
            if item["id"].lower() == name or item["name"].lower() == name:
                return item
        return None

    def find_boat_by_name(self, name):
        name = name.lower().strip()
        for boat in self.data.boats.values():
            if boat["id"].lower() == name or boat["name"].lower() == name:
                return boat
        return None

    async def get_effective_cooldown(self, member):
        base = await self.config.guild(member.guild).cooldown()
        equipped = await self.config.user(member).equipped_item()
        if equipped:
            item = self.data.items.get(equipped)
            if item and item.get("effect") == "cooldown_reduction":
                base = max(5, base - int(item.get("effect_value", 0)))
        return base

    async def get_luck_boost(self, member):
        equipped = await self.config.user(member).equipped_item()
        if equipped:
            item = self.data.items.get(equipped)
            if item and item.get("effect") == "luck_boost":
                return float(item.get("effect_value", 0.0))
        return 0.0

    async def attempt_fish(self, member):
        user_conf = self.config.user(member)
        last_fish = await user_conf.last_fish()
        cooldown = await self.get_effective_cooldown(member)
        now = time.time()
        remaining = (last_fish + cooldown) - now
        if remaining > 0:
            return {"success": False, "retry_at": int(now + remaining) + 1}
        area_id = await user_conf.current_area()
        luck = await self.get_luck_boost(member)
        fish = self.data.roll_fish(area_id, luck)
        if not fish:
            return {"success": False, "error": "no_fish"}
        async with user_conf.inventory_fish() as inventory:
            inventory[fish["id"]] = inventory.get(fish["id"], 0) + 1
        async with user_conf.caught_counts() as counts:
            counts[fish["id"]] = counts.get(fish["id"], 0) + 1
        rarity = self.data.rarities.get(fish["rarity"], {"weight": 100})
        xp_gain = max(1, int(150 / max(rarity.get("weight", 100), 1)))
        xp = await user_conf.xp()
        await user_conf.xp.set(xp + xp_gain)
        await user_conf.last_fish.set(now)
        await self.update_quest_progress(member, fish)
        return {"success": True, "fish": fish, "xp_gain": xp_gain, "retry_at": int(now + cooldown) + 1}

    async def update_quest_progress(self, member, fish):
        user_conf = self.config.user(member)
        async with user_conf.active_quests() as active:
            for quest_id, quest_state in active.items():
                quest = self.data.quests.get(quest_id)
                if not quest:
                    continue
                matched = False
                if quest["type"] == "catch_any":
                    matched = True
                elif quest["type"] == "catch_fish" and quest.get("target") == fish["id"]:
                    matched = True
                elif quest["type"] == "catch_rarity" and quest.get("target") == fish["rarity"]:
                    matched = True
                if matched and quest_state["progress"] < quest["amount"]:
                    quest_state["progress"] += 1

    async def turn_in_quest(self, member, quest_id):
        quest = self.data.quests.get(quest_id)
        if not quest:
            return "That quest no longer exists."
        user_conf = self.config.user(member)
        active = await user_conf.active_quests()
        state = active.get(quest_id)
        if not state or state["progress"] < quest["amount"]:
            return "You haven't completed this quest yet."
        currency = await user_conf.currency()
        await user_conf.currency.set(currency + quest.get("reward_currency", 0))
        xp = await user_conf.xp()
        await user_conf.xp.set(xp + quest.get("reward_xp", 0))
        if quest.get("reward_items"):
            async with user_conf.inventory_items() as inventory:
                for item_id, amount in quest["reward_items"].items():
                    inventory[item_id] = inventory.get(item_id, 0) + amount
        async with user_conf.active_quests() as active_mut:
            active_mut.pop(quest_id, None)
        if not quest.get("repeatable"):
            async with user_conf.completed_quests() as completed:
                if quest_id not in completed:
                    completed.append(quest_id)
        return f"Quest complete! You received {self.format_currency(quest.get('reward_currency', 0))}."

    async def travel_to(self, member, area_id):
        area = self.data.areas.get(area_id)
        if not area:
            return "That area does not exist."
        user_conf = self.config.user(member)
        required = area.get("required_boat")
        if required:
            boats = await user_conf.boats()
            if required not in boats:
                boat = self.data.boats.get(required, {})
                return f"You need the {boat.get('name', required)} to reach {area['name']}. You can buy it in the shop."
        await user_conf.current_area.set(area_id)
        return f"You have traveled to {area['name']}."

    async def sell_fish(self, member, fish_id, amount):
        fish = self.data.fish.get(fish_id)
        if not fish or amount <= 0:
            return 0
        user_conf = self.config.user(member)
        async with user_conf.inventory_fish() as inventory:
            owned = inventory.get(fish_id, 0)
            amount = min(amount, owned)
            if amount <= 0:
                return 0
            inventory[fish_id] = owned - amount
            if inventory[fish_id] <= 0:
                inventory.pop(fish_id, None)
        total = fish.get("value", 0) * amount
        currency = await user_conf.currency()
        await user_conf.currency.set(currency + total)
        return total

    async def buy_boat(self, member, boat_id):
        boat = self.data.boats.get(boat_id)
        if not boat:
            return False, "That boat does not exist."
        user_conf = self.config.user(member)
        boats = await user_conf.boats()
        if boat_id in boats:
            return False, "You already own this boat."
        currency = await user_conf.currency()
        if currency < boat["price"]:
            return False, "You do not have enough FishCoins for this boat."
        await user_conf.currency.set(currency - boat["price"])
        boats.append(boat_id)
        await user_conf.boats.set(boats)
        return True, f"You bought the {boat['name']}!"

    async def buy_item(self, member, item_id):
        item = self.data.items.get(item_id)
        if not item:
            return False, "That item does not exist."
        user_conf = self.config.user(member)
        currency = await user_conf.currency()
        if currency < item["price"]:
            return False, "You do not have enough FishCoins for this item."
        await user_conf.currency.set(currency - item["price"])
        async with user_conf.inventory_items() as inventory:
            inventory[item_id] = inventory.get(item_id, 0) + 1
        return True, f"You bought a {item['name']}!"

    async def build_main_menu(self, member, guild):
        user_conf = self.config.user(member)
        currency = await user_conf.currency()
        area_id = await user_conf.current_area()
        area = self.data.areas.get(area_id, {})
        xp = await user_conf.xp()
        level, _, _ = self.level_from_xp(xp)
        embed = self.base_embed(
            f"🎣 {member.display_name}'s Fishing Adventure",
            "Pick an option from the dropdown below to get started.",
            color=0x2ECC71,
        )
        embed.add_field(name="Currency", value=self.format_currency(currency), inline=True)
        embed.add_field(name="Level", value=str(level), inline=True)
        embed.add_field(name="Current Area", value=area.get("name", area_id), inline=True)
        image = await self.page_image(guild, "menu")
        if image:
            embed.set_image(url=image)
        view = MainMenuView(self, member)
        return embed, view

    async def dispatch_menu(self, interaction: discord.Interaction, key, item):
        member = interaction.user
        guild = interaction.guild
        builders = {
            "fish": self.build_fish_page,
            "travel": self.build_travel_page,
            "shop": self.build_shop_home,
            "leaderboard": self.build_leaderboard_page,
            "fishpedia": self.build_fishpedia_list,
            "quests": self.build_quests_list,
            "inventory": self.build_inventory_page,
            "profile": self.build_profile_page,
        }
        builder = builders.get(key)
        if not builder:
            return
        embed, view = await builder(member, guild)
        await finish_transition(interaction, item, embed, view)

    async def build_fish_page(self, member, guild, back_to=None):
        back = back_to or self.default_back(member, guild)
        result = await self.attempt_fish(member)
        image = await self.page_image(guild, "fish")
        if not result["success"]:
            if result.get("error") == "no_fish":
                embed = self.base_embed(
                    "🎣 Nothing to catch",
                    "There don't seem to be any fish in this area yet.",
                    color=0xE74C3C,
                )
            else:
                retry_at = result["retry_at"]
                embed = self.base_embed(
                    "🎣 Still Reeling In",
                    f"You need to wait before you can fish again.\nYou can fish again <t:{retry_at}:R> (<t:{retry_at}:T>).",
                    color=0xE67E22,
                )
        else:
            fish = result["fish"]
            rarity_id = fish["rarity"]
            embed = self.base_embed(
                f"{self.data.rarity_emoji(rarity_id)} You caught a {fish['name']}!",
                fish.get("description", ""),
                color=self.data.rarity_color(rarity_id),
            )
            embed.add_field(name="Rarity", value=self.data.rarity_name(rarity_id), inline=True)
            embed.add_field(name="XP Gained", value=str(result["xp_gain"]), inline=True)
            embed.add_field(name="Next Cast", value=f"<t:{result['retry_at']}:R>", inline=True)
            fish_image = fish.get("image")
            if fish_image:
                embed.set_thumbnail(url=fish_image)
        if image:
            embed.set_image(url=image)
        view = FishActionView(self, member, back)
        return embed, view

    async def build_travel_page(self, member, guild, page=0, back_to=None):
        back = back_to or self.default_back(member, guild)
        areas = self.data.sorted_areas()
        total_pages = max(1, (len(areas) + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(0, min(page, total_pages - 1))
        chunk = areas[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
        user_conf = self.config.user(member)
        current_area = await user_conf.current_area()
        owned_boats = await user_conf.boats()
        embed = self.base_embed("🧭 Travel", "Choose a new area to fish in.", color=0x3498DB)
        for area in chunk:
            required = area.get("required_boat")
            if area["id"] == current_area:
                status = "📍 Current Area"
            elif not required or required in owned_boats:
                status = "🔓 Unlocked"
            else:
                boat_name = self.data.boats.get(required, {}).get("name", required)
                status = f"🔒 Requires the {boat_name}"
            embed.add_field(name=area["name"], value=f"{area.get('description', '')}\n{status}", inline=False)
        image = await self.page_image(guild, "travel")
        if image:
            embed.set_image(url=image)
        if total_pages > 1:
            embed.set_footer(text=f"Page {page + 1}/{total_pages}")
        view = TravelView(self, member, guild, chunk, page, total_pages, back)
        return embed, view

    async def build_shop_home(self, member, guild, back_to=None):
        back = back_to or self.default_back(member, guild)
        embed = self.base_embed(
            "🛒 Shop",
            "Buy boats and items, or sell your fish for FishCoins.",
            color=0xF1C40F,
        )
        image = await self.page_image(guild, "shop")
        if image:
            embed.set_image(url=image)
        view = ShopHomeView(self, member, guild, back)
        return embed, view

    async def build_shop_list(self, member, guild, category, page=0, back_to=None):
        back = back_to or (lambda: self.build_shop_home(member, guild))
        user_conf = self.config.user(member)
        currency = await user_conf.currency()
        if category == "boats":
            entries = list(self.data.boats.values())
            title = "⛵ Boats for Sale"
        elif category == "items":
            entries = list(self.data.items.values())
            title = "🎒 Items for Sale"
        else:
            inventory = await user_conf.inventory_fish()
            entries = [self.data.fish[fid] for fid, amount in inventory.items() if amount > 0 and fid in self.data.fish]
            title = "💰 Sell Fish"
        total_pages = max(1, (len(entries) + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(0, min(page, total_pages - 1))
        chunk = entries[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
        embed = self.base_embed(title, f"Your balance: {self.format_currency(currency)}", color=0xF1C40F)
        if not chunk:
            empty_text = {
                "boats": "There are no boats available right now.",
                "items": "There are no items available right now.",
                "sell": "You don't have any fish to sell yet. Go catch some!",
            }[category]
            embed.description += f"\n{empty_text}"
        if category == "sell":
            inventory = await user_conf.inventory_fish()
            for fish in chunk:
                owned_amount = inventory.get(fish["id"], 0)
                embed.add_field(
                    name=fish["name"],
                    value=f"You own {owned_amount} • Sells for {self.format_currency(fish.get('value', 0))} each",
                    inline=False,
                )
        elif category == "boats":
            owned_boats = await user_conf.boats()
            for boat in chunk:
                status = "✅ Owned" if boat["id"] in owned_boats else self.format_currency(boat["price"])
                embed.add_field(name=boat["name"], value=f"{boat.get('description', '')}\n{status}", inline=False)
        else:
            for item in chunk:
                embed.add_field(
                    name=item["name"],
                    value=f"{item.get('description', '')}\n{self.format_currency(item['price'])}",
                    inline=False,
                )
        image = await self.page_image(guild, "shop")
        if image:
            embed.set_image(url=image)
        if total_pages > 1:
            embed.set_footer(text=f"Page {page + 1}/{total_pages}")
        view = ShopListView(self, member, guild, category, chunk, page, total_pages, back)
        return embed, view

    async def build_shop_detail(self, member, guild, category, entry_id, back_to):
        user_conf = self.config.user(member)
        owned = False
        entry = None
        if category == "boats":
            entry = self.data.boats.get(entry_id)
            if entry:
                owned_boats = await user_conf.boats()
                owned = entry_id in owned_boats
        elif category == "items":
            entry = self.data.items.get(entry_id)
        else:
            entry = self.data.fish.get(entry_id)

        if not entry:
            embed = self.base_embed("Not Found", "That entry could not be found.", color=0xE74C3C)
            view = BaseFishView(self, member)
            view.add_item(BackButton(back_to))
            return embed, view

        if category == "sell":
            inventory = await user_conf.inventory_fish()
            owned_amount = inventory.get(entry_id, 0)
            price = entry.get("value", 0)
            color = self.data.rarity_color(entry.get("rarity"))
        else:
            price = entry.get("price", 0)
            color = 0xF1C40F

        embed = self.base_embed(entry["name"], entry.get("description", ""), color=color)
        if category == "sell":
            embed.add_field(name="Rarity", value=self.data.rarity_name(entry["rarity"]), inline=True)
            embed.add_field(name="You Own", value=str(owned_amount), inline=True)
            embed.add_field(name="Sell Value", value=self.format_currency(price), inline=True)
        else:
            embed.add_field(name="Price", value=self.format_currency(price), inline=True)
            if category == "boats":
                embed.add_field(name="Status", value="Owned" if owned else "Not Owned", inline=True)
                unlock_area = self.data.areas.get(entry.get("unlocks_area"), {})
                embed.add_field(name="Unlocks", value=unlock_area.get("name", "Unknown"), inline=True)

        image = entry.get("image")
        if image:
            embed.set_image(url=image)
        view = ShopDetailView(self, member, guild, category, entry, back_to, owned=owned)
        return embed, view

    async def build_leaderboard_page(self, member, guild, page=0, back_to=None):
        back = back_to or self.default_back(member, guild)
        all_users = await self.config.all_users()
        ranked = []
        for user_id, data in all_users.items():
            target_member = guild.get_member(int(user_id))
            if not target_member:
                continue
            total_caught = sum(data.get("caught_counts", {}).values())
            ranked.append((target_member, total_caught, data.get("currency", 0), data.get("xp", 0)))
        ranked.sort(key=lambda entry: (entry[1], entry[2]), reverse=True)
        total_pages = max(1, (len(ranked) + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(0, min(page, total_pages - 1))
        chunk = ranked[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
        embed = self.base_embed("🏆 Top Anglers", "Ranked by total fish caught.", color=0xF1C40F)
        if not chunk:
            embed.description = "No anglers on the leaderboard yet. Go catch some fish!"
        for index, (target_member, total_caught, currency, xp) in enumerate(chunk, start=page * PAGE_SIZE + 1):
            level, _, _ = self.level_from_xp(xp)
            embed.add_field(
                name=f"#{index} {target_member.display_name}",
                value=f"{total_caught} fish caught • Level {level} • {self.format_currency(currency)}",
                inline=False,
            )
        image = await self.page_image(guild, "leaderboard")
        if image:
            embed.set_image(url=image)
        if total_pages > 1:
            embed.set_footer(text=f"Page {page + 1}/{total_pages}")

        def builder(new_page):
            return self.build_leaderboard_page(member, guild, page=new_page, back_to=back)

        view = SimplePagedView(self, member, back, page, total_pages, builder)
        return embed, view

    async def build_fishpedia_list(self, member, guild, page=0, back_to=None):
        back = back_to or self.default_back(member, guild)
        user_conf = self.config.user(member)
        caught = await user_conf.caught_counts()
        all_fish = sorted(
            self.data.fish.values(),
            key=lambda f: (-(self.data.rarities.get(f["rarity"], {}).get("weight", 0)), f["name"]),
        )
        total_species = len(all_fish)
        caught_species = sum(1 for f in all_fish if caught.get(f["id"], 0) > 0)
        total_pages = max(1, (len(all_fish) + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(0, min(page, total_pages - 1))
        chunk = all_fish[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
        embed = self.base_embed(
            "📖 Fishpedia",
            f"You've discovered {caught_species}/{total_species} species. Select a fish below to view its details.",
            color=0x9B59B6,
        )
        for fish in chunk:
            count = caught.get(fish["id"], 0)
            status = f"Caught x{count}" if count else "Not yet caught"
            embed.add_field(
                name=f"{self.data.rarity_emoji(fish['rarity'])} {fish['name']}",
                value=f"{self.data.rarity_name(fish['rarity'])} • {status}",
                inline=True,
            )
        image = await self.page_image(guild, "fishpedia")
        if image:
            embed.set_image(url=image)
        if total_pages > 1:
            embed.set_footer(text=f"Page {page + 1}/{total_pages}")
        view = FishpediaListView(self, member, guild, chunk, page, total_pages, back)
        return embed, view

    async def build_fishpedia_detail(self, member, guild, fish_id, back_to):
        fish = self.data.fish.get(fish_id)
        if not fish:
            embed = self.base_embed("Not Found", "That fish could not be found.", color=0xE74C3C)
            view = BaseFishView(self, member)
            view.add_item(BackButton(back_to))
            return embed, view
        user_conf = self.config.user(member)
        caught = await user_conf.caught_counts()
        count = caught.get(fish_id, 0)
        embed = self.base_embed(
            f"{self.data.rarity_emoji(fish['rarity'])} {fish['name']}",
            fish.get("description", ""),
            color=self.data.rarity_color(fish["rarity"]),
        )
        embed.add_field(name="Rarity", value=self.data.rarity_name(fish["rarity"]), inline=True)
        embed.add_field(name="Caught", value=str(count), inline=True)
        embed.add_field(name="Sell Value", value=self.format_currency(fish.get("value", 0)), inline=True)
        areas = [self.data.areas.get(a, {}).get("name", a) for a in fish.get("areas", [])]
        embed.add_field(name="Found In", value=", ".join(areas) if areas else "Unknown", inline=False)
        image = fish.get("image")
        if image:
            embed.set_image(url=image)
        view = BaseFishView(self, member)
        view.add_item(BackButton(back_to))
        return embed, view

    async def build_quests_list(self, member, guild, page=0, back_to=None, mine=False):
        back = back_to or self.default_back(member, guild)
        user_conf = self.config.user(member)
        area_id = await user_conf.current_area()
        active = await user_conf.active_quests()
        completed = await user_conf.completed_quests()
        if mine:
            quests = [self.data.quests[q] for q in active.keys() if q in self.data.quests]
            title = "📜 My Active Quests"
            description = "All quests you currently have active, across every area."
        else:
            quests = [
                q for q in self.data.quests.values()
                if q.get("area") == area_id and (q["id"] not in completed or q.get("repeatable"))
            ]
            area = self.data.areas.get(area_id, {})
            title = f"📜 Quests in {area.get('name', area_id)}"
            description = "Speak to the local NPCs and take on a quest."
        total_pages = max(1, (len(quests) + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(0, min(page, total_pages - 1))
        chunk = quests[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
        embed = self.base_embed(title, description, color=0x1ABC9C)
        if not chunk:
            embed.description = (
                "You don't have any active quests. Visit an area to accept one!"
                if mine else "There are no quests here right now."
            )
        for quest in chunk:
            state = active.get(quest["id"])
            if state:
                status = f"In Progress ({state['progress']}/{quest['amount']})"
            elif quest["id"] in completed and not quest.get("repeatable"):
                status = "Completed"
            else:
                status = "Available"
            embed.add_field(name=f"{quest['name']} ({quest.get('npc', 'NPC')})", value=status, inline=False)
        image = await self.page_image(guild, "quests")
        if image:
            embed.set_image(url=image)
        if total_pages > 1:
            embed.set_footer(text=f"Page {page + 1}/{total_pages}")
        view = QuestsListView(self, member, guild, chunk, page, total_pages, back, mine)
        return embed, view

    def describe_quest_objective(self, quest):
        if quest["type"] == "catch_any":
            return f"Catch {quest['amount']} fish of any kind."
        if quest["type"] == "catch_fish":
            fish = self.data.fish.get(quest["target"], {})
            return f"Catch {quest['amount']}x {fish.get('name', quest['target'])}."
        if quest["type"] == "catch_rarity":
            return f"Catch {quest['amount']} fish of {self.data.rarity_name(quest['target'])} rarity."
        return "Unknown objective."

    def describe_quest_rewards(self, quest):
        parts = [self.format_currency(quest.get("reward_currency", 0))]
        if quest.get("reward_xp"):
            parts.append(f"{quest['reward_xp']} XP")
        for item_id, amount in quest.get("reward_items", {}).items():
            item = self.data.items.get(item_id, {})
            parts.append(f"{amount}x {item.get('name', item_id)}")
        return "\n".join(parts)

    async def build_quest_detail(self, member, guild, quest_id, back_to):
        quest = self.data.quests.get(quest_id)
        if not quest:
            embed = self.base_embed("Not Found", "That quest could not be found.", color=0xE74C3C)
            view = BaseFishView(self, member)
            view.add_item(BackButton(back_to))
            return embed, view
        user_conf = self.config.user(member)
        active = await user_conf.active_quests()
        completed = await user_conf.completed_quests()
        state = active.get(quest_id)
        embed = self.base_embed(quest["name"], quest.get("description", ""), color=0x1ABC9C)
        embed.add_field(name="NPC", value=quest.get("npc", "Unknown"), inline=True)
        area = self.data.areas.get(quest.get("area"), {})
        embed.add_field(name="Area", value=area.get("name", quest.get("area", "Unknown")), inline=True)
        embed.add_field(name="Objective", value=self.describe_quest_objective(quest), inline=False)
        embed.add_field(name="Rewards", value=self.describe_quest_rewards(quest), inline=False)
        if state:
            embed.add_field(name="Progress", value=f"{state['progress']}/{quest['amount']}", inline=True)
        elif quest_id in completed and not quest.get("repeatable"):
            embed.add_field(name="Status", value="Completed", inline=True)
        image = quest.get("image")
        if image:
            embed.set_image(url=image)
        view = QuestDetailView(self, member, guild, quest, state, completed, back_to)
        return embed, view

    async def build_inventory_page(self, member, guild, page=0, back_to=None):
        back = back_to or self.default_back(member, guild)
        user_conf = self.config.user(member)
        currency = await user_conf.currency()
        boats = await user_conf.boats()
        items = await user_conf.inventory_items()
        fish_inventory = await user_conf.inventory_fish()
        equipped = await user_conf.equipped_item()
        entries = []
        for boat_id in boats:
            boat = self.data.boats.get(boat_id)
            if boat:
                entries.append(("Boat", boat["name"], "Owned"))
        for item_id, amount in items.items():
            item = self.data.items.get(item_id)
            if item and amount > 0:
                label = f"{item['name']} (equipped)" if equipped == item_id else item["name"]
                entries.append(("Item", label, f"x{amount}"))
        for fish_id, amount in fish_inventory.items():
            fish = self.data.fish.get(fish_id)
            if fish and amount > 0:
                entries.append(("Fish", fish["name"], f"x{amount}"))
        total_pages = max(1, (len(entries) + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(0, min(page, total_pages - 1))
        chunk = entries[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
        embed = self.base_embed(
            f"🎒 {member.display_name}'s Inventory",
            f"Balance: {self.format_currency(currency)}",
            color=0x95A5A6,
        )
        if not chunk:
            embed.description += "\nYour inventory is empty. Go catch some fish!"
        for category, name, value in chunk:
            embed.add_field(name=f"[{category}] {name}", value=value, inline=True)
        image = await self.page_image(guild, "inventory")
        if image:
            embed.set_image(url=image)
        if total_pages > 1:
            embed.set_footer(text=f"Page {page + 1}/{total_pages}")

        def builder(new_page):
            return self.build_inventory_page(member, guild, page=new_page, back_to=back)

        equip_options = [
            (item_id, self.data.items[item_id])
            for item_id, amount in items.items()
            if amount > 0 and item_id in self.data.items
        ]
        view = InventoryView(self, member, guild, back, page, total_pages, builder, equip_options)
        return embed, view

    async def build_profile_page(self, member, guild, back_to=None):
        back = back_to or self.default_back(member, guild)
        user_conf = self.config.user(member)
        currency = await user_conf.currency()
        xp = await user_conf.xp()
        level, current_xp, needed_xp = self.level_from_xp(xp)
        caught = await user_conf.caught_counts()
        total_caught = sum(caught.values())
        species_caught = sum(1 for value in caught.values() if value > 0)
        boats = await user_conf.boats()
        completed_quests = await user_conf.completed_quests()
        area_id = await user_conf.current_area()
        area = self.data.areas.get(area_id, {})
        embed = self.base_embed(f"👤 {member.display_name}'s Profile", color=0x3498DB)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Level", value=f"{level} ({current_xp}/{needed_xp} XP)", inline=True)
        embed.add_field(name="Currency", value=self.format_currency(currency), inline=True)
        embed.add_field(name="Current Area", value=area.get("name", area_id), inline=True)
        embed.add_field(name="Total Fish Caught", value=str(total_caught), inline=True)
        embed.add_field(name="Species Discovered", value=f"{species_caught}/{len(self.data.fish)}", inline=True)
        embed.add_field(name="Boats Owned", value=str(len(boats)), inline=True)
        embed.add_field(name="Quests Completed", value=str(len(completed_quests)), inline=True)
        image = await self.page_image(guild, "profile")
        if image:
            embed.set_image(url=image)
        view = BaseFishView(self, member)
        view.add_item(BackButton(back))
        return embed, view

    @commands.group(name="fishrpg", aliases=["frpg"], invoke_without_command=True)
    async def fishrpg(self, ctx: commands.Context):
        embed, view = await self.build_main_menu(ctx.author, ctx.guild)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @fishrpg.command(name="fish")
    async def fishrpg_fish(self, ctx: commands.Context):
        embed, view = await self.build_fish_page(ctx.author, ctx.guild)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @fishrpg.command(name="travel")
    async def fishrpg_travel(self, ctx: commands.Context):
        embed, view = await self.build_travel_page(ctx.author, ctx.guild)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @fishrpg.command(name="shop")
    async def fishrpg_shop(self, ctx: commands.Context):
        embed, view = await self.build_shop_home(ctx.author, ctx.guild)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @fishrpg.command(name="leaderboard", aliases=["lb"])
    async def fishrpg_leaderboard(self, ctx: commands.Context):
        embed, view = await self.build_leaderboard_page(ctx.author, ctx.guild)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @fishrpg.command(name="fishpedia", aliases=["dex"])
    async def fishrpg_fishpedia(self, ctx: commands.Context):
        embed, view = await self.build_fishpedia_list(ctx.author, ctx.guild)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @fishrpg.command(name="quests")
    async def fishrpg_quests(self, ctx: commands.Context):
        embed, view = await self.build_quests_list(ctx.author, ctx.guild)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @fishrpg.command(name="inventory", aliases=["inv"])
    async def fishrpg_inventory(self, ctx: commands.Context):
        embed, view = await self.build_inventory_page(ctx.author, ctx.guild)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @fishrpg.command(name="profile")
    async def fishrpg_profile(self, ctx: commands.Context):
        embed, view = await self.build_profile_page(ctx.author, ctx.guild)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @fishrpg.command(name="sell")
    async def fishrpg_sell(self, ctx: commands.Context, amount: int = 1, *, fish_name: str):
        fish = self.find_fish_by_name(fish_name)
        if not fish:
            await ctx.send("I couldn't find a fish by that name.")
            return
        if amount <= 0:
            await ctx.send("Enter a positive amount to sell.")
            return
        total = await self.sell_fish(ctx.author, fish["id"], amount)
        if total <= 0:
            await ctx.send(f"You don't have any {fish['name']} to sell.")
            return
        await ctx.send(f"Sold {amount}x {fish['name']} for {self.format_currency(total)}.")

    @fishrpg.command(name="equip")
    async def fishrpg_equip(self, ctx: commands.Context, *, item_name: str):
        item = self.find_item_by_name(item_name)
        if not item:
            await ctx.send("I couldn't find an item by that name.")
            return
        owned = await self.config.user(ctx.author).inventory_items()
        if owned.get(item["id"], 0) <= 0:
            await ctx.send("You don't own that item.")
            return
        await self.config.user(ctx.author).equipped_item.set(item["id"])
        await ctx.send(f"Equipped {item['name']}.")

    @fishrpg.command(name="unequip")
    async def fishrpg_unequip(self, ctx: commands.Context):
        await self.config.user(ctx.author).equipped_item.set(None)
        await ctx.send("Unequipped your item.")

    @commands.group(name="fishrpgadmin", aliases=["fishadmin"])
    @commands.admin_or_permissions(manage_guild=True)
    async def fishrpgadmin(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @fishrpgadmin.command(name="cooldown")
    async def fishrpgadmin_cooldown(self, ctx: commands.Context, seconds: int):
        if seconds < 1:
            await ctx.send("Cooldown must be at least 1 second.")
            return
        await self.config.guild(ctx.guild).cooldown.set(seconds)
        await ctx.send(f"Fishing cooldown set to {seconds} seconds.")

    @fishrpgadmin.command(name="pageimage")
    async def fishrpgadmin_pageimage(self, ctx: commands.Context, page: str, url: str = None):
        page = page.lower()
        if page not in VALID_PAGE_IMAGE_KEYS:
            await ctx.send(f"Page must be one of: {', '.join(sorted(VALID_PAGE_IMAGE_KEYS))}")
            return
        async with self.config.guild(ctx.guild).page_images() as images:
            if url:
                images[page] = url
            else:
                images.pop(page, None)
        await ctx.send(f"Updated the image for the {page} page." if url else f"Cleared the image for the {page} page.")

    @fishrpgadmin.command(name="givecurrency")
    async def fishrpgadmin_givecurrency(self, ctx: commands.Context, member: discord.Member, amount: int):
        user_conf = self.config.user(member)
        currency = await user_conf.currency()
        await user_conf.currency.set(max(0, currency + amount))
        await ctx.send(f"Gave {amount} FishCoins to {member.display_name}.")

    @fishrpgadmin.command(name="givefish")
    async def fishrpgadmin_givefish(self, ctx: commands.Context, member: discord.Member, fish_id: str, amount: int = 1):
        fish = self.data.fish.get(fish_id) or self.find_fish_by_name(fish_id)
        if not fish:
            await ctx.send("I couldn't find a fish with that id or name.")
            return
        async with self.config.user(member).inventory_fish() as inventory:
            inventory[fish["id"]] = inventory.get(fish["id"], 0) + amount
        async with self.config.user(member).caught_counts() as counts:
            counts[fish["id"]] = counts.get(fish["id"], 0) + amount
        await ctx.send(f"Gave {amount}x {fish['name']} to {member.display_name}.")

    @fishrpgadmin.command(name="giveboat")
    async def fishrpgadmin_giveboat(self, ctx: commands.Context, member: discord.Member, boat_id: str):
        boat = self.data.boats.get(boat_id) or self.find_boat_by_name(boat_id)
        if not boat:
            await ctx.send("I couldn't find a boat with that id or name.")
            return
        async with self.config.user(member).boats() as boats:
            if boat["id"] not in boats:
                boats.append(boat["id"])
        await ctx.send(f"Gave the {boat['name']} to {member.display_name}.")

    @fishrpgadmin.command(name="giveitem")
    async def fishrpgadmin_giveitem(self, ctx: commands.Context, member: discord.Member, item_id: str, amount: int = 1):
        item = self.data.items.get(item_id) or self.find_item_by_name(item_id)
        if not item:
            await ctx.send("I couldn't find an item with that id or name.")
            return
        async with self.config.user(member).inventory_items() as inventory:
            inventory[item["id"]] = inventory.get(item["id"], 0) + amount
        await ctx.send(f"Gave {amount}x {item['name']} to {member.display_name}.")

    @fishrpgadmin.command(name="setarea")
    async def fishrpgadmin_setarea(self, ctx: commands.Context, member: discord.Member, area_id: str):
        area = self.data.areas.get(area_id)
        if not area:
            await ctx.send("I couldn't find an area with that id.")
            return
        await self.config.user(member).current_area.set(area_id)
        await ctx.send(f"Set {member.display_name}'s area to {area['name']}.")

    @fishrpgadmin.command(name="resetuser")
    async def fishrpgadmin_resetuser(self, ctx: commands.Context, member: discord.Member):
        await self.config.user(member).clear()
        await ctx.send(f"Reset all fishing data for {member.display_name}.")

    @fishrpgadmin.command(name="reload")
    async def fishrpgadmin_reload(self, ctx: commands.Context):
        try:
            self.data.reload()
        except Exception as error:
            await ctx.send(f"Failed to reload game data: {error}")
            return
        await ctx.send("Game data reloaded from disk.")
