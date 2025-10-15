import aiohttp
import asyncio
import discord
import random
from urllib.parse import quote_plus
from redbot.core import commands

class UrbanDictionary(commands.Cog):
    """Look up slang definitions, examples, and user ratings from Urban Dictionary."""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        await self.session.close()

    @commands.command()
    async def urban(self, ctx, *, term: str):
        """
        Look up a term on Urban Dictionary.
        Use "random" for a random entry.
        """
        query = term.strip()
        if query.lower() == "random":
            url = "https://api.urbandictionary.com/v0/random"
            display = "Random Entry"
        else:
            safe = quote_plus(query)
            url = f"https://api.urbandictionary.com/v0/define?term={safe}"
            display = query.title()

        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return await ctx.send(f"❌ HTTP {resp.status} from Urban Dictionary.")
                data = await resp.json()
        except aiohttp.ClientError:
            return await ctx.send("❌ Network error when contacting Urban Dictionary.")
        except Exception:
            return await ctx.send("❌ Unexpected error fetching data.")

        entries = data.get("list", [])
        if not entries:
            return await ctx.send(f"🔍 No definitions found for `{display}`.")

        pages = []
        for item in entries:
            # Clean up text
            definition = item.get("definition", "").replace("[", "").replace("]", "")
            example = item.get("example", "").strip().replace("[", "").replace("]", "")
            ups = item.get("thumbs_up", 0)
            downs = item.get("thumbs_down", 0)
            author = item.get("author", "Unknown")
            link = item.get("permalink")

            # Use the actual term for random entries
            entry_term = item.get("word", display)

            # Random colour for each embed
            rand_colour = discord.Colour(random.randint(0x000000, 0xFFFFFF))

            embed = discord.Embed(
                title=entry_term,
                url=link,
                description=definition or "No definition provided.",
                colour=rand_colour
            )
            embed.add_field(name="Example", value=example or "No example provided.", inline=False)
            embed.set_footer(text=f"👍 {ups}   👎 {downs}   •   Author: {author}")
            pages.append(embed)

        msg = await ctx.send(embed=pages[0])
        if len(pages) == 1:
            return

        await msg.add_reaction("◀️")
        await msg.add_reaction("▶️")

        index = 0

        def check(reaction, user):
            return (
                user == ctx.author
                and reaction.message.id == msg.id
                and str(reaction.emoji) in ("◀️", "▶️")
            )

        while True:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=120.0, check=check
                )
            except (asyncio.TimeoutError, asyncio.CancelledError):
                # Optionally clear reactions when pagination ends
                try:
                    await msg.clear_reactions()
                except discord.HTTPException:
                    pass
                break
            else:
                try:
                    await msg.remove_reaction(reaction, user)
                except discord.HTTPException:
                    pass

                if str(reaction.emoji) == "◀️":
                    index = (index - 1) % len(pages)
                else:
                    index = (index + 1) % len(pages)
                await msg.edit(embed=pages[index])
