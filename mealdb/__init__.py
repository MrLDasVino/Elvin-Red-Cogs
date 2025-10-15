from .mealdb import MealDB

async def setup(bot):

    await bot.add_cog(MealDB(bot))