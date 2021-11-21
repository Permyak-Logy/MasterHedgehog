import random

import discord
import sqlalchemy
from discord.ext import commands

from PLyBot import Bot, Cog
from PLyBot.const import EMOJI_NUMBERS
from db_session import SqlAlchemyBase, BaseConfigMix, MIN_DATETIME


class RandomConfig(SqlAlchemyBase, BaseConfigMix):
    __tablename__ = "random_configs"

    guild_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('guilds.id'),
                                 primary_key=True, nullable=False)
    access = sqlalchemy.Column(sqlalchemy.String, nullable=False, default='{}')
    active_until = sqlalchemy.Column(sqlalchemy.Date, nullable=True, default=MIN_DATETIME)


class RandomCog(Cog, name='Случайности'):
    """
    Модуль для получения различных случайностей!
    """

    def __init__(self, bot: Bot):
        super().__init__(bot, cls_config=RandomConfig)

    @commands.group('random', aliases=['rand'])
    async def _group_random(self, ctx: commands.Context):
        """
        Генерирует число в диапазоне [0.0:1.0]
        """

        await ctx.reply(str(random.random()))

    @_group_random.command('choice')
    async def _cmd_rand_choice(self, ctx: commands.Context, *items):
        """
        Выбирает случайным образом один из элементов указанных через пробел
        """

        assert len(items) > 0, "Нет предметов для выбора"

        item = random.choice(items)
        phrase = random.choice([
            f'Иии... я выбираю "{item}"',
            f'Мой выбор: "{item}"',
            f'Знаки указывают на "{item}"',
            f'{item}',
            'Я щас не в настроении... Спроси ещё раз!'
        ])

        await ctx.reply(phrase)

    @_group_random.command('int')
    async def _cmd_rand_int(self, ctx: commands.Context, start: int, end: int):
        """
        Выбирает случайное число в диапазоне [start:end]
        """

        assert start <= end, "start должен быть <= end"

        await ctx.reply(str(random.randint(start, end)))

    @_group_random.command('range')
    async def _cmd_rand_range(self, ctx: commands.Context, start: int, end: int):
        """
        Выбирает случайное число в диапазоне [start:end)
        """

        assert start < end, "start должен быть меньше end"

        await ctx.reply(str(random.randrange(start, end)))

    @commands.command('шар', aliases=['ball', 'ш', 'q'])
    async def _cmd_ball(self, ctx: commands.Context, question: str):
        """
        Пусть шар судьбы ответит на ваш вопрос
        """
        phrases = [
            "Да",
            "скорее всего",
            "100%",
            "очень вероятно",

            "духи говорят нет",
            "думаю нет",
            "Шансы хорошие",
            "есть сомнения",

            "точно нет",
            "Не ясно",
            "непонятно",
            "спросите снова",
            "не сейчас",
        ]
        await ctx.reply(random.choice(phrases).capitalize().format(question))

    @commands.command('die')
    async def _cmd_die(self, ctx: commands.Context, count: int = 1):
        """
        Бросает count шестигранных кубиков
        """
        assert 1 <= count <= 10, "Count от 1 до 10 принимает значения"
        results = [random.randint(1, 6) for _ in range(count)]
        total = sum(results)
        results = list(map(EMOJI_NUMBERS.get, results))
        await ctx.reply(embed=discord.Embed(description=" + ".join(results) + f" = {total}"))


def setup(bot: Bot):
    bot.add_cog(RandomCog(bot))
