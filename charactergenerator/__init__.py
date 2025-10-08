from .charactergenerator import CharacterGenerator

async def setup(bot):
    await bot.add_cog(CharacterGenerator(bot))
