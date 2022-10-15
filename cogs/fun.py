import asyncio
import logging
import random

import discord
import pyttsx3
from discord.ext import commands
from sqlalchemy import Column, ForeignKey, Integer, String, Date

import db_session
from PLyBot import Bot, Cog, Context, BotEmbed
from PLyBot.const import TEXT_EMOJI_NUMBERS
from db_session import SqlAlchemyBase, BaseConfigMix
from db_session.base import Message

try:
    from other import swift
    # swift = __import__('other', fromlist=['swift'])
except ImportError:
    swift = object()
    setattr(swift, 'words', [])

logging = logging.getLogger(__name__)


class FunConfig(SqlAlchemyBase, BaseConfigMix):
    __tablename__ = "fun_configs"

    guild_id = Column(Integer, ForeignKey('guilds.id'),
                      primary_key=True, nullable=False)
    access = Column(String, nullable=False, default='{}')
    active_until = Column(Date, nullable=True, default=None)

# TODO: Счётчик сообщений в канале
class FunCog(Cog, name="Веселье"):
    def __init__(self, bot: Bot):
        super().__init__(bot, cls_config=FunConfig, emoji_icon='😂')

    @staticmethod
    async def get_words(ctx: Context):
        with db_session.create_session() as session:
            # noinspection PyShadowingBuiltins
            def format_sentence(line: str):
                if not line or not set(filter(lambda x: x.isalnum(), set(line))) or not line.strip()[0].isalnum():
                    return ""
                symbols = set(filter(lambda x: not x.isalnum(), set(line)))
                for symbol in symbols:
                    line = line.replace(symbol, ' ' + symbol + ' ')
                line = line.replace('  ', ' ').strip()
                return line.lower()

            all_messages = session.query(Message).filter(Message.content != "",
                                                         Message.has_mentions == False,
                                                         Message.has_mentions_roles == False,
                                                         Message.has_mentions_everyone == False,
                                                         Message.guild == ctx.guild.id).all()

            await asyncio.sleep(0.0001)
            words = swift.words.copy()
            for sentence in map(lambda x: format_sentence(x.content), all_messages):
                await asyncio.sleep(0.000001)
                if sentence:
                    words += sentence.split()
        return words

    @commands.command('load_all_msgs')
    @commands.is_owner()
    @commands.guild_only()
    async def _cmd_load_all_msgs(self, ctx: Context):
        count = 0
        async with ctx.typing():
            with db_session.create_session() as session:
                session: db_session.Session

                guild: discord.Guild = ctx.guild
                for channel in guild.text_channels:
                    # noinspection PyBroadException
                    try:
                        async for message in channel.history():
                            count += 1
                            Message.update(session, message)
                            await asyncio.sleep(0.00001)
                    except Exception:
                        pass
                session.commit()
        await ctx.reply(embed=BotEmbed(ctx=ctx, description=f"Готово! Обновлено сообщений {count}"))

    @commands.command(name="слово", aliases=["word", "w", "бред"])
    @commands.cooldown(1, 0.1 * 60, type=commands.BucketType.guild)
    @commands.guild_only()
    async def _cmd_word(self, ctx: Context, cursor: str = None, level: int = 3):
        """
        Генератор бредовых предложений. Делает их из книги и на основе сообщений сервера
        """
        assert level >= 2, "Слишком маленький показатель бреда. Значение должно быть >= 2"

        async with ctx.typing():
            words = await self.get_words(ctx)
            count_words = len(words)

            cursor: str = "я" if cursor not in words else cursor
            last_words = [cursor]
            sentence = cursor

            while cursor != '.' and len(sentence) <= 1900:
                indexes = []
                for i in range(level - 1, count_words):
                    if all(map(lambda x: last_words[-x] == words[i - x], range(1, min(len(last_words), level)))):
                        indexes.append(i)

                assert indexes, "Упс. Я тут остановился и в общем... упал!!"

                cursor = words[random.choice(indexes)]
                if cursor.isalnum():
                    sentence += " "
                sentence += cursor

                last_words.append(cursor)
                if len(last_words) > level:
                    del last_words[0]

                await asyncio.sleep(0.00001)

            await ctx.reply(embed=BotEmbed(ctx=ctx, description=sentence))

    @commands.command('say', enabled=False)
    @commands.is_owner()
    @commands.guild_only()
    async def _cmd_say(self, ctx: Context, member: discord.Member, *, text: str):
        engine = pyttsx3.init()
        filename = f"audio\\{ctx.guild.id}-{ctx.author.id}-{member.id}.mp3"
        engine.save_to_file(text, filename)
        engine.runAndWait()
        from cogs.music import MusicCog
        cog: MusicCog = self.bot.get_cog('Музыка')
        voice_m: discord.VoiceState = member.voice
        channel: discord.VoiceChannel = voice_m.channel
        try:
            voice = await channel.connect()
        except discord.ClientException as E:
            logging.error(str(E))
            voice = self.bot.get_voice_client(ctx.guild)
        # await cog.start_play(voice, filename)  TODO: Вернуть

        import os
        if os.path.isfile(filename):
            os.remove(filename)

    @commands.command('say_pc', enabled=False)
    @commands.is_owner()
    async def _cmd_say_pc(self, _: Context, *, text: str):
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()

    @commands.command('sapper', aliases=['сапёр'])
    async def _cmd_sapper(self, ctx: Context, width: int = 9, height: int = 9, count: int = 10):
        """
        Отправляет текстовое сообщение для игры в сапёра
        """
        assert width * height >= count, "Слишком много бомб для игрового поля"

        points = list()

        for x in range(width):
            for y in range(height):
                points.append((x, y))

        bombs = [points.pop(random.randrange(0, len(points))) for _ in range(count)]

        field = [["" for _ in range(width)] for __ in range(height)]
        for point in points:
            bombs_count = 0
            for i in range(9):
                x = i % 3 - 1 + point[0]
                y = i // 3 - 1 + point[1]
                if not i % 3 - 1 == i // 3 - 1 == 0:
                    if (x, y) in bombs:
                        bombs_count += 1
            field[point[1]][point[0]] = f"||:{TEXT_EMOJI_NUMBERS[bombs_count]}:||"

        for bomb in bombs:
            field[bomb[1]][bomb[0]] = "||:boom:||"

        map_sapper = "\n".join(map("".join, field))
        await ctx.reply(
            embed=BotEmbed(ctx=ctx, title=f"Сапёр {width}x{height} с {count} бомбами", description=map_sapper))


async def setup(bot: Bot):
    await bot.add_cog(FunCog(bot))
