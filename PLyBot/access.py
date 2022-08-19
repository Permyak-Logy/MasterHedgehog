import json

import discord
from discord.ext import commands
from flask import Blueprint
from flask import jsonify

import db_session
from PLyBot.bot import Cog, Bot
from .api import BaseApiBP
from db_session.const import DEFAULT_ACCESS
from .const import STATUS_ABOUT

ATTRS_BOOL = {"admin", "everyone", "active"}
ATTRS_INT = {"min_client_time", "min_member_time", "min_role"}
ATTRS_LIST = {"roles", "users", "channels", "exc_roles", "exc_users", "exc_channels"}

JSON_STATUS = lambda s, msg=None: jsonify(status=s, msg=STATUS_ABOUT.get(s, "{msg}").format(msg=msg))


class AccessCog(Cog, name="Access Master Ёжа"):
    def __init__(self, bot):
        super().__init__(bot, emoji_icon='🛡️')
        self.bot.add_cog_blueprint(KeysApiBP(self), url_prefix='/access')

    async def cog_check(self, ctx: commands.Context):
        # TODO: Исправить
        # if ctx.author.guild_permissions.administrator:
        #     return True
        return await self.bot.is_owner(ctx.author)

    @staticmethod
    async def format_access(ctx: commands.Context, embed: discord.Embed, access: dict):
        for key, (val, lvl) in access.items():
            if 'channels' in key:
                val = "\n".join(
                    ctx.bot.get_channel(id_).mention for id_ in val if ctx.bot.get_channel(id_) is not None) or []
            if 'users' in key:
                val = "\n".join(ctx.bot.get_user(id_).mention for id_ in val if ctx.bot.get_user(id_) is not None) or []
            if 'roles' in key:
                val = "\n".join(
                    ctx.guild.get_role(id_).mention for id_ in val if ctx.guild.get_role(id_) is not None) or []
            if isinstance(val, bool):
                val = "Да" if val else "Нет"
            if not val:
                val = "Не указано"
            embed.add_field(name=key, value=str(val) + "*" * lvl)

    # TODO: Переделать поиск cog или command
    @commands.command(name='доступ', aliases=['acc', 'access'], enabled=False)
    @commands.guild_only()
    async def get_access_cmd(self, ctx: commands.Context, name: str):
        """
        Получает права доступа у команды или модуля (если name=="DEF", то покажет настройки по умолчанию)
        """
        command = self.bot.get_command(name)
        if command is None:
            cog = self.bot.get_cog(name)
        else:
            cog = command.cog
        assert not (command is None and cog is None), "Неизвестный модуль или команда"

        if not isinstance(cog, Cog):
            assert command is None, "Команда не поддерживает настройку прав"
            assert isinstance(cog, Cog) and cog.cls_config is not None, "Модуль не поддерживает настройку прав"

        session = db_session.create_session()
        access = cog.get_config(session, ctx.guild).get_access()[str(command)]
        session.close()

        await ctx.send("```json\n" + json.dumps(access, indent=4) + "\n```")

    # TODO: Подделать описания команд
    @commands.command(name='устдоступ', aliases=['set_acc', 'setacc', 'set_access', '=acc'], enabled=False)
    @commands.guild_only()
    async def set_access_cmd(self, ctx: commands.Context, name: str, attr: str = None, *args: int):
        """
        Устанавливает допуск по одному из параметров
        Если command == "ALL" то вышлет настройки для модуля, иначе для команды
        Если attr == "DEF" то выставит значение по умолчанию, иначе будет изменять атрибут
        args параметры для атрибута (0 == false, 1 == true если bool тип), если не указан то по умолчанию
        (Указывается целочисленным параметром)
        """
        command = self.bot.get_command(name)
        if command is None:
            cog = self.bot.get_cog(name)
        else:
            cog = command.cog
        assert not (command is None and cog is None), "Неизвестный модуль или команда"

        check = isinstance(cog, Cog) and cog.cls_config is not None
        assert check or command is None, "Команда не поддерживает настройку прав"
        assert check, "Модуль не поддерживает настройку прав"

        assert attr in ATTRS_BOOL | ATTRS_INT | ATTRS_LIST or attr is None, f"Недействительный параметр '{attr}'"

        session = db_session.create_session()
        config = cog.get_config(session, ctx.guild)
        access = config.get_access()
        change_access = access["__cog__" if command is None else str(command)]
        if attr is None:
            change_access.clear()
        elif args:
            if attr in ATTRS_BOOL:
                change_access[attr] = bool(args[0])
            elif attr in ATTRS_INT:
                change_access[attr] = int(args[0])
            elif attr in ATTRS_LIST:
                change_access[attr] = list(map(int, args))
        else:
            del change_access[attr]
        config.set_access(access)
        session.commit()
        session.close()

        await ctx.send(embed=discord.Embed(title="Успешно!", description="настройки конфига обновлены"))

    @commands.command(name='+доступ', aliases=['+access', '+acc'])
    @commands.guild_only()
    async def access_cmd(self, ctx: commands.Context, command_name: str):
        """
        Возвращает предварительные права доступа
        """
        command = self.bot.get_command(command_name)
        assert command is not None, f"Несуществующая команда '{command_name}'"

        cog = command.cog

        assert isinstance(cog, Cog), "Этот модуль не поддерживает установку прав"
        assert cog.cls_config is not None, "Этот модуль не поддерживает установку прав"

        session = db_session.create_session()
        access = cog.get_config(session, ctx.guild).get_access()
        session.close()

        access_cmd = access[str(command)]
        access_cog = access["__cog__"]

        def access_get(__key):
            val = access_cmd.get(__key) or access_cog.get(__key) or DEFAULT_ACCESS[__key]
            if __key in access_cmd:
                lvl = 0
            elif __key in access_cog:
                lvl = 1
            else:
                lvl = 2
            return val, lvl

        pre_access = {}
        for key in DEFAULT_ACCESS.keys():
            pre_access[key] = access_get(key)
        pre_access["command"] = (command_name, 0)
        embed = discord.Embed(
            title=f"Права доступа к \"{command_name}\""
        )
        await self.format_access(ctx, embed, pre_access)
        await ctx.send(embed=embed)

    @commands.command(name='комп', aliases=['моды', 'mods', 'модули', 'компоненты'])
    @commands.guild_only()
    async def get_modules(self, ctx: commands.Context):
        """
        Возвращает список модулей с некоторой технической информацией, по отношению к вам на этом сервере
        """
        session = db_session.create_session()
        text = []
        for name in sorted(self.bot.cogs.keys()):
            cog: Cog = self.bot.get_cog(name)

            elem = []
            if cog.cls_config is not None and hasattr(cog.cls_config, "active_until"):
                date = cog.get_config(session, ctx.guild).active_until
            else:
                date = None
            elem.append(f'активен{"=неограниченно" if date is None else f"_до={date}"}')

            if await self.bot.is_owner(ctx.author):
                config = cog.cls_config.__tablename__ if cog.cls_config else "Нет"
                elem.append(f'конфиг={config}')

            text.append(f'{name.ljust(len(max(self.bot.cogs.keys(), key=len)), " ")} [{"; ".join(elem)}]')

        if text:
            await ctx.send("```python\n" + "\n".join(text) + "\n```")
        else:
            await ctx.send("```python\nУ вас нет доступных модулей\n```")


class KeysApiBP(BaseApiBP):
    blueprint = Blueprint('keys_api', __name__)


def setup(bot: Bot):
    bot.add_cog(AccessCog(bot))
