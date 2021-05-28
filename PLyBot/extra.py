import datetime
import gc
import logging
import re
from typing import Union, Optional, Type, Iterable, Callable, List

import discord
from discord import Status

import db_session
from db_session.base import Guild, Member, User, Message

logging = logging.getLogger(__name__)

T = Type['T']


class Check:
    __value = False
    value = property()

    def __bool__(self):
        return self.__value

    def __str__(self):
        return f"{self.__class__.__name__}(act={self.__value})"

    def toggle(self) -> bool:
        self.__value = not self.__value
        return self.__value

    @value.getter
    def value(self) -> bool:
        return self.__value

    @value.setter
    def value(self, b: bool):
        self.__value = bool(b)


class HRF:
    @staticmethod
    def number(number: int) -> str:
        assert isinstance(number, int), "Число должно быть типа int"

        if not number % 1:
            number = int(number)

        m = 1 if number >= 0 else -1
        number = abs(number)

        d = {1: "тыс.", 2: "млн", 3: "млрд", 4: "трлн", 5: "квдр", 6: "квнт", 7: "скст",
             8: "септ", 9: "октл", 10: "ннл", 11: "дцл", 12: "aнд", 13: "ддц", 14: "трдц"}

        for i in range(len(d.keys()), 0, -1):
            if number // (1000 ** i * 10) != 0:
                return f"{number // 1000 ** i * m} {d[i]}."

        return str(number * m)

    @staticmethod
    def time(time: datetime.timedelta, big=True, medium=True, small=False, sep=" ") -> str:
        result = []

        years = time.days // 365
        days = time.days % 365

        hours = time.seconds // 3600
        minutes = time.seconds // 60
        seconds = time.seconds % 60

        milliseconds = time.microseconds // 1000
        microseconds = time.microseconds % 1000

        if big:
            if years:
                result.append(f"{years} г.")
            if days:
                result.append(f"{days} сут.")

        if medium:
            if hours:
                result.append(f"{hours} ч.")
            if minutes:
                result.append(f"{minutes} м.")
            if seconds:
                result.append(f"{seconds} с.")

        if small:
            if milliseconds:
                result.append(f"{seconds} мс.")
            if microseconds:
                result.append(f"{seconds} мкс.")

        return sep.join(result).strip()

    @staticmethod
    def full_time(time: datetime.timedelta, include_small_time=False) -> str:
        # TODO: сделать с полными обозначениями
        return HRF.time(time, include_small_time)

    @staticmethod
    def beautiful_number(number: Union[float, int]) -> str:
        if not number % 1:
            number = int(number)
        return str(number)


