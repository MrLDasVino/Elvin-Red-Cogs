
import aiohttp
import discord
from datetime import datetime

from discord import Color
from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify


class MealDB(commands.Cog):
    """Fetch recipes via TheMealDB API."""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        # Cleanly close our HTTP session when the cog unloads
        self.bot.loop.create_task(self.session.close())

    async def fetch_json(self, url: str) -> dict:
        """Helper to GET JSON from a URL."""
        async with self.session.get(url) as resp:
            resp.raise_for_status()
            return await resp.json()

    @commands.command(name="meal")
    async def meal(self, ctx, *, query: str = None):
        """
        Fetch a random meal or search by name.
        Usage:
          [p]meal random
          [p]meal <search term>
        """
        # Show help if no query or help flags passed
        if not query or query.lower() in ("help", "-h", "--help", "?"):
            return await ctx.send_help()

        # Choose endpoint
        if query.lower() == "random":
            url = "https://www.themealdb.com/api/json/v1/1/random.php"
        else:
            url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={query}"

        data = await self.fetch_json(url)
        meals = data.get("meals") or []
        if not meals:
            return await ctx.send(f"No meals found for `{query}`.")

        meal_data = meals[0]
        embed = await self.build_embed(meal_data)
        if not embed:
            return await ctx.send_help()

        await ctx.send(embed=embed)

    async def build_embed(self, meal: dict) -> discord.Embed:
        """Constructs a polished embed for a given meal dict."""
        title = meal["strMeal"]
        source_url = meal.get("strSource") or meal.get("strYoutube") or None
        category = meal.get("strCategory", "Unknown")
        cuisine = meal.get("strArea", "Unknown")
        tags = meal.get("strTags")

        embed = discord.Embed(
            title=title,
            url=source_url,
            description=f"Category: {category} • Cuisine: {cuisine}",
            color=Color.random(),
        )
        embed.timestamp = datetime.utcnow()

        # Optional Tags field
        if tags:
            tag_list = ", ".join(tag.strip() for tag in tags.split(","))
            embed.add_field(name="Tags", value=tag_list, inline=False)

        # Ingredients as plain text bullets
        ingredients = []
        for i in range(1, 21):
            name = meal.get(f"strIngredient{i}")
            measure = meal.get(f"strMeasure{i}")
            if name and name.strip():
                measure_text = measure.strip() if measure and measure.strip() else "—"
                ingredients.append(f"• {name.strip()}: {measure_text}")
        embed.add_field(name="Ingredients", value="\n".join(ingredients), inline=False)

        # Paginated Instructions
        instructions = meal.get("strInstructions", "No instructions provided.").strip()
        pages = list(pagify(instructions, page_length=1024))
        total = len(pages)
        for idx, page in enumerate(pages, start=1):
            field_name = f"Instructions ({idx}/{total})"
            embed.add_field(name=field_name, value=page, inline=False)

        # Banner image at bottom instead of thumbnail
        embed.set_image(url=meal["strMealThumb"])

        return embed
