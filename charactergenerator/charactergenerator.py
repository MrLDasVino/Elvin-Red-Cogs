import json
import random
from pathlib import Path

import discord
from redbot.core import commands

class CharacterGenerator(commands.Cog):
    """
    Generate quirky characters with multiple optional filters.
    Posts results in a rich embed with a random Discord color and thumbnail.
    """

    def __init__(self, bot):
        self.bot = bot
        self.character_data = {}

    async def cog_load(self):
        """
        Called once when the cog is loaded.
        Caches character_data.json in memory.
        """
        data_path = Path(__file__).parent / "character_data.json"
        try:
            with open(data_path, encoding="utf-8") as f:
                self.character_data = json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load character_data.json: {e}")

    @commands.command()
    async def charactergenerate(self, ctx, *filters):
        """
        Generate a random character in an embed.
        You can supply multiple filter pairs, e.g.:
        [p]charactergenerate profession wizard goal avenge secret debt

        Valid filters: profession, quirk, backstory,
                       goal, secret, relationship, equipment
        """
        data = self.character_data

        # Define all pools
        pools = {
            "first_names":  data.get("first_names", []),
            "last_names":   data.get("last_names", []),
            "profession":   data.get("professions", []),
            "quirk":        data.get("quirks", []),
            "backstory":    data.get("backstories", []),
            "goal":         data.get("goals", []),
            "secret":       data.get("secrets", []),
            "relationship": data.get("relationships", []),
            "equipment":    data.get("equipment", []),
            "thumbnail":    data.get("thumbnails", []),
        }

        # Check core pools
        core = [
            "first_names", "last_names", "profession", "quirk",
            "backstory", "goal", "secret", "relationship", "equipment"
        ]
        if any(not pools[key] for key in core):
            await ctx.send("Character data is missing or malformed.")
            return

        # Apply filters if provided
        if filters:
            if len(filters) % 2 != 0:
                await ctx.send(
                    "Filters must come in trait–term pairs "
                    "(e.g., profession wizard)."
                )
                return

            used = set()
            for i in range(0, len(filters), 2):
                trait = filters[i].lower()
                term  = filters[i + 1]

                if trait not in pools or trait in ("first_names", "last_names"):
                    valid = ", ".join(
                        k for k in pools
                        if k not in ("first_names", "last_names", "thumbnail")
                    )
                    await ctx.send(f"Invalid filter `{trait}`. Choose from: {valid}.")
                    return

                if trait in used:
                    await ctx.send(f"Duplicate filter `{trait}` not allowed.")
                    return
                used.add(trait)

                matches = [item for item in pools[trait] if term.lower() in item.lower()]
                if not matches:
                    await ctx.send(f"No `{trait}` entries matched “{term}.”")
                    return

                pools[trait] = matches

        # Randomly pick each trait
        first        = random.choice(pools["first_names"])
        last         = random.choice(pools["last_names"])
        profession   = random.choice(pools["profession"])
        quirk        = random.choice(pools["quirk"])
        backstory    = random.choice(pools["backstory"])
        goal         = random.choice(pools["goal"])
        secret       = random.choice(pools["secret"])
        relationship = random.choice(pools["relationship"])
        equipment    = random.choice(pools["equipment"])

        # Build embed with Discord's random color
        embed = discord.Embed(
            title=f"{first} {last}",
            color=discord.Color.random()
        )
        embed.add_field(name="🎓 Profession",   value=profession,   inline=False)
        embed.add_field(name="✨ Quirk",        value=quirk,        inline=False)
        embed.add_field(name="📜 Backstory",    value=backstory,    inline=False)
        embed.add_field(name="🎯 Goal",         value=goal,         inline=False)
        embed.add_field(name="🔒 Secret",       value=secret,       inline=False)
        embed.add_field(name="🤝 Relationship", value=relationship, inline=False)
        embed.add_field(name="🛡 Equipment",    value=equipment,    inline=False)

        # Attach a random thumbnail if available
        thumbs = pools.get("thumbnail", [])
        if thumbs:
            embed.set_thumbnail(url=random.choice(thumbs))

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CharacterGenerator(bot))
