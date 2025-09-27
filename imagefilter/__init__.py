from .imagefilter import ImageFilter

async def setup(bot):
    """Entry point for the cog."""
    await bot.add_cog(ImageFilter(bot))
