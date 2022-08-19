import argparse
import asyncio
import datetime
import os
import subprocess
import sys

import discord
from discord.errors import Forbidden
from discord.ext import commands
from discord_components import Select, SelectOption, Interaction

import db_session
from PLyBot import Bot, Cog, join_string, Context, BotEmbed
from db_session.base import Guild
from db_session.const import MIN_DATETIME
from db_session import BaseConfigMix
from flask import Blueprint
activate_parser = argparse.ArgumentParser()
activate_parser.add_argument('-A', action="store_true")


# TODO: Вывод логов
# TODO: Русифицировать команды
class DeveloperCog(Cog, name="Для разработчиков"):
    def __init__(self, bot: Bot):
        super().__init__(bot, emoji_icon="🛠️")

    @commands.group(name='sudo')
    @commands.is_owner()
    async def _group_sudo(self, ctx: Context, command: str = None, *args: str):
        """Вызов root команд"""
        # TODO: Сделать разовое выполнение от root
        await ctx.just_send_help()

    @_group_sudo.command('cogs')
    async def _cmd_sudo_cogs(self, ctx: Context, *, guild: discord.Guild = None):
        """Вызывает контроллер для включения и выключения модулей"""
        guild: discord.Guild = guild or ctx.guild
        assert guild, "Не указан сервер"
        cogs_with_active_until = []
        for cog in filter(bool, map(self.bot.get_cog, self.bot.cogs)):
            if not (isinstance(cog, Cog) and cog.cls_config is not None):
                continue
            if hasattr(cog.cls_config, "active_until"):
                cogs_with_active_until.append(cog)

        embed = BotEmbed(ctx=ctx, title="Контролер модулей")
        options = []

        with db_session.create_session() as session:
            for cog in cogs_with_active_until:
                config = cog.get_config(session, guild)
                date: datetime.date = config.active_until
                active_until = ("🟢" if config.check_active_until() else "🔴") + " " + (
                    f"Активен до {date}" if date else "Активен на век")

                options.append(SelectOption(
                    label=cog.qualified_name,
                    value=cog.id,
                    emoji=cog.emoji_icon,
                    description=active_until,
                    default=config.check_active_until()
                ))
                embed.add_field(name=cog.emoji_icon + " " + cog.qualified_name, value=active_until)

        custom_id = f"_cmd_sudo_cogs:{ctx.message.id}"

        msg: discord.Message = await ctx.reply(
            embed=embed, components=[Select(
                placeholder="Выбери каналы!",
                options=options,
                min_values=0,
                max_values=len(cogs_with_active_until),
                custom_id=custom_id)
            ])
        try:
            interaction: Interaction = await self.bot.wait_for(
                "select_option", check=lambda inter: inter.custom_id == custom_id and inter.user == ctx.author,
                timeout=5 * 60
            )
        except asyncio.TimeoutError:
            pass
        else:
            toggles_cogs = list(map(int, interaction.values))
            cogs_activated = []
            cogs_deactivated = []
            with db_session.create_session() as session:
                for cog in cogs_with_active_until:
                    config: BaseConfigMix = cog.get_config(session, guild)
                    if (cog.id in toggles_cogs) is (config.check_active_until()):
                        continue

                    if cog.id not in toggles_cogs:
                        config.active_until = MIN_DATETIME
                        cogs_deactivated.append(cog)
                    else:
                        config.active_until = None
                        cogs_activated.append(cog)

                session.commit()
            embed = BotEmbed(ctx=ctx, title="Успешно!")
            if cogs_activated:
                embed.add_field(name="Активированы", value="\n".join(map(
                    lambda x: x.emoji_icon + " " + x.qualified_name, cogs_activated)))
            if cogs_deactivated:
                embed.add_field(name="Деактивированы", value="\n".join(map(
                    lambda x: x.emoji_icon + " " + x.qualified_name, cogs_deactivated)))

            await interaction.send(embed=embed, ephemeral=True, delete_after=60)
        finally:
            await msg.delete()

    @_group_sudo.command(name='activate', aliases=['act'])
    @commands.is_owner()
    async def _cmd_sudo_activate(self, ctx: Context, *, guild: discord.Guild = None):
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
        embed = BotEmbed(ctx=ctx, title="Успешно!", description=f'На сервере были успешно активированы модули:\n\n'
                                                                f'{activated}', colour=self.bot.colour)
        await ctx.send(embed=embed)

    @_group_sudo.command(name="deactivate", aliases=['deact'])
    @commands.is_owner()
    async def _cmd_sudo_deactivate(self, ctx: Context, *, guild: discord.Guild = None):
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
        embed = BotEmbed(ctx=ctx, title="Успешно!", description=f'На сервере были успешно деактивированы модули:\n\t'
                                                                f'{activated}', colour=self.bot.colour)
        await ctx.send(embed=embed)

    @_group_sudo.command(name="set_cog_active_until", aliases=['set_cau'])
    @commands.is_owner()
    async def _cmd_sudo_set_cog_active_until(self, ctx: Context, guild: int, cog: str, date: str = None):
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

        await ctx.send(embed=BotEmbed(ctx=ctx,
                                      title="Успех",
                                      description=f"Время активности {cog} сервера {guild} установленно на {date}",
                                      colour=self.bot.colour))

    @_group_sudo.command(name="get_cog_active_until", aliases=['get_cau'])
    @commands.is_owner()
    async def _cmd_sudo_get_cog_active_until(self, ctx: Context, guild: int, cog: str):
        guild = self.bot.get_guild(guild)
        assert isinstance(guild, discord.Guild), "Неизвестный сервер"

        cog = self.bot.get_cog(cog)
        assert isinstance(cog, Cog) and cog.cls_config is not None, "Данный модуль не работает с базой данных"

        with db_session.create_session() as session:
            config = cog.get_config(session, guild)

            assert hasattr(config, "active_until"), "В этом модуле нет настройки активности"
            embed = BotEmbed(ctx=ctx, title=f"Сервер {guild}", description="Модуль {cog} активен {msg}")
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
        with db_session.create_session() as session:
            embed.add_field(name="Бан:", value="Есть" if Guild.get(session, guild).ban_activity else "Нет")
        embed.set_footer(text=f"ID: {guild.id}")
        await ctx.reply(embed=embed)

    @_group_sudo.command('ban_guild')
    @commands.is_owner()
    async def _cmd_sudo_ban_guild(self, ctx: Context, guild: discord.Guild = None):
        """Банит активность на указанном сервере"""
        guild = guild or ctx.guild
        assert guild, "Не указан сервер"

        with db_session.create_session() as session:
            Guild.get(session, guild).ban_activity = True
            session.commit()
        await ctx.reply(f"Я успешно забанил сервер: {guild}")

    @_group_sudo.command('unban_guild')
    @commands.is_owner()
    async def _cmd_sudo_unban_guild(self, ctx: Context, guild: discord.Guild = None):
        """Разбанивает активность на указанном сервере"""

        guild = guild or ctx.guild
        assert guild, "Не указан сервер"

        with db_session.create_session() as session:
            Guild.get(session, guild).ban_activity = False
            session.commit()
        await ctx.reply(f"Я успешно разбанил сервер: {guild}")

    @_group_sudo.command(name="отпр", aliases=['send'])
    @commands.is_owner()
    async def _cmd_sudo_send(self, ctx: Context, user: discord.User, *text: str):
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
    async def _cmd_sudo_reboot(self, ctx: Context, delay: int = 5):
        """
        Перезагружает систему бота
        """

        await ctx.reply(embed=BotEmbed(ctx=ctx, description=f"Хорошо. Перезагрузка стартует в {delay} сек."))
        subprocess.Popen([sys.executable, 'rebooter.py', str(delay), str(os.getpid())])
        await asyncio.sleep(delay - 1)
        self.bot.is_ready()
        await self.bot.logout()

    @_group_sudo.command(name="отключение", aliases=['logout', 'exit', 'disconnect', 'close'])
    @commands.is_owner()
    async def _cmd_sudo_logout(self, ctx: Context):
        """
        Выходит из системы
        """
        self.bot.active_auto_save = False
        delay = 5
        await ctx.message.delete(delay=delay)
        await ctx.send(embed=BotEmbed(ctx=ctx,
                                      title="Система",
                                      description="Выполняю отключение",
                                      colour=self.bot.colour,
                                      delete_after=delay))
        await asyncio.sleep(delay + 1)
        await self.bot.logout()

    @_group_sudo.command(name='ctrl_c')
    @commands.is_owner()
    async def _cmd_sudo_ctrl_c(self, ctx: Context):
        """
        Возвращает ошибку KeyboardInterrupt
        """
        await ctx.send(
            embed=BotEmbed(ctx=ctx, title="Система", description="Выполняю ctrl + C", colour=self.bot.colour))
        await asyncio.sleep(1)
        raise KeyboardInterrupt()

    @_group_sudo.command('su', aliases=['sudo'])
    @commands.is_owner()
    async def _cmd_sudo_su(self, ctx: Context):
        """
        Отключает или включает все проверки доступа для пользователей группы Owner
        """
        assert ctx.author.id == self.bot.root_id, "Только root может включить режим root"
        self.bot.root_active = not self.bot.root_active
        await ctx.reply(
            embed=BotEmbed(ctx=ctx, title="Система", description="Игнорирование ограничений доступа: " + (
                "Включено\n||Будьте осторожны с использованием!||" if self.bot.root_active else "Выключено"))
        )

    @_group_sudo.command('admins')
    @commands.is_owner()
    async def _cmd_sudo_admins(self, ctx: Context, guild: discord.Guild = None):
        """Ищет все роли с правами админа"""
        guild = guild or ctx.guild
        assert guild, "Не указан сервер для поиска"
        admins = []
        for role in guild.roles[::-1]:
            if role.permissions.administrator:
                admins.append(role)

        embed = BotEmbed(ctx=ctx,
                         description="\n".join(map(lambda x: f"`{x.id}` {x.name}", admins)))
        await ctx.send(embed=embed)

    @_group_sudo.command('guilds')
    @commands.is_owner()
    async def _cmd_sudo_guilds(self, ctx: Context):
        """Показывает все сервера на которых сейчас бот"""

        embed = BotEmbed(ctx=ctx,
                         description="\n".join(map(lambda x: f"`{x.id}` {x.name}", ctx.bot.guilds)))
        await ctx.send(embed=embed)

    @_group_sudo.command('invites')
    @commands.is_owner()
    async def __cmd_sudo_invites(self, ctx: Context, guild: discord.Guild):
        """Высылает все действующие ссылки приглашения в гильдию"""
        embed = BotEmbed(
            ctx=ctx, title=f"Ссылки на {guild.name}",
            description=("||Вы уже состоите на этом сервере||\n\n" if guild.get_member(
                ctx.author.id) else "") + "\n".join(
                map(lambda x: f"**{x[0]}.** https://discord.gg/{x[1].code} `{x[1].inviter}`\n"
                              f"MA=`{x[1].max_age}` MU=`{x[1].max_uses}` CA=`{x[1].created_at}`\n",
                    enumerate(await ctx.bot.get_guild(guild.id).invites(), start=1))))
        embed.set_thumbnail(url=guild.icon_url)
        await ctx.send(embed=embed)

    @_group_sudo.command('routes_api')
    @commands.is_owner()
    async def __cmd_sudo_routes_api(self, ctx: Context):
        embed = BotEmbed(ctx=ctx)
        for prefix, blueprint in self.bot.get_blueprints().items():
            blueprint: Blueprint
            embed.add_field(name=blueprint.name, value=f"http://127.0.0.1{prefix}", inline=False)
        await ctx.reply(embed=embed)


def setup(bot: Bot):
    bot.add_cog(DeveloperCog(bot))
