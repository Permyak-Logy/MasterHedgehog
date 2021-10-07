from discord.ext import commands
from discord.ext.commands import BadArgument

from PLyBot import Cog, Bot, Context
from WarframeAPI import wf_api


async def convert(cls, _: Context, argument):
    if argument not in wf_api.get_platforms():
        raise BadArgument("Неизвестная платформа")
    return cls(argument)


wf_api.convert = classmethod(convert)


class WarframeCog(Cog, name="Warframe"):
    def __init__(self, bot: Bot):
        super(WarframeCog, self).__init__(bot)

    # noinspection PyUnusedLocal
    @commands.command()
    async def void_trader_info(self, ctx: Context, platform: wf_api = wf_api("pc")):
        """
        Возвращает информацию по торговцу бездны"""
        """
        {
        "id": "string",
        "activation": "2019-08-24T14:15:22Z",
        "expiry": "2019-08-24T14:15:22Z",
        "character": "string",
        "location": "string",
        "inventory": [
            {
            "item": "string",
            "ducats": 0,
            "credits": 0
            }
        ],
        "psId": "string",
        "active": true,
        "startString": "string",
        "endString": "string"
        }
        """
        data = platform.get_void_trader_info()


def setup(bot: Bot):
    bot.add_cog(WarframeCog(bot))
