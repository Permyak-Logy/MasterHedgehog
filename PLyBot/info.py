import asyncio
from typing import Union

import discord
from discord.ext import commands

from .bot import Bot, Cog, Context
from .const import ALL_GOOD_TYPES


class InfoCog(Cog, name="Информация"):
    def __init__(self, bot: Bot):
        super().__init__(bot)

        help_cmd: commands.Command = self.bot.get_command("help")
        help_cmd.name = 'хелп'
        help_cmd.aliases = list(set(help_cmd.aliases) | {"помощь", "help", "h", "?"})
        help_cmd.cog = self
        help_cmd.help = 'Показывает информацию о команде или категории'

        self.bot.reload_command('help')

    @commands.Cog.listener('on_message')
    async def on_mention(self, message: discord.Message):
        if not self.bot.is_ready():
            return
        if self.bot.user.mentioned_in(message) and len(message.content.split()) == 1:
            await self.bot.get_command("info").invoke(await self.bot.get_context(message))

    @commands.command(name="инфо", aliases=["info", "i", "информация", "about"])
    async def info(self, ctx: Context):
        """
        Выдаёт информацию о боте
        """
        bot: Bot = ctx.bot
        owner = bot.get_user(403910550028943361)
        embed = discord.Embed(
            title=str(self.bot.user.name),
            colour=self.bot.colour_embeds,
            description=(
                f"Привет! Меня зовут {self.bot.name}! Я бот с огромным функционалом и разными возможностями.\n"
                f"\n"
                f"Мой префикс `{self.bot.command_prefix}`, но ты также можешь просто @обратиться ко мне. "
                f"Взгляни на команду `{self.bot.command_prefix}{self.bot.get_command('help')}`"
                f"для более детальной информации о моих возможностях или просто после команды прописать '?'.\n"
                f"||например `{self.bot.command_prefix}инфо ?` или `{self.bot.command_prefix}"
                f"{self.bot.get_command('help')} инфо`||"
            )
        )
        embed.add_field(name="Сборка", value=self.bot.version)
        embed.set_thumbnail(url=bot.user.avatar_url)
        if isinstance(owner, discord.User):
            embed.set_author(name=owner.name, icon_url=owner.avatar_url)
            embed.set_footer(text="PyPLy ©", icon_url=owner.avatar_url)
            embed.add_field(name="Мой разработчик", value=f"{owner}")
            embed.set_image(
                url="https://cdn.discordapp.com/attachments/832900181534965810/903237957362778152/PyPLy.png")
        await asyncio.sleep(1.5)
        await ctx.send(embed=embed)

    @commands.command(name="пинг", aliases=["ping"])
    async def ping(self, ctx: Context):
        """
        Высылает задержку между ботом и Discord
        """
        await ctx.send(embed=discord.Embed(title="Понг!", description=f"Задержка {round(self.bot.latency, 3) * 1000} "
                                                                      f"мс.",
                                           colour=self.bot.colour_embeds))

    @commands.command(name="пригласить", aliases=["invite"])
    async def invite(self, ctx: Context):
        """
        Отправляет ссылку для приглашения бота
        """
        link = await ctx.bot.invite_link
        await ctx.send(embed=discord.Embed(
            title="Нажми сюда чтобы меня добавить на свой сервер", description=f"||{link}||", url=link,
            colour=ctx.bot.colour_embeds).set_thumbnail(url=ctx.bot.user.avatar_url))

    # TODO: заглушено на время работ
    # @commands.command(name="синтакс", aliases=["syntax"])
    async def syntax(self, ctx: Context):
        """
        Показывает сообщение
        """
        embed = discord.Embed(
            title="Справка по оформлению команд",
            colour=self.bot.colour_embeds,
            description="Привет! Оформление моего синтаксиса команд достаточно простое.\n"
                        "Все команды состоят из префикса, названия команды и аргументов.\n"
                        "Вызов команды начинается "
        )
        await ctx.send(embed=embed)

    # @commands.command(name="чексинтакс", aliases=["checksyntax"])
    async def check_syntax(self, ctx: Context, *args: ALL_GOOD_TYPES):
        """
        Используйте эту команду для определения того что получит команда в качестве аргументов
        Проверить можно только первые 10 аргументов
        """

        # TODO: Пофиксить проверку (не определяется тип)

        embed = discord.Embed(
            title="Проверка на аргументы",
            description="Ниже представлены аргументы с их типами",
            colour=self.bot.colour_embeds
        )
        for i, arg in enumerate(args[:10]):
            embed.add_field(name=f"{i + 1}. {type(arg)}", value=arg)
        await ctx.send(embed=embed)

    @commands.command(name="видят", aliases=['see'])
    async def have_access(self, ctx: Context,
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
        emb = discord.Embed(
            title=f"Список участников имеющих доступ к каналу",
            colour=self.bot.colour_embeds,
            description=(
                    "\n".join(list(result)[:count]) +
                    ("" if len(result) - count < 0 else "\n... +" + str(len(result) - count)))
        )

        emb.add_field(name="Всего", value=str(len(result)))
        emb.add_field(name="Канал", value=channel.mention)
        await ctx.send(embed=emb)

    # @commands.command(name="префикс", aliases=['prefix'])
    async def set_prefix(self, ctx: Context, prefix: str):
        pass


def setup(bot: Bot):
    bot.add_cog(InfoCog(bot))