class DBTools:
    # Некоторые манипуляции с бд о участниках серверов
    @staticmethod
    def get_all_guilds(session: db_session.Session) -> List[Guild]:
        return session.query(Guild).all()

    @staticmethod
    def update_all_guilds(session: db_session.Session, guilds: Iterable[Guild]):
        ids = set(guild.id for guild in guilds)
        for guild_data in DBTools.get_all_guilds(session):
            if guild_data.id not in ids:
                # TODO: Очистка участников, ролей и каналов гильдии
                session.delete(guild_data)

        for guild in guilds:
            DBTools.update_guild(session, guild)

    @staticmethod
    def get_guild(session: db_session.Session, guild: discord.Guild) -> Optional[Guild]:
        return session.query(Guild).filter(Guild.id == guild.id).first()

    @staticmethod
    def add_guild(session: db_session.Session, guild: discord.Guild) -> Guild:
        if DBTools.get_guild(session, guild):
            raise ValueError("Такой сервер уже есть")

        guild_data = Guild()
        guild_data.id = guild.id
        guild_data.owner_id = guild.owner_id
        guild_data.name = guild.name
        guild_data.mfa_level = guild.mfa_level
        guild_data.verification_level = guild.verification_level
        guild_data.region = guild.region
        guild_data.icon = guild.icon
        guild_data.afk_channel = guild.afk_channel.id if guild.afk_channel else None
        guild_data.default_role = guild.default_role.id

        session.add(guild_data)
        return guild_data

    @staticmethod
    def update_guild(session: db_session.Session, guild: discord.Guild) -> Guild:
        guild_data = DBTools.get_guild(session, guild)
        if not guild_data:
            guild_data = DBTools.add_guild(session, guild)
        else:
            guild_data.id = guild.id
            guild_data.owner_id = guild.owner_id
            guild_data.name = guild.name
            guild_data.mfa_level = guild.mfa_level
            guild_data.verification_level = guild.verification_level
            guild_data.region = guild.region
            guild_data.icon = guild.icon
            guild_data.afk_channel = guild.afk_channel.id if guild.afk_channel else None
            guild_data.default_role = guild.default_role.id

        return guild_data

    @staticmethod
    def delete_guild(session: db_session.Session, guild: discord.Guild) -> Guild:
        guild = DBTools.get_guild(session, guild)
        if not guild:
            raise ValueError("Такого сервера нет в базе")
        session.delete(guild)
        return guild

    @staticmethod
    def get_all_members(session: db_session.Session) -> List[Member]:
        return session.query(Member).all()

    @staticmethod
    def update_all_members(session: db_session.Session, members: Iterable[Member]):
        pass

    @staticmethod
    def get_member(session: db_session.Session, member: discord.Member) -> Optional[Member]:
        return session.query(Member).filter(Member.id == member.id, Member.guild_id == member.guild.id).first()

    @staticmethod
    def add_member(session: db_session.Session, member: discord.Member) -> Member:
        if DBTools.get_member(session, member):
            raise ValueError("Участник уже есть в базе")
        member_data = Member()

        member_data.user_id = member.id
        member_data.guild_id = member.guild.id
        member_data.display_name = member.display_name
        member_data.joined_at = member.joined_at
        member_data.desktop_status = member.desktop_status
        member_data.mobile_status = member.mobile_status
        member_data.web_status = member.web_status

        session.add(member_data)
        return member_data

    @staticmethod
    def update_member(session: db_session.Session, member: discord.Member) -> Member:
        member_data = DBTools.get_member(session, member)
        if not member_data:
            m = DBTools.add_member(session, member)
        else:
            member_data.user_id = member.id
            member_data.guild_id = member.guild.id
            member_data.display_name = member.display_name
            member_data.joined_at = member.joined_at
            member_data.desktop_status = member.desktop_status
            member_data.mobile_status = member.mobile_status
            member_data.web_status = member.web_status
        return member_data

    @staticmethod
    def delete_member(session: db_session.Session, member: discord.Member) -> Member:
        member_data = DBTools.get_member(session, member)
        if not member_data:
            raise ValueError("Такого участника нет в базе")
        session.delete(member_data)
        return member_data

    @staticmethod
    def get_all_users(session: db_session.Session):
        return session.query(User).all()

    @staticmethod
    def update_all_users(session: db_session.Session, users: Iterable[User]):
        pass

    @staticmethod
    def get_user(session: db_session.Session, user: Union[discord.User, discord.Member]) -> Optional[User]:
        return session.query(User).filter(User.id == user.id).first()

    @staticmethod
    def add_user(session: db_session.Session, user: Union[discord.User, discord.Member]) -> User:
        if DBTools.get_user(session, user):
            raise ValueError("Участник уже в базе")
        u = User()
        u.id = user.id
        u.nick = str(user)
        u.bot = user.bot
        u.created_at = user.created_at
        session.add(u)
        return u

    @staticmethod
    def update_user(session: db_session.Session, user: Union[discord.User, discord.Member]) -> User:
        u = DBTools.get_user(session, user)
        if not u:
            u = DBTools.add_user(session, user)
        else:
            u.id = user.id
            u.nick = str(user)
            u.bot = user.bot
            u.created_at = user.created_at
        return u

    @staticmethod
    def delete_user(session: db_session.Session, user: Union[discord.User, discord.Member]) -> User:
        u = DBTools.get_user(session, user)
        if not u:
            raise ValueError("Такого участника нет в базе")
        session.delete(u)
        return u

    # @staticmethod
    # def get_msg_data(session: db_session.Session, message: discord.Message) -> Optional[Message]:
    #     return session.query(Message).filter(Message.id == message.id).first()
    # @staticmethod
    # def add_msg(session: db_session.Session, message: discord.Message) -> Message:
    #     if DBTools.get_msg_data(session, message):
    #         raise ValueError("Такое сообщение уже есть")
    #     msg = Message()
    #     msg.id = message.id
    #     if message.guild:
    #         msg.guild = message.guild.id
    #     msg.author = message.author.id
    #     msg.channel = message.channel.id
    #     msg.content = message.content
    #     msg.has_mentions = bool(message.mentions)
    #     msg.has_mentions_roles = bool(message.role_mentions)
    #     msg.has_mentions_everyone = bool(message.mention_everyone)
    #     msg.timestamp = message.created_at.timestamp()
    #     session.add(msg)
    #     return msg
    # @staticmethod
    # def update_msg(session: db_session.Session, message: discord.Message) -> Message:
    #     msg = DBTools.get_msg_data(session, message)
    #     if not msg:
    #         msg = DBTools.add_msg(session, message)
    #     else:
    #         msg.id = message.id
    #         if message.guild:
    #             msg.guild = message.guild.id
    #         msg.author = message.author.id
    #         msg.channel = message.channel.id
    #         msg.content = message.content
    #         msg.has_mentions = bool(message.mentions)
    #         msg.has_mentions_roles = bool(message.role_mentions)
    #         msg.has_mentions_everyone = bool(message.mention_everyone)
    #         msg.timestamp = message.created_at.timestamp()
    #     return msg
    # @staticmethod
    # def delete_msg(session: db_session.Session, message: discord.Message) -> Message:
    #     m = DBTools.get_msg_data(session, message)
    #     if not m:
    #         raise ValueError("Такого сообщения нет в базе")
    #     session.delete(m)
    #     return m
    pass


