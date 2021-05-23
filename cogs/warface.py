import sqlalchemy
from discord.ext import commands

from PLyBot import Bot, Cog, Context
from db_session import SqlAlchemyBase, BaseConfigMix


class WarfaceConfig(SqlAlchemyBase, BaseConfigMix):
    __tablename__ = "warface_configs"

    guild_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('guilds.id'),
                                 primary_key=True, nullable=False)
    access = sqlalchemy.Column(sqlalchemy.String, nullable=False, default='{}')
    active_until = sqlalchemy.Column(sqlalchemy.Date, nullable=True, default=None)


class WarfaceCog(Cog, name="WarfaceStats"):
    def __init__(self, bot: Bot):
        super().__init__(bot, cls_config=WarfaceConfig)

    @commands.command()
    async def wf_user(self, ctx: Context):
        pass

    @commands.group(invoke_without_command=True)
    async def animals(self, ctx: Context, a, b):
        await ctx.send(f'3, 4 {a}, {b}')

    @animals.command(name='joke', short_doc="joking 1")
    async def joke1(self, ctx, a, b):
        """
        joke 1
        """
        await ctx.send(f'a random joke {a} {b}')

    @commands.command(name='joke', short_doc='joking 2')
    async def joke2(self, ctx, a, b):
        """
        joke2
        """
        await ctx.send(f'a random koke {a} {b}')


def setup(bot: Bot):
    bot.add_cog(WarfaceCog(bot))
