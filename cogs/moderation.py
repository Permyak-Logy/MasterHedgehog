import asyncio
from typing import Optional
from typing import Union

import discord
import sqlalchemy
from discord.ext import commands

import db_session
from PLyBot import Bot
from PLyBot import Cog, join_string, get_time_from_string, BotEmbed
from db_session import SqlAlchemyBase, BaseConfigMix, NONE
from db_session.base import Member


# TODO: Поиск удалённых сообщений
class ModerationConfig(SqlAlchemyBase, BaseConfigMix):
    __tablename__ = "moderation_configs"

    guild_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('guilds.id'),
                                 primary_key=True, nullable=False)
    mute_role = sqlalchemy.Column(sqlalchemy.Integer, nullable=True, unique=True)
    access = sqlalchemy.Column(sqlalchemy.String, nullable=False, default='{}')
    active_until = sqlalchemy.Column(sqlalchemy.Date, nullable=True, default=None)

    def __str__(self):
        return f'{self.__class__.__name__}(id={self.guild_id} mute_role={self.mute_role})'

    def __repr__(self):
        return self.__class__.__name__

    def get_mute_role(self, bot: Bot) -> Union[discord.Role, None]:
        guild = self.get_guild(bot)
        if self.mute_role != NONE and isinstance(guild, discord.Guild):
            return guild.get_role(self.mute_role)

    def set_mute_role(self, role: discord.Role):
        if isinstance(role, discord.Role):
            self.mute_role = role.id
        else:
            self.mute_role = None


