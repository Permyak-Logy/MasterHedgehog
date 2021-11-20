from PLyBot import Bot, Cog, Context
from db_session import SqlAlchemyBase, BaseConfigMix
from sqlalchemy import Column, Integer, String, Date, ForeignKey
from discord.ext import commands
import discord


class ConfigCog(SqlAlchemyBase, BaseConfigMix):
    __tablename__ = "config"

    guild_id = Column(Integer, ForeignKey('guilds.id'), primary_key=True, nullable=False)
    access = Column(String, nullable=False, default='{}')
    active_until = Column(Date, nullable=True, default=None)


class ExpCog(Cog):
    def __init__(self, bot: Bot):
        super().__init__(bot, cls_config=ConfigCog)

    @commands.group()
    async def group1(self, ctx: Context, *, args):
        await ctx.reply('Использована команда group1 ' + args)

    @group1.command()
    async def cmd(self, ctx: Context):
        await ctx.reply('Использована команда cmd')


def setup(bot: Bot):
    bot.add_cog(ExpCog(bot))
