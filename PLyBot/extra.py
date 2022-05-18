import datetime
import gc
import logging
import re
from typing import Union, Optional, Type, Iterable, Callable
from discord.ext import commands
from discord import Status
import asyncio

__logging = logging.getLogger(__name__)
__old_f = commands.group

ONLINE = 1
OFFLINE = 2
IDLE = 3
DND = 4
INVISIBLE = 5
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

        d = {1: "тыс.", 2: "млн.", 3: "млрд.", 4: "трлн.", 5: "квдр.", 6: "квнт.", 7: "скст.",
             8: "септ.", 9: "октл.", 10: "ннл.", 11: "дцл.", 12: "aнд.", 13: "ддц.", 14: "трдц."}

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
                result.append(f"{milliseconds} мс.")
            if microseconds:
                result.append(f"{microseconds} мкс.")

        return sep.join(result).strip()

    @staticmethod
    def full_time(time: datetime.timedelta, include_small_time=False) -> str:
        return HRF.time(time, include_small_time)

    @staticmethod
    def beautiful_number(number: Union[float, int]) -> str:
        if not number % 1:
            number = int(number)
        return str(number)


class Permissions:
    VIEW = 1
    EDIT = 2

    @staticmethod
    def make(**flags) -> int:
        flag = 0

        flag |= Permissions.VIEW if flags.pop('view', 0) else 0
        flag |= Permissions.EDIT if flags.pop('edit', 0) else 0

        if flags:
            raise TypeError(f'Передан неизвестный ключ {flags}')

        return flag


async def timer(sec: float, func):
    await asyncio.sleep(sec)
    return func()


async def atimer(sec: float, afunc):
    await asyncio.sleep(sec)
    return await afunc


def group(name=None, invoke_without_command=True, **attrs):
    return __old_f(name, invoke_without_command=invoke_without_command, **attrs)


def full_using_db(*, default_return=None, is_async=False):
    """Декоратор СТРОГО для методов класса PLyBot.bot.Bot"""

    def wp(func):
        if is_async:
            async def new(self, *args, **kwargs):
                if self.using_db:
                    return await func(self, *args, **kwargs)
                return default_return
        else:
            def new(self, *args, **kwargs):
                if self.using_db:
                    return func(self, *args, **kwargs)
                return default_return

        return new

    return wp


def run_if_ready_db(*, default_return=None, is_async=False):
    """Декоратор СТРОГО для методов класса PLyBot.bot.Bot"""

    def wp(func):
        if is_async:
            async def new(self, *args, **kwargs):
                if self.ready_db:
                    return await func(self, *args, **kwargs)
                return default_return
        else:
            def new(self, *args, **kwargs):
                if self.ready_db:
                    return func(self, *args, **kwargs)
                return default_return
        return new

    return wp


def plug_func(res_default=None):
    def decorator(func):
        nonlocal res_default
        __logging.warning(f"use plug func {func}. returned: '{repr(res_default)}'")
        return lambda *_, **__: res_default

    return decorator


def plug_afunc(res_default=None):
    def decorator(func):
        nonlocal res_default
        __logging.warning(f"use plug afunc {func}. returned: '{repr(res_default)}'")

        async def wp(*_, **__):
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


def cast_status_to_int(status) -> int:
    if status == Status.online:
        return ONLINE
    if status == Status.offline:
        return OFFLINE
    if status == Status.idle:
        return IDLE
    if status == Status.dnd:
        return DND
    if status == Status.invisible:
        return INVISIBLE
    return -1


def get_any(__iterable: Iterable[T], key: Callable = bool) -> Optional[T]:
    for elem in __iterable:
        if key(elem):
            return elem


commands.group = group  # Глобальная замена group в commands
