from .freegames import freegames  # noqa

async def setup(bot):
    cog = freegames(bot)
    await bot.add_cog(cog)