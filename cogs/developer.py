import argparse
import asyncio
import datetime

import discord
from discord.errors import Forbidden
from discord.ext import commands

import db_session
from PLyBot import Bot, Cog, ApiKey, join_string, Context
from db_session.const import MIN_DATETIME

activate_parser = argparse.ArgumentParser()
activate_parser.add_argument('-A', action="store_true")


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
    @commands.guild_only()
    async def activate(self, ctx: Context, *, cog: str = "ALL"):
        """
        Активирует на бессрочное использование указанный модуль
        """
        guild: discord.Guild = ctx.guild
        cogs = list(filter(bool, map(self.bot.get_cog, self.bot.cogs))) if cog == "ALL" else [self.bot.get_cog(cog)]
        assert cogs, "Не найден модуль"
        activated = []
        with db_session.create_session() as session:
            for cog in cogs:
                if not (isinstance(cog, Cog) and cog.cls_config is not None):
                    continue
                config = cog.get_config(session, ctx.guild)
                if not hasattr(config, "active_until"):
                    continue
                config.active_until = None
                activated.append(cog.qualified_name)
            session.commit()
        activated = "\n\t".join(activated)
        embed = discord.Embed(title="Успешно!", description=f'На сервере были успешно активированы модули:\n\t'
                                                            f'{activated}', colour=self.bot.colour_embeds)
        await ctx.send(embed=embed)

    @_group_sudo.command(aliases=['deact'])
    @commands.is_owner()
    @commands.guild_only()
    async def deactivate(self, ctx: Context, *, cog: str = "ALL"):
        """
        Деактивирует на бессрочное использование указанный модуль
        """
        guild: discord.Guild = ctx.guild
        cogs = list(filter(bool, map(self.bot.get_cog, self.bot.cogs))) if cog == "ALL" else [self.bot.get_cog(cog)]
        assert cogs, "Не найден модуль"
        activated = []
        with db_session.create_session() as session:
            for cog in cogs:
                if not (isinstance(cog, Cog) and cog.cls_config is not None):
                    continue
                config = cog.get_config(session, guild)
                if not hasattr(config, "active_until"):
                    continue
                config.active_until = MIN_DATETIME
                activated.append(cog.qualified_name)

            session.commit()
        activated = "\n\t".join(activated)
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
    @_group_sudo.command()
    @commands.is_owner()
    async def ban_guild(self, ctx: Context, guild: discord.Guild = None):
        pass

    @_group_sudo.command()
    @commands.is_owner()
    async def unban_guild(self, ctx: Context, guild: discord.Guild = None):
        pass

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
    async def reboot(self, ctx: Context):
        """
        Перезагружает систему бота
        """

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
