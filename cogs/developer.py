import argparse
import asyncio
import datetime
import os
import subprocess
import sys

import discord
from discord.errors import Forbidden
from discord.ext import commands

import db_session
from PLyBot import Bot, Cog, ApiKey, join_string, Context
from db_session.base import Guild
from db_session.const import MIN_DATETIME

activate_parser = argparse.ArgumentParser()
activate_parser.add_argument('-A', action="store_true")


# TODO: Вывод логов
# TODO: Русифицировать команды
class DeveloperCog(Cog, name="Для разработчиков"):
    def __init__(self, bot: Bot):
        super().__init__(bot, emoji_icon="🛠️")

    @commands.group(name='sudo', alaises=['su'])
    @commands.is_owner()
    async def _group_sudo(self, ctx: Context):
        """Вызов root команд"""
        await ctx.just_send_help()

    @_group_sudo.command(name='activate', aliases=['act'])
    @commands.is_owner()
    async def activate(self, ctx: Context, *, guild: discord.Guild = None):
        """
        Активирует на бессрочное использование всех модулей на сервере
        """
        guild: discord.Guild = guild or ctx.guild
        assert guild, "Не указан сервер"
        cogs = list(filter(bool, map(self.bot.get_cog, self.bot.cogs)))
        activated = []
        with db_session.create_session() as session:
            for cog in cogs:
                if not (isinstance(cog, Cog) and cog.cls_config is not None):
                    continue
                config = cog.get_config(session, guild)
                if not hasattr(config, "active_until"):
                    continue
                config.active_until = None
                activated.append(f"`{cog.qualified_name}`")
            session.commit()
        activated = " | ".join(activated)
        embed = discord.Embed(title="Успешно!", description=f'На сервере были успешно активированы модули:\n\n'
                                                            f'{activated}', colour=self.bot.colour_embeds)
        await ctx.send(embed=embed)

    @_group_sudo.command(aliases=['deact'])
    @commands.is_owner()
    async def deactivate(self, ctx: Context, *, guild: discord.Guild = None):
        """
        Деактивирует на бессрочное использование указанный модуль
        """
        guild: discord.Guild = guild or ctx.guild
        assert guild, "Не указан сервер"
        cogs = list(filter(bool, map(self.bot.get_cog, self.bot.cogs)))

        activated = []
        with db_session.create_session() as session:
            for cog in cogs:
                if not (isinstance(cog, Cog) and cog.cls_config is not None):
                    continue
                config = cog.get_config(session, guild)
                if not hasattr(config, "active_until"):
                    continue
                config.active_until = MIN_DATETIME
                activated.append(f'`{cog.qualified_name}`')

            session.commit()
        activated = " | ".join(activated)
        embed = discord.Embed(title="Успешно!", description=f'На сервере были успешно деактивированы модули:\n\t'
                                                            f'{activated}', colour=self.bot.colour_embeds)
        await ctx.send(embed=embed)

    @_group_sudo.command(aliases=['set_cau'])
    @commands.is_owner()
    async def set_cog_active_until(self, ctx: Context, guild: int, cog: str, date: str = None):
        """
        date в формате "ММ/ДД/ГГ"
        """
        guild = self.bot.get_guild(guild)
        assert isinstance(guild, discord.Guild), "Неизвестный сервер"

        cog = self.bot.get_cog(cog)
        assert isinstance(cog, Cog) and cog.cls_config is not None, "Данный модуль не работает с базой данных"

        if date is not None:
            try:
                date = datetime.datetime.strptime(date, "%x").date()
            except ValueError:
                assert False, "Неверный формат даты"

        with db_session.create_session() as session:
            config = cog.get_config(session, guild)

            assert hasattr(config, "active_until"), "В этом модуле нет настройки активности"

            config.active_until = date
            session.commit()

        await ctx.send(embed=discord.Embed(
            title="Успех", description=f"Время активности {cog} сервера {guild} установленно на {date}",
            colour=self.bot.colour_embeds))

    @_group_sudo.command(aliases=['get_cau'])
    @commands.is_owner()
    async def get_cog_active_until(self, ctx: Context, guild: int, cog: str):
        guild = self.bot.get_guild(guild)
        assert isinstance(guild, discord.Guild), "Неизвестный сервер"

        cog = self.bot.get_cog(cog)
        assert isinstance(cog, Cog) and cog.cls_config is not None, "Данный модуль не работает с базой данных"

        with db_session.create_session() as session:
            config = cog.get_config(session, guild)

            assert hasattr(config, "active_until"), "В этом модуле нет настройки активности"
            embed = discord.Embed(title=f"Сервер {guild}", description="Модуль {cog} активен {msg}")
            if config.active_until:
                embed.description = embed.description.format(cog=cog, msg=f"до {config.active_until}")
            else:
                embed.description = embed.description.format(cog=cog, msg=f"неограниченно")
            await ctx.send(embed=embed)

    # TODO: Сделать бан гильдии, разбан гильдии, отправка сообщения пользователю, перезагрузка
    @_group_sudo.command('guild', aliase=['сервер'])
    @commands.is_owner()
    async def _group_guild(self, ctx: Context, guild: discord.Guild = None):
        """Показывает техническую часть сервера"""
        guild = guild or ctx.guild
        assert guild, "Не указан сервер"

        statuses = list(map(lambda m: m.status, guild.members))
        types = list(map(lambda m: m.bot, guild.members))

        embed = discord.Embed(
            title=f"Информация о сервере {guild}", colour=self.bot.colour_embeds).set_thumbnail(url=guild.icon_url)
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
        with db_session.create_session() as session:
            embed.add_field(name="Бан:", value="Есть" if Guild.get(session, guild).ban_activity else "Нет")
        embed.set_footer(text=f"ID: {guild.id}")
        await ctx.reply(embed=embed)

    @_group_sudo.command('ban_guild')
    @commands.is_owner()
    async def ban_guild(self, ctx: Context, guild: discord.Guild = None):
        """Банит активность на указанном сервере"""
        guild = guild or ctx.guild
        assert guild, "Не указан сервер"

        with db_session.create_session() as session:
            Guild.get(session, guild).ban_activity = True
            session.commit()
        await ctx.reply(f"Я успешно забанил сервер: {guild}")

    @_group_sudo.command('unban_guild')
    @commands.is_owner()
    async def unban_guild(self, ctx: Context, guild: discord.Guild = None):
        """Разбанивает активность на указанном сервере"""

        guild = guild or ctx.guild
        assert guild, "Не указан сервер"

        with db_session.create_session() as session:
            Guild.get(session, guild).ban_activity = False
            session.commit()
        await ctx.reply(f"Я успешно разбанил сервер: {guild}")

    @_group_sudo.command(name="отпр", aliases=['send'])
    @commands.is_owner()
    async def send(self, ctx: Context, user: discord.User, *text: str):
        """
        Отправляет сообщение пользователю с текстом
        """
        async with ctx.typing():
            async with user.typing():
                text = join_string(text)
                await asyncio.sleep(len(text) * 0.2)
                try:
                    await user.send(text)
                except Forbidden as E:
                    await ctx.send(str(E))
                else:
                    await ctx.send("Доставлено!")

    @_group_sudo.command(name="перезагрузка", aliases=['reboot'])
    @commands.is_owner()
    async def reboot(self, ctx: Context, delay: int = 5):
        """
        Перезагружает систему бота
        """

        await ctx.reply(embed=discord.Embed(description=f"Хорошо. Перезагрузка стартует в {delay} сек."))
        subprocess.Popen([sys.executable, 'rebooter.py', str(delay), str(os.getpid())])
        await asyncio.sleep(delay - 1)
        self.bot.is_ready()
        await self.bot.logout()

    @_group_sudo.command(name="отключение", aliases=['logout', 'exit', 'disconnect', 'close'])
    @commands.is_owner()
    async def logout(self, ctx: Context):
        """
        Выходит из системы
        """
        self.bot.active_auto_save = False
        delay = 5
        await ctx.message.delete(delay=delay)
        await ctx.send(embed=discord.Embed(
            title="Система",
            description="Выполняю отключение",
            colour=self.bot.colour_embeds,
            delete_after=delay))
        await asyncio.sleep(delay + 1)
        await self.bot.logout()

    @_group_sudo.command()
    @commands.is_owner()
    async def ctrl_c(self, ctx: Context):
        """
        Возвращает ошибку KeyboardInterrupt
        """
        await ctx.send(
            embed=discord.Embed(title="Система", description="Выполняю ctrl + C", colour=self.bot.colour_embeds))
        await asyncio.sleep(1)
        raise KeyboardInterrupt()


def setup(bot: Bot):
    bot.add_cog(DeveloperCog(bot))
