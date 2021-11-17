import asyncio
import logging
from datetime import datetime, timedelta
from threading import Thread
from typing import Union, Optional, Type

import discord
from discord import VoiceClient
from discord.ext import commands
from discord.utils import get
from flask import Flask, Blueprint

import db_session
from db_session import Session, BaseConfigMix
from db_session.base import User, Member, Guild, Message
from .enums import TypeBot
from .extra import HRF, full_using_db, run_if_ready_db
from .help import HelpCommand

# TODO: Загрузка внешней базы данных
# TODO: Роли участников в отдельной таблице

logging = logging.getLogger(__name__)


class Bot(commands.Bot):
    def __init__(self, *, db_con: Optional[str] = None, bot_type: TypeBot = TypeBot.other, app_name=__name__,
                 turn_on_api_server=False, **options):
        super().__init__(intents=options.pop("intents", discord.Intents.all()),
                         help_command=options.pop('help_command', HelpCommand()),
                         **options)
        self.__db_connect = db_con
        self.__models = {}

        self.__blueprints = {}  # "/url_prefix": <class: blueprint>
        self.__cog_blueprints = {}

        if bot_type == TypeBot.self:
            self._skip_check = lambda x, y: x != y
        elif bot_type == TypeBot.other:
            self._skip_check = lambda x, y: x == y
        elif bot_type == TypeBot.both:
            self._skip_check = lambda x, y: False
        else:
            self._skip_check = lambda x, y: True
        self.name = options.pop("bot_name", self.__class__.__name__)
        self.version = options.pop("version", "unknown")

        self.colour_embeds = options.pop("colour_embeds", discord.colour.Color.from_rgb(127, 127, 127))
        self.activity: discord.Activity = options.pop("activity", None)
        self.started = options.pop("started", datetime.now())

        self.__invite_link = options.pop("invite_link", None)
        self.permissions = options.pop("permissions", 0)

        self.count_invokes = 0
        self.after_invoke(self.on_after_invoke)

        self.__ready_db = False
        if turn_on_api_server:
            self.flask_app = Flask(app_name)
            self.flask_app.route('/')(self.index_api)

        else:
            self.flask_app = None

        logging.info(f'init bot {self.name} {self.version}')

    @property
    def using_db(self) -> bool:
        return bool(self.__db_connect)

    @property
    async def invite_link(self):
        """Возвращает ссылку приглашение для бота. Работает только если авторизован бот, а не обычный пользователь."""

        assert self.user.bot, "Это не доступно для обычного пользователя"
        if self.__invite_link:
            return self.__invite_link
        info = await self.application_info()
        return f'https://discord.com/api/oauth2/authorize?client_id={info.id}&permissions={self.permissions}&scope=bot'

    @property
    def ready_db(self):
        return self.__ready_db

    # Слушатели событий #####################################################
    async def on_ready(self):
        if self.using_db:
            with db_session.create_session() as session:
                self.update_all_data(session)
                session.commit()
            self.__ready_db = True

        if self.activity:
            await self.change_presence(activity=self.activity)

        logging.info(f"Бот класса {self.__class__.__name__} готов к работе как \"{self.user}\"")

    async def on_resumed(self):
        logging.info(f"[resumed] Бот {self.user} возобновил сеанс")

    async def on_connect(self):
        logging.info(f"[connect] Бот {self.user} подключился к discord")

    async def on_disconnect(self):
        logging.info(f"[disconnect] Бот {self.user} отключился от discord")

    async def on_message(self, message: discord.Message):
        if self.using_db:
            with db_session.create_session() as session:
                session: Session
                Message.update(session, message)
                User.update(session, message.author)

                if isinstance(message.author, discord.Member):
                    Member.update(session, message.author)
                    Member.get(session, message.author).last_activity = message.created_at

                session.commit()

        await self.process_commands(message)

    @run_if_ready_db(is_async=True)
    @full_using_db(is_async=True)
    async def on_guild_join(self, guild: discord.Guild):
        logging.info(f"{self.user} joined on {guild}")
        with db_session.create_session() as session:
            Guild.update(session, guild)
            session.commit()

    @run_if_ready_db(is_async=True)
    @full_using_db(is_async=True)
    async def on_guild_update(self, _, guild: discord.Guild):
        logging.debug(f"{guild} updated")
        with db_session.create_session() as session:
            session: Session
            Guild.update(session, guild)
            session.commit()

    @run_if_ready_db(is_async=True)
    @full_using_db(is_async=True)
    async def on_user_update(self, _, user: discord.User):
        logging.debug(f"{user} updated")
        with db_session.create_session() as session:
            session: Session
            User.update(session, user)
            session.commit()

    @run_if_ready_db(is_async=True)
    @full_using_db(is_async=True)
    async def on_member_update(self, _, member: discord.Member):
        logging.debug(f"{member} updated")
        with db_session.create_session() as session:
            session: Session
            Member.update(session, member)
            # TODO: database is locked сделать async commit
            session.commit()

    @run_if_ready_db(is_async=True)
    @full_using_db(is_async=True)
    async def on_member_join(self, member: discord.Member):
        await self.wait_until_ready()
        # TODO: Выдача ролей при перезаходе. Убрать костыль
        with db_session.create_session() as session:
            session: Session
            User.update(session, member)

            try:
                cog: Cog = self.get_cog('Роли')
                config = cog.get_config(session, member.guild)
                if config.check_active_until():

                    data = Member.get(session, member)

                    # noinspection PyUnresolvedReferences
                    if config.return_old_roles:
                        roles = list(filter(lambda r: r.name != '@everyone', data.get_roles(self)))
                        for role in roles:
                            try:
                                await member.add_roles(role)
                            except discord.Forbidden:
                                pass
            except AttributeError:
                pass

            Member.update(session, self.get_guild(member.guild.id).get_member(member.id))
            session.commit()

    @run_if_ready_db(is_async=True)
    @full_using_db(is_async=True)
    async def on_member_remove(self, member: discord.Member):
        await self.wait_until_ready()
        # TODO: Избавится от костыля

        with db_session.create_session() as session:
            session: Session

            class BreakError(Exception):
                pass

            try:
                cog: Cog = self.get_cog('Роли')
                config = cog.get_config(session, member.guild)
                if not config.check_active_until():
                    raise BreakError()

                data = Member.get(session, member)
                # noinspection PyUnresolvedReferences
                if not config.return_old_roles:
                    raise BreakError()

                if not hasattr(data, 'joined'):
                    raise AttributeError()
                data.joined = False

            except (AttributeError, BreakError):
                Member.delete(session, member)

            session.commit()

    async def on_command_error(self, ctx: commands.Context, exception: commands.CommandError):
        await self.wait_until_ready()

        logging.warning(f"[ERROR_COMMAND] [{ctx}] {exception}")
        embed = discord.Embed(
            title="Ошибка исполнения!",
            description="Что-то пошло не так",
            colour=self.colour_embeds
        )

        if isinstance(exception, commands.MissingRequiredArgument):
            embed.add_field(name="Сообщение",
                            value="Не указан обязательный аргумент {}".format(exception.param))
        elif isinstance(exception, commands.CommandInvokeError):
            original = exception.original
            if isinstance(original, discord.Forbidden):
                embed.add_field(name="Сообщение", value="Мне это недоступно или не разрешено делать :(")
            elif isinstance(original, AssertionError):
                embed.add_field(name="Сообщение", value=str(original))
            else:
                embed.add_field(name="Сообщение", value="Внутренняя ошибка в команде")
                embed.add_field(name="Output", value="`{}: {}`".format(type(original).__name__, original))
                await super().on_command_error(ctx, exception)
        elif isinstance(exception, commands.BadArgument):
            if isinstance(exception, commands.MemberNotFound):
                embed.add_field(name="Сообщение", value=f"Участник {exception.argument} не найден")
            elif isinstance(exception, commands.GuildNotFound):
                embed.add_field(name="Сообщение", value=f"Сервер {exception.argument} не найден")
            elif isinstance(exception, commands.UserNotFound):
                embed.add_field(name="Сообщение", value=f"Пользователь {exception.argument} не найден")
            elif isinstance(exception, commands.MessageNotFound):
                embed.add_field(name="Сообщение", value=f"Сообщение {exception.argument} не найдено")
            elif isinstance(exception, commands.ChannelNotReadable):
                embed.add_field(name="Сообщение", value=f"Я не могу просматривать канал {exception.argument}")
            elif isinstance(exception, commands.ChannelNotFound):
                embed.add_field(name="Сообщение", value=f"{exception.argument}")
            elif isinstance(exception, commands.BadColourArgument):
                embed.add_field(name="Сообщение", value=f"Цвет {exception.argument} не действителен")
            elif isinstance(exception, commands.RoleNotFound):
                embed.add_field(name="Сообщение", value=f"Роль {exception.argument} не найдена")
            elif isinstance(exception, commands.BadInviteArgument):
                embed.add_field(name="Сообщение", value="Приглашение недействительно или истекло")
            elif isinstance(exception, commands.EmojiNotFound):
                embed.add_field(name="Сообщение", value=f"Эмодзи {exception.argument} не найдено")
            elif isinstance(exception, commands.BadBoolArgument):
                embed.add_field(name="Сообщение",
                                value=f"{exception.argument} не является распознанной логической опцией")
            elif isinstance(exception, commands.PartialEmojiConversionFailure):
                embed.add_field(name="Сообщение", value=f"Не удалось преобразовать {exception.argument} в эмодзи")
            else:
                embed.add_field(name="Сообщение", value="Неверный тип одного из аргументов ")
                embed.add_field(name="Помощник", value=(
                    "Используй `{}help {}` чтобы узнать как правильно оформлять команду".format(
                        self.command_prefix, ctx.invoked_with)))
        elif isinstance(exception, commands.CheckFailure):
            if isinstance(exception, commands.NotOwner):
                embed.add_field(name="Сообщение", value="Эта команда доступна только разработчикам")
            elif isinstance(exception, commands.PrivateMessageOnly):
                embed.add_field(name="Сообщение", value="Эта команда не доступна в групповых чатах")
            elif isinstance(exception, commands.NoPrivateMessage):
                embed.add_field(name="Сообщение", value="Эта команда не доступна в личных чатах")
            elif isinstance(exception, commands.BotMissingPermissions):
                embed.add_field(name="Сообщение", value="У меня не достаточно прав!")
            elif isinstance(exception, commands.MissingPermissions):
                embed.add_field(name="Сообщение", value="У вас недостаточно прав!")
            elif isinstance(exception, commands.NSFWChannelRequired):
                embed.add_field(name="Сообщение", value="Эта команда доступна только в NSFW каналах")
            else:
                embed.add_field(name="Сообщение", value="Вам недоступна эта команда")
        elif isinstance(exception, commands.CommandNotFound):
            embed.add_field(name="Сообщение", value="Команды '{}' не существует".format(ctx.invoked_with))
        elif isinstance(exception, commands.CommandOnCooldown):
            embed.add_field(
                name="Сообщение",
                value=f"Погоди остынь! Повтори попытку через {HRF.time(timedelta(seconds=exception.retry_after))}"
            )

        else:
            embed.add_field(name="Сообщение", value="Неизвестная ошибка")
            await super().on_command_error(ctx, exception)

        if await self.is_owner(user=ctx.author):
            embed.add_field(name="SysMsg", value="`{}: {}`".format(type(exception), exception))

        await ctx.reply(embed=embed)

    async def on_after_invoke(self, _):
        self.count_invokes += 1

    # Полезные методы #####################################################
    def add_cogs(self, *cogs: commands.Cog):
        for cog in cogs:
            self.add_cog(cog)

    def add_models(self, *models):
        if not models:
            raise ValueError("Укажите классы моделей")
        for model in models:
            if model.__name__ in self.__models:
                raise ValueError(f"Модель {model.__name__} уже зарегистрирована или передана дважды")
            self.__models[model.__name__] = model

    def add_cog_blueprint(self, blueprint, *args, url_prefix: str, **kwargs):
        self.add_blueprint(blueprint.blueprint, *args, url_prefix=url_prefix, **kwargs)

        self.__cog_blueprints[url_prefix] = blueprint

        if self.flask_app:  # Добавляем в сам flask только если мы его вкл.
            self.flask_app.register_blueprint(blueprint.blueprint, *args, url_prefix=url_prefix, **kwargs)

    def add_blueprint(self, blueprint: Blueprint, *args, url_prefix: str, **kwargs):
        if url_prefix in self.__blueprints:
            raise ValueError(f"На prefix_url='{url_prefix}' уже зарегистрирован blueprint")

        self.__blueprints[url_prefix] = blueprint

        if self.flask_app:  # Добавляем в сам flask только если мы его вкл.
            self.flask_app.register_blueprint(blueprint, *args, url_prefix=url_prefix, **kwargs)

    def get_voice_client(self, guild: discord.Guild) -> Optional[VoiceClient]:
        return get(self.voice_clients, guild=guild)

    # Команды #####################################################
    async def process_commands(self, message: discord.Message):
        if message.author.bot:
            return

        ctx: Context = await self.get_context(message, cls=Context)

        # Смотрим. Можем ли мы отправить help через знак ?
        split = ctx.message.content.split()
        if ctx.command is not None and len(split) == 2 and split[1] == '?':
            # Если да то отправляем help по возможности
            invoked_help = bool(await ctx.send_help(ctx.invoked_with))
        else:
            invoked_help = False

        if not invoked_help:
            # В случае безуспешной отправки help мы вызываем функцию
            await self.invoke(ctx)

        if ctx.command:
            logging.info(f"[INVOKE] [{ctx.command}] {ctx.args} {ctx.kwargs}")

    def reload_command(self, name: str) -> commands.Command:
        command = self.remove_command(name)
        self.add_command(command)
        return command

    # Взаимодействие с cogs #####################################################
    def load_all_extensions(self, filenames: list):
        """Загружаем все указанные расширения. Желательно вызвать эту функцию перед выходом в сеть"""

        logging.info("=" * 6 + f"Загружаем расширения" + "=" * 6)
        for i, filename in enumerate(filenames, start=1):
            try:
                logging.info(f"Загружаем {filename} ({i}/{len(filenames)})")
                __import__(filename, fromlist='setup').setup(self)

            except ImportError as E:
                logging.warning(f"Ошибка загрузки в {filename} '{E.__class__.__name__}: {E}'")
                raise E

        logging.info("=" * 6 + f"Загрузка выполнена" + "=" * 6)

    def reload_all_extensions(self):
        for ext in self.extensions:
            self.reload_extension(ext)

    # Глобальное взаимодействие с данными #####################################################
    def update_all_data(self, session: db_session.Session):
        Guild.update_all(session, self.guilds)
        User.update_all(session, self.users)
        Member.update_all(session, self.get_all_members())

        logging.info('=' * 6 + 'Обновление бд выполнено' + '=' * 6)

    # routes для Flask #####################################################
    def index_api(self):
        response = {"cogs": {}}
        for url_rule, bp in self.__cog_blueprints.items():
            if hasattr(bp, "cog"):
                response["cogs"][bp.cog.qualified_name] = url_rule
        return response

    # TODO: Сделать получение уникального Prefix для каждого сервера

    # Runner #####################################################
    def run(self, *args, **kwargs):
        if self.using_db:
            db_session.global_init(self.__db_connect, self.__models)

        loop = self.loop

        async def runner_discord():
            try:
                await self.start(*args, **kwargs)
            finally:
                if not self.is_closed():
                    await self.close()

        async def runner_flask():
            try:
                thread = Thread(target=self.flask_app.run, kwargs={"host": '0.0.0.0', "port": 80}, daemon=True)
                thread.start()
                while thread.is_alive():
                    await asyncio.sleep(1)
            finally:
                pass

        def stop_loop_on_completion(_):
            loop.stop()

        future = asyncio.ensure_future(runner_discord(), loop=loop)
        future.add_done_callback(stop_loop_on_completion)

        if self.using_db and self.flask_app and self.__cog_blueprints:
            # Если есть хотя бы 1 указанный blueprint и вкл. flask,
            # то запускаем flask сервер
            future2 = asyncio.ensure_future(runner_flask(), loop=loop)
            future2.add_done_callback(stop_loop_on_completion)

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            logging.info('Received signal to terminate bot and event loop.')
        finally:
            future.remove_done_callback(stop_loop_on_completion)


