import asyncio
import random

import discord
import sqlalchemy
from discord.errors import NotFound
from discord.ext import commands

import db_session
from PLyBot import Bot, Cog, join_string, HRF, BotEmbed, Context
from db_session import SqlAlchemyBase, BaseConfigMix


class LotteryConfig(SqlAlchemyBase, BaseConfigMix):
    __tablename__ = "lottery_configs"

    guild_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('guilds.id'),
                                 primary_key=True, nullable=False)
    access = sqlalchemy.Column(sqlalchemy.String, nullable=False, default='{}')
    active_until = sqlalchemy.Column(sqlalchemy.Date, nullable=True, default=None)


# TODO: Русифицировать команды и Сделать embed по цвету бота
class LotteryCog(Cog, name="Лотереи"):
    """
    Модуль для розыгрышей призов. В нём вы можете разыграть какую либо роль.
    """

    def __init__(self, bot: Bot):
        super().__init__(bot, cls_config=LotteryConfig, emoji_icon='🎉')

    # TODO: Заглушка
    @commands.command('розыгрыш_денег', aliases=['add_lottery_moneys', 'lottery_moneys'], enabled=False)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _cmd_add_raffle_moneys(self, ctx: Context, moneys: int, seconds: int, *title: str):
        """
        Создаёт розыгрыш на деньги (seconds в сек, title не обязательно указывать)
        (**!!ВНИМАНИЕ** Необходим доступный модуль 'Экономика')
        """

        title = join_string(title, f"Внимание! Денежный розыгрыш!")
        assert seconds >= 0, "Время должно быть >= 0"
        await self._handle_raffle_moneys(ctx, moneys, seconds, title)

    @staticmethod
    async def _handle_raffle_moneys(ctx: Context, moneys: int, delay: int, title: str):
        economy_cog: Cog = ctx.bot.get_cog('Экономика')
        assert economy_cog is not None, "Для работы этой команды необходим подключённый модуль 'Экономика'"
        assert await economy_cog.cog_check(ctx), "Вам не доступна эта команда"

        from .economy import EconomyCog, Balance
        economy_cog: EconomyCog

        with db_session.create_session() as session:
            config = economy_cog.get_config(session, ctx.guild)
            emote = "✅"
            embed = BotEmbed(ctx=ctx,
                             title=title,
                             description=f"Для участия нажмите на {emote}",
                             colour=discord.colour.Color.purple()
                             )
            embed.add_field(name="Сумма", value=HRF.number(moneys) + " " + config.currency_icon)
            embed.add_field(name="Итоги через",
                            value=f"{delay // 60 // 60} ч. {delay // 60 % 60} мин. {delay % 60} сек.")
            message = await ctx.send(embed=embed)
            await message.add_reaction(emote)

        await asyncio.sleep(delay)

        try:
            message: discord.Message = await message.channel.fetch_message(message.id)
        except NotFound:
            return

        for reaction in message.reactions:
            reaction: discord.Reaction
            if reaction.emoji != emote:
                continue
            members = list(filter(lambda x: x is not None,
                                  map(lambda m: message.guild.get_member(m.id),
                                      filter(lambda u: not u.bot, await reaction.users().flatten()))))
            if not members:
                break
            member = random.choice(members)
            with db_session.create_session() as session:
                config = economy_cog.get_config(session, ctx.guild)
                embed = BotEmbed(ctx=ctx,
                                 title="И у нас есть призёр!",
                                 description=f"{member.mention} получает {HRF.number(moneys)} "
                                             f"{config.currency_icon} на счёт банка",
                                 colour=discord.colour.Color.dark_purple()
                                 )
                await ctx.send(embed=embed)
                Balance.get(session, member).add_dep(moneys)
                session.commit()
            break
        await message.delete()

    @staticmethod
    async def _handle_raffle(ctx: Context, role: discord.Role, delay: int, title: str):
        emote = "✅"
        embed = BotEmbed(ctx=ctx,
                         title=title,
                         description=f"Для участия нажмите на {emote}",
                         colour=discord.colour.Color.purple()
                         )
        embed.add_field(name="Роль", value=role.mention)
        embed.add_field(name="Итоги через", value=f"{delay} сек.")
        message = await ctx.send(embed=embed)
        await message.add_reaction(emote)
        await asyncio.sleep(delay)

        try:
            message: discord.Message = await message.channel.fetch_message(message.id)
        except NotFound:
            return

        for reaction in message.reactions:
            reaction: discord.Reaction
            if reaction.emoji != emote:
                continue
            members = list(filter(lambda x: x is not None,
                                  map(lambda m: message.guild.get_member(m.id),
                                      filter(lambda u: not u.bot, await reaction.users().flatten()))))
            if not members:
                break
            member = random.choice(members)
            embed = BotEmbed(ctx=ctx,
                             title="И у нас есть призёр!",
                             description=f"{member.mention} получает роль {role.mention}",
                             colour=discord.colour.Color.dark_purple()
                             )
            await ctx.send(embed=embed)
            await member.add_roles(role)
            break
        await message.delete()

    @commands.cooldown(1, 5)
    @commands.command(name='лотерея', aliases=['add_lottery', 'lottery'])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def _cmd_lottery(self, ctx: Context, role: discord.Role, seconds: int, *title: str):
        """
        Создаёт розыгрыш на роль (seconds в сек, title не обязательно указывать)
        """

        title = join_string(title, f"Внимание! Розыгрыш на роль!")
        assert seconds >= 0, "Время должно быть >= 0"

        assert ctx.author.top_role > role or ctx.author.guild_permissions.administrator, \
            "Указанная роль должна быть ниже вашей"

        assert ctx.guild.get_member(self.bot.user.id).top_role > role, \
            "Указанная роль слишком высокая для меня"

        await self._handle_raffle(ctx, role, seconds, title)


async def setup(bot: Bot):
    await bot.add_cog(LotteryCog(bot))