class ModerationCog(Cog, name="Модерация"):
    """
    Модуль модерации. Он содержит в себе простой набор команд для модерирования сервера.
    Если вы раннее не работали с этим модулем, то вам следует установить для начала роль для мьюта
    с помощью `!!мьютроль @Роль`, иначе вы не сможете воспользоваться командой `мьют`.

    В некоторые команды можно указывать время. Это время указывается в виде Xq где X это число (Если дробь то точку
    использовать), а q это первая буква единиц измерений с маленькой буквы. На данный момент доступно
    определение дней (д), часов (ч), минут (м), секунд (с).
    """

    def __init__(self, bot: Bot):
        super().__init__(bot, cls_config=ModerationConfig, emoji_icon='⚙️')

    def get_config(self, session: db_session.Session, guild: Union[discord.Guild, int]) -> Optional[ModerationConfig]:
        return super().get_config(session, guild)

    @commands.command(name='забанить', aliases=['ban', 'бан', 'заблокировать', 'заблокать', 'блок'])
    @commands.cooldown(1, 5)
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def _cmd_ban(self, ctx: commands.Context, member: discord.Member, time: str = "F", *reason: str):
        """
        Банит участника сервера. Если был указано время не равное "F",
        то он забанит лишь на это время, а после снимает бан.
        Можно также указать причину, но это не обязательно.
        """

        reason = join_string(reason, "Не указана")
        seconds = get_time_from_string(time).total_seconds()
        assert seconds >= 1 or time == "F", "Время должно быть более 1 сек или равно быть 'F' (Бессрочно)"
        guild = ctx.guild
        if guild.owner != ctx.author != self.bot.user:
            assert ctx.author.top_role > member.top_role, "Вы можете так делать только с людьми ниже вас"

        assert guild.get_member(self.bot.user.id).top_role > member.top_role, \
            "Извини. У меня не достаточно прав"

        await guild.ban(user=member, reason=reason)

        embed = BotEmbed(ctx=ctx,
                         title="Операция успешна",
                         colour=discord.colour.Color.from_rgb(0, 255, 0),
                         description=f"Участник {member.mention} был забанен по причине \"{reason}\" "
                                     f"{'навсегда' if time == 'F' else f'на {time}'}"
                         )
        await ctx.send(embed=embed)

        if seconds > 0:
            await asyncio.sleep(seconds)
            try:
                await guild.unban(member, reason="Закончилось время бана")
            finally:
                pass

    @commands.command(name='разбанить', aliases=['unban', 'разбан', 'разблокировать', 'разблокать', 'разблок'])
    @commands.cooldown(1, 5)
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def _cmd_unban(self, ctx: commands.Context, member: discord.Member, *reason):
        """
        Разбанивает  участника по указанной причине. (Указывать её не обязательно)
        """

        reason = join_string(reason, "Не указана")

        guild: discord.Guild = ctx.guild
        if guild.owner != ctx.author != self.bot.user:
            assert ctx.author.top_role > member.top_role, "Вы можете так делать только с людьми ниже вас"

        assert guild.get_member(self.bot.user.id).top_role > member.top_role, \
            "Извини. У меня не достаточно прав"

        await guild.unban(user=member, reason=reason)

        embed = BotEmbed(ctx=ctx,
                         title="Операция успешна",
                         colour=discord.colour.Color.from_rgb(0, 255, 0),
                         description=f"Участник {member.mention} был разбанен по причине \"{reason}\""
                         )
        await ctx.send(embed=embed)

    @commands.command(name='кикнуть', aliases=['kick', 'кик', 'пнуть', 'выпнуть'])
    @commands.cooldown(1, 5)
    @commands.guild_only()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def _cmd_kick(self, ctx: commands.Context, member: discord.Member, *reason: str):
        """
        Исключает участника по указанной причине. (Указывать её не обязательно)
        """

        reason = join_string(reason, "Не указана")

        if ctx.guild.owner != ctx.author != self.bot.user:
            assert ctx.author.top_role > member.top_role, \
                "Вы можете так делать только с людьми ниже вас"

        assert ctx.guild.get_member(self.bot.user.id).top_role > member.top_role, \
            "Извини. У меня не достаточно высокая роль"

        await ctx.guild.kick(user=member, reason=reason)

        embed = BotEmbed(ctx=ctx,
                         title="Операция успешна",
                         colour=discord.colour.Color.from_rgb(0, 255, 0),
                         description=f"Участник {member.mention} был исключён по причине \"{reason}\""
                         )
        await ctx.send(embed=embed)

    # TODO: Возможность послать ^C для остановки
    @commands.command(name='очистить', aliases=['clear', 'purge', 'prg', 'cls'])
    @commands.cooldown(3, 1)
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def _cmd_purge(self, ctx: commands.Context, limit: int, *check: str):
        """
        Чистит канал с лимитом очистки сообщений и проверяющей функцией check
        Если limit == -1 то очистка будет всего канала (msg)
        """
        async with ctx.typing():
            if await self.bot.is_owner(ctx.author):
                check = eval(f'lambda msg: {" ".join(check)}') if check else None
            else:
                check = None

            await ctx.message.delete()

            if limit == -1:
                limit = None

            assert limit is None or limit >= 0, "Указанный лимит должен быть >= 0  (или == -1)"
            await ctx.channel.purge(limit=limit, check=check)

            embed = BotEmbed(ctx=ctx,
                             title="Операция успешна",
                             colour=discord.colour.Color.from_rgb(0, 255, 0),
                             description=(
                                 f"Очищено не более {limit} сообщений в канале {ctx.channel.mention}"
                                 if isinstance(limit, int) else
                                 f"Очищены все сообщения в канале {ctx.channel.mention}"
                             ))

        await ctx.send(embed=embed, delete_after=10)

    # TODO: Добавить запоминание предупреждений, после чего банить участника
    @commands.command(name='пред', aliases=['warn'])
    @commands.cooldown(1, 5)
    @commands.guild_only()
    async def _cmd_warn(self, ctx: commands.Context, member: discord.Member, *reason: str):
        """
        Высылает сообщение с предупреждением участнику и указанной причине (Указывать не обязательно)
        """

        reason = join_string(reason, "Не указана")

        if ctx.guild.owner != ctx.author != self.bot.user:
            assert ctx.author.top_role > member.top_role, "Вы можете так делать только с людьми ниже вас"

        await member.send(embed=BotEmbed(ctx=ctx,
                                         title="Предупреждение",
                                         description=f"Вам было сделано предупреждение по причине \"{reason}\""
                                                     f"на сервере {ctx.guild}"
                                         ))

        embed = BotEmbed(ctx=ctx,
                         title="Операция успешна",
                         colour=discord.colour.Color.from_rgb(0, 255, 0),
                         description=f"Участник {member.mention} был предупреждён по причине \"{reason}\""
                         )

        await ctx.send(embed=embed)

    # TODO: Сделать больше информации
    @commands.command(name='юзер', aliases=['user', 'пользователь'])
    @commands.guild_only()
    async def _cmd_user(self, ctx: commands.Context, user: discord.Member = None):
        if not user:
            user = ctx.author

        embed = BotEmbed(ctx=ctx, title=f"Пользователь: \""
                                        f"{user.display_name if user.id != 403910550028943361 else 'Не твоё дело'}\"",
                         colour=discord.Color.from_rgb(0, 255, 0),
                         description="Запрос на данные о пользователе")
        embed.set_thumbnail(url=user.avatar_url)

        embed.add_field(name="Никнейм", value=(user.name if user.id != 403910550028943361 else "*#^@ERROR7^@#"))

        embed.add_field(name="Бот", value=str(user.bot) if user.id != 403910550028943361 else "Да хрен знает")
        if hasattr(user, "status"):
            if user.status == discord.Status.online:
                status = "🟢 Онлайн"
            elif user.status == discord.Status.idle:
                status = "🟡 Не активен"
            elif user.status == discord.Status.do_not_disturb:
                status = "🔴 Не беспокоить"
            else:
                status = "⚫ Оффлайн"
            embed.add_field(name="Статус", value=status if user.id != 403910550028943361 else "Не скажу")

        embed.add_field(name="Дата регистрации", value=(user.created_at.strftime('%d/%m/%Y %H:%M:%S')
                                                        if user.id != 403910550028943361 else "Думай сам"))
        member = ctx.guild.get_member(user.id)
        if isinstance(member, discord.Member):
            embed.add_field(name="На сервере с", value=(member.joined_at.strftime('%d/%m/%Y %H:%M:%S')
                                                        if user.id != 403910550028943361 else "01.01.0001"))
            with db_session.create_session() as session:
                session: db_session.Session
                embed.add_field(name="Вижу на серверах",
                                value=str(len(session.query(Member).filter(Member.id == user.id).all())))
        await ctx.send(embed=embed)

    @commands.command(name='мьют', aliases=['mute', 'мут'])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def _cmd_mute(self, ctx: commands.Context, member: discord.Member, time: str = "F", *reason: str):
        """
        Мьютит участника (time указывается в виде числа и единиц измерений
        например: 1ч, 2д, 3с, 120м. (Единицы измерения: д, ч, м, с)
        или можно указать 'F' и тогда будет срок бессрочно)
        """
        reason = join_string(reason, "Не указана")
        seconds = get_time_from_string(time).total_seconds()
        assert seconds >= 1 or time == "F", "Время должно быть более 1 сек или равно быть 'F' (Бессрочно)"
        guild: discord.Guild = ctx.guild
        if guild.owner != ctx.author != self.bot.user:
            assert ctx.author.top_role > member.top_role, "Вы можете так делать только с людьми ниже вас"

        assert guild.get_member(self.bot.user.id).top_role > member.top_role, \
            "Извини. У меня не достаточно прав"

        session = db_session.create_session()
        config = self.get_config(session, guild)
        role = config.get_mute_role(ctx.bot)
        session.close()

        assert role is not None, "Нет роли для мьюта"
        assert role not in member.roles, "Участник и так замьючен"

        await member.add_roles(role, reason=reason)

        embed = BotEmbed(ctx=ctx,
                         title="Операция успешна",
                         colour=discord.colour.Color.from_rgb(0, 255, 0),
                         description=f"Участник {member.mention} был замьючен по причине \"{reason}\" "
                                     f"{'навсегда' if time == 'F' else f'на {time}'}"
                         )
        await ctx.send(embed=embed)
        if time != "F":
            await asyncio.sleep(seconds)
            try:
                await member.remove_roles(role, reason=f"Закончилось время мьюта (Причина: {reason})")
            finally:
                pass

    @commands.command(name='размьют', aliases=['unmute', 'размут'])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def _cmd_unmute(self, ctx: commands.Context, member: discord.Member, *reason: str):
        """
        Снимает мьют с участника если таковой имеется
        """
        reason = join_string(reason, default="Не указана")
        guild: discord.Guild = ctx.guild
        if guild.owner != ctx.author != self.bot.user:
            assert ctx.author.top_role > member.top_role, "Вы можете так делать только с людьми ниже вас"

        assert guild.get_member(self.bot.user.id).top_role > member.top_role, \
            "Извини. У меня не достаточно прав"

        session = db_session.create_session()
        config = self.get_config(session, guild)
        role = config.get_mute_role(ctx.bot)
        session.close()

        assert role is not None, "Нет роли для мьюта"
        assert role in member.roles, "Участник и так не в мьюте"

        await member.remove_roles(role, reason=reason)

        embed = BotEmbed(ctx=ctx,
                         title="Операция успешна",
                         colour=discord.colour.Color.from_rgb(0, 255, 0),
                         description=f"Участник {member.mention} был размьючен по причине \"{reason}\""
                         )
        await ctx.send(embed=embed)

    @commands.command(name='мьютроль', aliases=['muterole', 'мутроль'])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def _cmd_set_mute_role(self, ctx: commands.Context, role: discord.Role = None):
        """
        Устанавливает роль для мьюта
        """
        session = db_session.create_session()
        config = self.get_config(session, ctx.guild)
        config.set_mute_role(role)
        session.commit()
        session.close()
        if role is not None:
            await ctx.send(embed=BotEmbed(ctx=ctx, title="Успешно!",
                                          description=f"Роль {role} установленна как\"Мьют роль\" "))
        else:
            await ctx.send(embed=BotEmbed(ctx=ctx, title="Успешно!", description=f"Роль для мьюта сброшена"))


async def setup(bot: Bot):
    await bot.add_cog(ModerationCog(bot))