class Cog(commands.Cog, name="Без названия"):
    cls_config: BaseConfigMix
    count_inited = 0
    count_ready = 0

    def __init__(self, bot: Bot, cls_config=None):
        self.bot = bot
        if cls_config is not None:
            assert self.bot.using_db, "Для работы модуля необходимо использование базы данных"
        self.cls_config: Type[cls_config.__class__] = cls_config
        self._skip_check_access = False

        if cls_config is not None:
            self.bot.add_models(cls_config)
        Cog.count_inited += 1

    def __repr__(self):
        return str(self)

    def __str__(self):
        return self.__class__.__name__ + '()'

    @property
    def using_db(self):
        return self.bot.using_db

    @full_using_db(default_return=True, is_async=True)
    async def cog_check(self, ctx):
        """
        Базовая проверка для команд в категории
        """
        ctx: Context
        await self.bot.wait_until_ready()

        with db_session.create_session() as session:
            session: db_session.Session

            async def check_guild(guild_: discord.Guild) -> bool:
                if Guild.get(session, guild_).ban_activity:
                    return False
                if self.cls_config is not None:
                    config = self.update_config(session, guild_)
                    session.commit()
                    if not config.check_active_until():
                        return False

                    if not self._skip_check_access and not await config.check_access(ctx):
                        return False
                return True

            if ctx.guild:
                return await check_guild(ctx.guild)

            guilds = set(
                map(lambda m: self.bot.get_guild(m.guild_id),
                    session.query(Member).filter(Member.id == ctx.author.id).all()))
            result = False
            for guild in set(filter(bool, guilds)):
                result = await check_guild(guild) or result
            return result

    # Слушатели
    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()

        if self.using_db and self.cls_config is not None:
            with db_session.create_session() as session:
                for guild in self.bot.guilds:
                    self.update_config(session, guild)
                session.commit()

        Cog.count_ready += 1

        logging.info(f'{self.__class__.__name__}: Готов! (Всего {Cog.count_ready}/{Cog.count_inited})')

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        if self.using_db and self.cls_config:
            with db_session.create_session() as session:
                self.update_config(session, guild)
                session.commit()
                logging.info(f'{guild} has been added in table "{self.cls_config.__tablename__}"')

    # Методы для работы с конфигами категории
    @full_using_db()
    def get_config(self, session: db_session.Session, guild: Union[discord.Guild, int]) -> Optional[BaseConfigMix]:
        assert self.cls_config, "Метод может быть использован только при определённом заранее cls_config"
        guild_id = guild.id if isinstance(guild, discord.Guild) else guild
        return session.query(self.cls_config).filter(self.cls_config.guild_id == guild_id).first()

    @full_using_db()
    def update_config(self, session: db_session, guild: discord.Guild):  # TODO: Утечка скорости (Много повторов)
        assert self.cls_config, "Метод может быть использован только при определённом заранее cls_config"

        config = self.get_config(session, guild)

        # Создаём новый конфиг если не был найден
        if config is None:
            config = self.cls_config()
            config.guild_id = guild.id
            session.add(config)

        # Установка базовых прав доступа по возможности и очистка неиспользуемых прав
        try:
            access: dict = config.get_access()

            # Очищаем всё что пусто
            for key in set(access.keys()):
                if not access[key]:
                    del access[key]

            # Добавляем всё недостающее
            print('-----------')
            for command in self.get_commands():
                command: commands.Command
                print(command, command.parents, guild)
                if str(command) not in access:
                    access[str(command)] = {}
            if "__cog__" not in access:
                access["__cog__"] = {}

            # Устанавливаем новые права
            config.set_access(access)
        except AttributeError:
            pass

        return config

    @staticmethod
    def on_func_error(coro):
        # TODO: Тип обработчик ошибок. Но нужно доработать (для before_invoke)
        def wrapper(function):
            async def wp(self, ctx, *args, **kwargs):
                try:
                    return await function(ctx, *args, **kwargs)
                except Exception as error:
                    await coro(self, ctx, error)

            return wp

        return wrapper