def full_db_using(*, default=None, is_async=False):
    def wp(func):
        nonlocal default

        if is_async:
            async def new(self, *args, **kwargs):
                nonlocal default
                if not self.using_db:
                    return default
                else:
                    return await func(self, *args, **kwargs)
        else:
            def new(self, *args, **kwargs):
                nonlocal default
                if not self.using_db:
                    return default
                else:
                    return func(self, *args, **kwargs)
        return new

    return wp


def plug_func(res_default=None):
    def decorator(func):
        nonlocal res_default
        logging.warning(f"use plug func {func}. returned: '{repr(res_default)}'")
        return lambda *_, **__: res_default

    return decorator


def plug_afunc(res_default=None):
    def decorator(func):
        nonlocal res_default
        logging.warning(f"use plug afunc {func}. returned: '{repr(res_default)}'")

        async def wp(*args, **kwargs):
            return res_default

        return wp

    return decorator


def equal(value_a):
    def wp(value_b):
        nonlocal value_a
        return value_a == value_b

    return wp


def not_equal(value_a):
    def wp(value_b):
        nonlocal value_a
        return value_a != value_b

    return wp


def not_in(value_a):
    def wp(value_b):
        return value_b not in value_a

    return wp


def in_(value_a):
    def wp(value_b):
        return value_b in value_a

    return wp


def get_obj(obj_id: Union[int, str]):
    if isinstance(obj_id, str):
        obj_id = int(obj_id, 16)
    elif not isinstance(obj_id, int):
        raise TypeError
    for obj in gc.get_objects():
        if id(obj) == obj_id:
            return obj
    raise ValueError(f"Ничего не найдено c id == {repr(obj_id)}")


def join_string(args: tuple, default="") -> str:
    return " ".join(args) if args else default


def get_time_from_string(string: str) -> datetime.timedelta:
    default = ["0_"]
    days = re.search(r'\b-?\d+(\.)?\d*[дd]\b', string) or default
    hours = re.search(r'\b-?\d+(\.)?\d*[чh]\b', string) or default
    minutes = re.search(r'\b-?\d+(\.)?\d*[мm]\b', string) or default
    seconds = re.search(r'\b-?\d+(\.)?\d*[сs]\b', string) or default
    return datetime.timedelta(days=float(days[0][:-1]),
                              hours=float(hours[0][:-1]),
                              minutes=float(minutes[0][:-1]),
                              seconds=float(seconds[0][:-1]))


def get_any(__iterable: Iterable[T], key: Callable = bool) -> Optional[T]:
    for elem in __iterable:
        if key(elem):
            return elem
