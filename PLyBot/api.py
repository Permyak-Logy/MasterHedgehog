import secrets
from datetime import datetime
from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands import BadArgument
from flask import Blueprint
from flask import request, jsonify
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey

import db_session
from PLyBot.bot import Cog, Bot, Context
from PLyBot.embed import BotEmbed
from db_session import SqlAlchemyBase
from db_session.const import DEFAULT_ACCESS
from .const import HeadersApi, STATUS_ABOUT
from .extra import Permissions

JSON_STATUS = lambda s, msg=None: (jsonify(status=s, msg=STATUS_ABOUT.get(s, "{msg}").format(msg=msg)), s)


class ApiPerm:
    READ = 1
    WRITE = 2

    def __init__(self, read=True, write=True):
        self.flag = 0
        self.flag |= read and self.READ
        self.flag |= write and self.WRITE

    def read(self) -> bool:
        return bool(self.flag & self.READ)

    def write(self) -> bool:
        return bool(self.flag & self.WRITE)

    @classmethod
    async def convert(cls, _: Context, argument):
        allow = ["просмотр", "изменение"]
        if argument not in allow:
            raise BadArgument(f"Неизвестный вид прав. Доступны: {allow}")
        return cls(read=True, write=argument == "изменение")

    @classmethod
    def from_flag(cls, flag: int) -> "ApiPerm":
        return cls(read=bool(flag & ApiPerm.READ), write=bool(flag & ApiPerm.WRITE))


class ApiKey(SqlAlchemyBase):  # TODO: Ассиметричное шифрование добавить
    __tablename__ = 'api_keys'

    key = Column(String, primary_key=True)
    permission = Column(Integer, nullable=False, default=Permissions.make())
    until_active = Column(DateTime)

    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(Integer, nullable=False, default=datetime.now)
    created_for_guild = Column(Integer, ForeignKey('guilds.id'), nullable=False)

    @staticmethod
    def get(session: db_session.Session, key: str) -> "ApiKey":
        return session.query(ApiKey).filter(ApiKey.key == key).first()

    def gen(self, ctx, permission_flags=0, until_active: datetime = None):
        self.key = secrets.token_hex(8)
        self.permission = Permissions.make()
        self.until_active = datetime.now()

        self.created_by = ctx.author.id
        self.created_for_guild = ctx.guild.id

        self.until_active = until_active
        self.permission = permission_flags

    def __repr__(self):
        return f"ApiKey"

    def __str__(self):
        return repr(self)


class ApiCog(Cog, name="Api"):
    def __init__(self, bot):
        super().__init__(bot, emoji_icon='📡')
        self.bot.add_blueprint(HintsBP(self.bot).blueprint, url_prefix='/api/hints')
        self.bot.add_blueprint(CogsBP(self.bot).blueprint, url_prefix='/api/cogs')
        self.bot.add_models(ApiKey)

    @commands.command('api-key')
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def _cmd_api_key(self, ctx: Context, permission: ApiPerm = ApiPerm(write=True)):
        with db_session.create_session() as session:
            api_key = ApiKey()
            api_key.gen(ctx, permission_flags=permission.flag)
            session.add(api_key)
            session.commit()

            embed = BotEmbed(ctx=ctx)
            embed.add_field(name="Код", value=api_key.key, inline=False)
            await ctx.reply(embed=embed)


class BaseApiBP:
    blueprint: Blueprint

    def __init__(self, cog: Cog):
        self.cog = cog
        self.blueprint.before_request(self.before_check_request)
        self.blueprint.route('/')(self.index)
        if cog.cls_config and hasattr(cog.cls_config, 'access'):
            self.blueprint.route('/access', methods=['GET', 'POST'])(self.access)

    def get_routes(self):
        return _GetRuleFromSetupState()(self.blueprint)

    def index(self):
        return jsonify(cog=self.cog.qualified_name,
                       sections=list(self.get_routes().keys() - {'/'})), 200

    def access(self):
        with db_session.create_session() as session:
            if request.method == 'GET':
                try:
                    guild_id = int(request.headers[HeadersApi.GUILD_ID])

                except ValueError:
                    return JSON_STATUS(400)
                else:
                    access = self.cog.get_config(session, guild_id).get_access()
                    access['__default__'] = DEFAULT_ACCESS.copy()
                    return jsonify(guild_id=int(request.headers[HeadersApi.GUILD_ID]),
                                   cog=self.cog.qualified_name,
                                   access=access)
            elif request.method == 'POST':
                return jsonify(status='ok')

    def before_check_request(self):
        guild_id = request.headers.get(HeadersApi.GUILD_ID)
        api_key = request.headers.get(HeadersApi.API_KEY)
        if not guild_id or not api_key or not guild_id.isnumeric():
            return JSON_STATUS(400)

        with db_session.create_session() as session:
            if self.cog.cls_config and not self.cog.get_config(session, guild_id):
                return JSON_STATUS(425)
            api_key_data = ApiKey.get(session, api_key)
            if not api_key_data:
                return JSON_STATUS(403)
            perm = ApiPerm.from_flag(flag=api_key_data.permission)
            if request.method == "GET" and not perm.read():
                return JSON_STATUS(403)
            if request.method == "POST" and not perm.write():
                return JSON_STATUS(403)