class Context(commands.Context):
    bot: Optional[Bot]

    def __init__(self, **attrs):
        super().__init__(**attrs)
        self.bot: Optional[Bot]
        self.args: list
        self.kwargs: dict
        self.command: Optional[commands.Command]

    def __str__(self):
        return "{}(cmd={}{} cog={} msg={}  author={} guild={})".format(
            self.__class__.__name__, self.prefix, self.command or self.invoked_with,
            self.getattr(self.cog, 'qualified_name'), self.getattr(self.message, 'id'),
            self.getattr(self.author, 'id'), self.getattr(self.guild, 'id'))

    def __repr__(self):
        return self.__class__.__name__ + f"(cmd={self.prefix}{self.command or self.invoked_with} " \
                                         f"cog={self.getattr(self.cog, 'qualified_name')})"

    @property
    def cog(self) -> Optional[commands.Cog]:
        return super(Context, self).cog

    @discord.utils.cached_property
    def guild(self) -> Optional[discord.Guild]:
        return super(Context, self).guild

    @discord.utils.cached_property
    def channel(self) -> Union[discord.abc.Messageable, discord.TextChannel]:
        return super(Context, self).channel

    @discord.utils.cached_property
    def author(self) -> Union[discord.User, discord.Member]:
        return super(Context, self).author

    @discord.utils.cached_property
    def me(self) -> Union[discord.Member, discord.ClientUser]:
        return super(Context, self).me

    @property
    def voice_client(self) -> Optional[Union[discord.VoiceProtocol, discord.VoiceClient]]:
        return super(Context, self).voice_client

    @staticmethod
    def getattr(a, attr=None, default=None):
        return (getattr(a, attr) if attr else a) if a else default


Cog.cog_check.__annotations__['ctx'] = Context
