from .pickerwheel import PickerWheel

async def setup(bot):
    cog = PickerWheel(bot)
    await bot.add_cog(cog)

