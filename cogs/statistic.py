from datetime import datetime

import discord
import sqlalchemy
from discord.ext import commands

from PLyBot import Bot, Cog, HRF, Context
from db_session import SqlAlchemyBase, BaseConfigMix, MIN_DATETIME


class StatisticConfig(SqlAlchemyBase, BaseConfigMix):
    __tablename__ = "statistic_configs"

    guild_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('guilds.id'),
                                 primary_key=True, nullable=False)
    access = sqlalchemy.Column(sqlalchemy.String, nullable=False, default='{}')
    active_until = sqlalchemy.Column(sqlalchemy.Date, nullable=True, default=MIN_DATETIME)


class StatisticCog(Cog, name='Статистика'):
    """
    Модуль для получения различных случайностей!
    """

    def __init__(self, bot: Bot):
        super().__init__(bot, cls_config=StatisticConfig)

    @commands.command()
    @commands.guild_only()
    async def stats_guild(self, ctx: commands.Context):
        """
        Показывает статистику сервера
        """
        embed = discord.Embed(title=f"Статистика бота {ctx.me.display_name}", colour=self.bot.colour_embeds)
        embed.set_thumbnail(url=ctx.me.avatar_url)
        count_members = len(ctx.guild.members)
        count_bots = len(list(filter(lambda x: not x.bot, ctx.guild.members)))

        embed.add_field(
            name="Участники",
            value=(f"Всего - {count_members}\n"
                   f"Людей - {count_members - count_bots}\n"
                   f"Ботов - {count_bots}"))

        embed.add_field(
            name="Активность",
            value=(f"В сети - {1}\n"
                   f"Не активны - {2}\n"
                   f"Не беспокоить - {3}\n"
                   f"Не в сети - {4}"))

        embed.add_field(
            name="Каналы",
            value=(f"Категорий - {1}\n"
                   f"Каналов - {2}\n"
                   f"Тестовых - {3}\n"
                   f"Голосовых - {4}\n"
                   f""))

        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def stats_role(self, ctx: commands.Context, role: discord.Role):
        """
        Показывает статистику роли на сервере
        """

    @commands.command()
    async def stats_bot(self, ctx: Context):
        """
        Показывает статистику бота
        """

        embed = discord.Embed(title=f"Статистика бота {ctx.me.display_name}", colour=self.bot.colour_embeds)
        embed.set_thumbnail(url=ctx.me.avatar_url)
        embed.add_field(name="Серверов под наблюдением", value=str(len(self.bot.guilds)))
        embed.add_field(name="Каналов под наблюдением", value=str(len(set(self.bot.get_all_channels()))))
        embed.add_field(name="Людей под наблюдением", value=str(len(self.bot.users)))
        embed.add_field(name="Выполнено команд", value=str(self.bot.count_invokes + 1))

        embed.add_field(name="Возраст", value=HRF.time(datetime.now() - self.bot.user.created_at, sep="\n") or "-")
        embed.add_field(name="Работает", value=HRF.time(datetime.now() - self.bot.started) or "-")

        embed.add_field(name="Модулей", value=str(len(self.bot.cogs)))
        embed.add_field(name="Команд", value=str(len(self.bot.commands)))

        await ctx.send(embed=embed)


def setup(bot: Bot):
    bot.add_cog(StatisticCog(bot))
