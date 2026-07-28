from .fishrpg import FishRPG


async def setup(bot):
    await bot.add_cog(FishRPG(bot))
