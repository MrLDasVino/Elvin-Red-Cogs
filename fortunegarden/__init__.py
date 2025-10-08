from .fortunegarden import FortuneGarden

async def setup(bot):
    cog = FortuneGarden(bot)
    await bot.add_cog(cog)