class JsonParam:
    def __init__(self, dtype, islist=False, about=None):
        self.type = dtype
        self.islist = islist
        self.about = about

    def make(self, value):
        return jsonify(value=value, type=self.type, about=self.about, islist=self.islist)

    def get(self, json_data: dict):
        pass


class HintsBP:
    blueprint = Blueprint('hints_api', __name__)

    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.load()

    def load(self):
        @self.blueprint.route('/guild', methods=['GET'])
        def hint_guild():
            nonlocal self
            if set(request.json.keys()) ^ {"guild_id"}:
                return JSON_STATUS(400)

            guild: discord.Guild = self.bot.get_guild(request.json['guild_id'])
            if not guild:
                return JSON_STATUS(404)

            return jsonify(status=202, msg=STATUS_ABOUT[202], guild={
                "guild_id": guild.id,
                "name": guild.name,
                "icon_url": str(guild.icon_url)

            })

        @self.blueprint.route('/member', methods=['GET'])
        def hint_member():
            nonlocal self
            if set(request.json.keys()) ^ {"user_id", "guild_id"}:
                return JSON_STATUS(400)

            guild: discord.Guild = self.bot.get_guild(request.json['guild_id'])
            if not guild:
                return JSON_STATUS(404)

            member: discord.Member = guild.get_member(request.json['user_id'])
            if not member:
                return JSON_STATUS(404)

            return jsonify(status=202, msg=STATUS_ABOUT[202], member={
                "guild_id": guild.id,
                "user_id": member.id,
                "display_name": str(member.display_name)
            })

        @self.blueprint.route('/user', methods=['GET'])
        def hint_user():
            nonlocal self
            if set(request.json.keys()) ^ {"user_id"}:
                return JSON_STATUS(400)

            user: discord.User = self.bot.get_user(request.json['user_id'])
            if not user:
                return JSON_STATUS(404)

            return jsonify(status=202, msg=STATUS_ABOUT[202], user={
                "user_id": user.id,
                "display_name": str(user.display_name),
                "avatar_url": str(user.avatar_url)
            })

        @self.blueprint.route('/channel', methods=['GET'])
        def hint_channel():
            nonlocal self
            if set(request.json.keys()) ^ {"channel_id"}:
                return JSON_STATUS(400)
            return JSON_STATUS(204)


class CogsBP:
    blueprint = Blueprint('cogs_api', __name__)

    def __init__(self, bot: Bot):
        self.bot = bot
        self.load()

    def load(self):
        @self.blueprint.route('/')
        def api_cogs():
            response = {"cogs": {}}
            for url_rule, bp in self.bot.get_cog_blueprints().items():
                if hasattr(bp, "cog"):
                    response["cogs"][bp.cog.qualified_name] = url_rule
            return response


class _GetRuleFromSetupState:
    """Этот класс служит чисто для выкачки из blueprint.deferred_functions routes и функции созданные
    методом blueprint.route"""

    def __init__(self, blueprint: Blueprint = None):
        self.__blueprint = blueprint

    def __call__(self, blueprint: Blueprint = None):
        if not self.__blueprint and not blueprint:
            return {}

        result = {}
        for func in (self.__blueprint or blueprint).deferred_functions:
            try:
                # noinspection PyTypeChecker
                rule, endpoint, f, options = func(self)
                result[rule] = (endpoint, f, options)
            except AttributeError:
                pass
        return result

    @staticmethod
    def add_url_rule(rule, endpoint, f, **options):
        return rule, endpoint, f, options


def setup(bot: Bot):
    bot.add_cog(ApiCog(bot))
