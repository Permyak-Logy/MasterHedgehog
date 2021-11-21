import datetime
import json
import logging
import typing

import discord
import sqlalchemy
from discord.ext import commands

from . import SqlAlchemyBase
from .const import DEFAULT_ACCESS

logging = logging.getLogger(__name__)

NULL = NONE = None
TRUE = True
FALSE = False


class BaseConfigMix:
    guild_id: sqlalchemy.Column
    access: sqlalchemy.Column
    active_until: sqlalchemy.Column

    def get_access(self) -> dict:
        if hasattr(self, 'access'):
            if self.access == NONE:
                return {}
            return json.loads(self.access)
        raise AttributeError("У меня нет возможности представлять доступы")

    def set_access(self, access: dict):
        if hasattr(self, 'access'):
            # noinspection PyTypeChecker
            self.access = json.dumps(access, ensure_ascii=False)
        else:
            raise AttributeError("У меня нет возможности представлять доступы")

    async def check_access(self, ctx: commands.Context) -> bool:
        try:
            access = self.get_access()

        except AttributeError:
            return True
        try:
            # TODO: Сделать для каждой команды свои настройки допуска
            access_cmd = access[str(str(ctx.command).split()[0])]
        except KeyError as E:
            logging.warning(f"Не удалось получить данные о доступах к команде ({E.__class__.__name__}: {E})")
            return True
        access_cog = access['__cog__']

        def access_get(key):
            return access_cmd.get(key, access_cog.get(key, DEFAULT_ACCESS[key]))

        if await ctx.bot.is_owner(ctx.author):
            return True

        if access_get("everyone"):
            return True

        if ctx.author.id in access_get("exc_users"):
            return False
        if ctx.author.id in access_get("users"):
            return True

        if ctx.author.guild_permissions.administrator and access_get("admin"):
            return True

        if any(map(lambda r: r.id in access_get("exc_roles"), ctx.author.roles)):
            return False
        if any(map(lambda r: r.id in access_get("roles"), ctx.author.roles)):
            return True

        if access_get("min_client_time") > (ctx.author.created_at - datetime.datetime.now()).seconds:
            return False
        if access_get("min_member_time") > (ctx.author.created_at - datetime.datetime.now()).seconds:
            return False

        if access_get("exc_channels") and ctx.channel.id in access_get("exc_channels"):
            return False
        if access_get("channels") and ctx.channel.id in access_get("channels"):
            return True

        return access_get('active')

    def get_guild(self, obj: typing.Union[commands.Bot, commands.Context]) -> typing.Union[discord.Guild, None]:
        if hasattr(self, 'guild_id'):
            if isinstance(obj, commands.Context):
                bot = obj.bot
            elif isinstance(obj, commands.Bot):
                bot = obj
            else:
                raise TypeError(f"Неверный тип аргумента obj (got type '{type(obj)}')")
            # noinspection PyTypeChecker
            return bot.get_guild(self.guild_id)

    def check_active_until(self) -> bool:
        if hasattr(self, 'active_until'):
            if isinstance(self.active_until, datetime.date):
                now = datetime.datetime.now().date()
                return self.active_until + datetime.timedelta(days=1) > now
        return True


del SqlAlchemyBase, sqlalchemy
