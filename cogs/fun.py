import asyncio
import logging
import random

import discord
import pyttsx3
from discord.ext import commands

import db_session
from PLyBot import Bot, Cog, Context, BotEmbed
from PLyBot.const import TEXT_EMOJI_NUMBERS
from db_session.base import Message
from db_session import SqlAlchemyBase, BaseConfigMix, MIN_DATETIME
from sqlalchemy import Column, ForeignKey, Integer, String, Date

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
    active_until = Column(Date, nullable=True, default=MIN_DATETIME)


# TODO: R
class FunCog(Cog, name="Веселье"):
    def __init__(self, bot: Bot):
        super().__init__(bot, cls_config=FunConfig, emoji_icon='😂')

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
                    except Exception:
                        pass
                session.commit()
        await ctx.reply(embed=BotEmbed(ctx=ctx, description=f"Готово! Обновлено сообщений {count}"))

    @commands.command(name="слово", aliases=["word", "w", "бред"])
    @commands.cooldown(1, 0.1 * 60, type=commands.BucketType.guild)
    @commands.guild_only()
    async def _cmd_word(self, ctx: Context, word: str = None, level: int = 2):
        """
        Генератор бредовых предложений. Делает их из книги
        """

        async with ctx.typing():
            with db_session.create_session() as session:
                # noinspection PyShadowingBuiltins
                def format(line: str):
                    if not line or not set(filter(lambda x: x.isalnum(), set(line))) or not line.strip()[0].isalnum():
                        return ""
                    # symbols = set(filter(lambda x: not x.isalnum(), set(line)))
                    symbols = ".,;?!-"
                    for symbol in symbols:
                        line = line.replace(symbol, ' ' + symbol + ' ')
                    line = line.replace('  ', ' ').strip()
                    return line.lower()

                all_messages = session.query(Message).filter(Message.content != "", Message.has_mentions == False,
                                                             Message.has_mentions_roles == False,
                                                             Message.has_mentions_everyone == False).all()
                await asyncio.sleep(0.0001)
                all_sentences = list(map(format, filter(bool, map(lambda x: x.content, all_messages))))
                await asyncio.sleep(0.0001)
                sentences = []
                for sentence in all_sentences:
                    sentences += sentence.split()
            await asyncio.sleep(0.0001)
            words = swift.words + sentences

            if level < 2:
                level = 2
            sentence = []
            word = random.choice(words) if word not in words else word
            sentence.append(word)
            for n in range(1, level):
                indexes = [i for i in range(n, len(words)) if
                           all(map(lambda x: sentence[-(x + 1)] == words[i - (x + 1)], range(n)))]

                word = "."
                for i in range(len(indexes)):
                    try:
                        word = words[random.choice(indexes)]
                    except IndexError:
                        if i != len(indexes):
                            break
                sentence += [word]
                if word == '.':
                    break
            while word != '.' and sum(map(len, sentence)) <= 1900:
                indexes = [i for i in range(level - 1, len(words)) if all(map(lambda x: sentence[-x] == words[i - x],
                                                                              range(1, level)))]
                word = words[random.choice(indexes)]
                sentence += [word]

            await ctx.send(' '.join(sentence))

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
        await ctx.reply(embed=BotEmbed(ctx=ctx, title=f"Сапёр {width}x{height} с {count} бомбами", description=map_sapper))


def setup(bot: Bot):
    bot.add_cog(FunCog(bot))
