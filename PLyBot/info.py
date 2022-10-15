import asyncio
from typing import Union, Optional

import discord
from discord.ext import commands

import db_session
from db_session.base import Guild
from .bot import Bot, Cog, Context
from .const import ALL_GOOD_TYPES
from .embed import BotEmbed


class InfoCog(Cog, name="Информация"):
    def __init__(self, bot: Bot):
        super().__init__(bot, emoji_icon='📌')

        help_cmd: commands.Command = self.bot.get_command("help")
        help_cmd.name = 'хелп'
        help_cmd.aliases = list(set(help_cmd.aliases) | {"помощь", "help", "h", "?"})
        help_cmd.cog = self
        help_cmd.help = 'Показывает информацию о команде или категории'
        help_cmd.callback.__annotations__["cog|cmd"] = None

        self._cmd_prefix_set.enabled = bot.using_db

        self.bot.reload_command('help')

    @commands.Cog.listener('on_guild_join')
    async def hello_guild(self, guild: discord.Guild, *,
                          channel: Optional[Union[discord.DMChannel, discord.TextChannel]]):
        channel = channel or guild.system_channel
        if channel is None:
            return

        bot: Bot = self.bot
        prefix = bot.prefix_guild(guild)
        owner = bot.get_user(403910550028943361)
        embed = BotEmbed(
            title=str(self.bot.user.name),
            colour=self.bot.colour,
            description=(
                f"Привет! Меня зовут {self.bot.name}! Я бот с огромным функционалом и разными возможностями.\n"
                f"\n"
                f"Мой префикс `{prefix}`, но ты также можешь просто @обратиться ко мне.\n"
                f"Взгляни на команду `{prefix}{self.bot.get_command('help')}`"
                f"для более детальной информации о моих возможностях или просто после команды напиши `?`.\n"
                f"||например `{prefix}{self._cmd_info} ?` или "
                f"`{prefix}{self.bot.get_command('help')} {self._cmd_info}`||")
        )
        embed.add_field(name="Сборка", value=self.bot.version)
        embed.set_thumbnail(url=bot.user.avatar_url)
        if isinstance(owner, discord.User):
            embed.set_author(name=owner.name, icon_url=owner.avatar_url)
            if self.bot.footer:
                embed.set_footer(**self.bot.footer)
            embed.add_field(name="Мой разработчик", value=f"{owner}")
            embed.set_image(
                url="https://cdn.discordapp.com/attachments/653543360161644545/911597130412593162/Master_.png")
        await channel.send(embed=embed)

    @commands.Cog.listener('on_message')
    async def on_mention(self, message: discord.Message):
        if not self.bot.is_ready():
            return
        if self.bot.user.mentioned_in(message) and len(message.content.split()) == 1:
            ctx: Context = await self.bot.get_context(message)
            ctx.prefix = ctx.prefix or await self.bot.get_prefix(message)
            await self.bot.get_command("info").invoke(ctx)

    @commands.command(name="инфо", aliases=["info", "i", "информация", "about"])
    async def _cmd_info(self, ctx: Context):
        """
        Выдаёт информацию о боте
        """
        await self.hello_guild(ctx.guild, channel=ctx.channel)

    @commands.command(name="пинг", aliases=["ping"])
    async def _cmd_ping(self, ctx: Context):
        """
        Высылает задержку между ботом и Discord
        """
        await ctx.reply(
            embed=BotEmbed(ctx=ctx, title="Понг!", description=f"Задержка {round(self.bot.latency, 3) * 1000} "
                                                               f"мс.",
                           colour=self.bot.colour))

    @commands.command(name="пригласить", aliases=["invite"])
    async def _cmd_invite(self, ctx: Context):
        """
        Отправляет ссылку для приглашения бота
        """
        link = await ctx.bot.invite_link
        await ctx.reply(embed=BotEmbed(ctx=ctx,
                                       title="Нажми сюда чтобы меня добавить на свой сервер", url=link,
                                       colour=ctx.bot.colour).set_thumbnail(url=ctx.bot.user.avatar_url))

    @commands.command(name="сервер", aliases=['server'])
    @commands.guild_only()
    async def _cmd_server(self, ctx: Context):
        """Показывает информацию о сервере: количество участников, владельца, уровень проверки и так далее."""
        guild = ctx.guild

        statuses = list(map(lambda m: m.status, guild.members))
        types = list(map(lambda m: m.bot, guild.members))

        embed = BotEmbed(ctx=ctx,
                         title=f"Информация о сервере {guild}", colour=self.bot.colour).set_thumbnail(
            url=guild.icon_url)
        embed.add_field(name="Участники", value=f"\\👥 Всего: **{guild.member_count}**\n"
                                                f"\\👤 Людей: **{types.count(False)}**\n"
                                                f"\\🤖 Ботов: **{types.count(True)}**")

        statuses_text = ""
        count_online = statuses.count(discord.Status.online)
        count_idle = statuses.count(discord.Status.idle)
        count_dnd = statuses.count(discord.Status.dnd)
        count_offline = statuses.count(discord.Status.offline)
        if count_online:
            statuses_text += f"\\🟢 В сети: **{count_online}**\n"
        if count_idle:
            statuses_text += f"\\🟠 Не активен: **{count_idle}**\n"
        if count_dnd:
            statuses_text += f"\\🔴 Не беспокоить: **{count_dnd}**\n"
        if count_offline:
            statuses_text += f"\\⚫ Не в сети: **{count_offline}**\n"
        embed.add_field(name="По статусам:", value=statuses_text)

        channels_text = f"\\💬 Всего: {guild.channels.__len__()}\n"
        if guild.text_channels:
            channels_text += f"**#** Текстовых: **{guild.text_channels.__len__()}**\n"
        if guild.voice_channels:
            channels_text += f"\\🔊 Голосовых: **{guild.voice_channels.__len__()}**\n"
        if guild.stage_channels:
            channels_text += f"\\📣 Stage: **{guild.stage_channels.__len__()}**\n"
        embed.add_field(name="Каналы:", value=channels_text)

        embed.add_field(name="Владелец", value=str(guild.owner))
        embed.add_field(name="Уровень проверки:", value=str(guild.mfa_level or "Отсутствует"))
        embed.add_field(name="Дата создания:", value=str(guild.created_at.date()))
        embed.set_footer(text=f"ID: {guild.id}")

        await ctx.reply(embed=embed)

    @commands.command(name="инвайтинфо", aliase=['inviteinfo'], enabled=False)
    async def _cmd_invite_info(self, ctx: Context):
        """Показывает более детальную информацию о ссылке приглашении"""

    # TODO: заглушено на время работ
    @commands.command(name="синтакс", aliases=["syntax"], enabled=False)
    async def _cmd_syntax(self, ctx: Context):
        """
        Показывает сообщение
        """
        embed = BotEmbed(ctx=ctx,
                         title="Справка по оформлению команд",
                         colour=self.bot.colour,
                         description="Привет! Оформление моего синтаксиса команд достаточно простое.\n"
                                     "Все команды состоят из префикса, названия команды и аргументов.\n"
                                     "Вызов команды начинается "
                         )
        await ctx.send(embed=embed)

    @commands.command(name="чексинтакс", aliases=["checksyntax"], enabled=False)
    async def _cmd_check_syntax(self, ctx: Context, *args: ALL_GOOD_TYPES):
        """
        Используйте эту команду для определения того что получит команда в качестве аргументов
        Проверить можно только первые 10 аргументов
        """

        # TODO: Пофиксить проверку (не определяется тип)

        embed = BotEmbed(ctx=ctx,
                         title="Проверка на аргументы",
                         description="Ниже представлены аргументы с их типами",
                         colour=self.bot.colour
                         )
        for i, arg in enumerate(args[:10]):
            embed.add_field(name=f"{i + 1}. {type(arg)}", value=arg)
        await ctx.send(embed=embed)

    @commands.command(name="видят", aliases=['see'], enabled=False)
    async def _cmd_have_access(self, ctx: Context,
                               channel: Union[discord.VoiceChannel, discord.TextChannel, discord.StageChannel]):
        """
        Показывает участников которые видят указанный канал
        """
        result = set()
        for member in ctx.guild.members:
            member: discord.Member
            if member.permissions_in(channel).view_channel:
                result.add(member.mention)

        count = 15
        emb = BotEmbed(ctx=ctx,
                       title=f"Список участников имеющих доступ к каналу",
                       colour=self.bot.colour,
                       description=(
                               "\n".join(list(result)[:count]) +
                               ("" if len(result) - count < 0 else "\n... +" + str(len(result) - count)))
                       )

        emb.add_field(name="Всего", value=str(len(result)))
        emb.add_field(name="Канал", value=channel.mention)
        await ctx.send(embed=emb)

    @commands.group('prefix')
    @commands.has_guild_permissions(administrator=True)
    async def _group_prefix(self, ctx: commands.Context):
        embed = BotEmbed(ctx=ctx, description=f"Префикс сервера: `{ctx.prefix}`",
                         colour=self.bot.colour)
        await ctx.reply(embed=embed)

    @_group_prefix.command('set', enabled=False)
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    async def _cmd_prefix_set(self, ctx: commands.Context, new_prefix: str = None):
        """Устанавливает новый префикс в гильдию. Если хотите сбрость, то оставьте поле new_prefix пустым"""
        assert "%" not in new_prefix, f"Префикс содержит запрещённые символы: %"
        with db_session.create_session() as session:
            guild_data = Guild.get(session, ctx.guild)
            guild_data.command_prefix = new_prefix
            session.commit()
        embed = BotEmbed(ctx=ctx, description=f"Установлен новый префикс: `{new_prefix or self.bot.default_prefix}`",
                         colour=self.bot.colour)
        await ctx.reply(embed=embed)


async def setup(bot: Bot):
    await bot.add_cog(InfoCog(bot))
