import asyncio
import os
import re
from random import choice

import discord
from discord import VoiceClient
from discord.ext import commands
from discord.utils import get
from youtube_dl import YoutubeDL

from PLyBot import Bot, Cog, plug_func, Context

# noinspection SpellCheckingInspection
CONVERSATION_DATA = {
    r'(\b([бb][лl](я|(y?a))?((ть)|t)?)|(сука?)\b)|(хуй)|(дрочит)|(трах)': [
        'audio\\bolshe_syuda_ne_pishi-namobilu.com.mp3',
        'audio\\muzhik_ty_kto-namobilu.com.mp3',
        'audio\\oj_kak_vse_yeto_neprilichno-namobilu.com.mp3',
        'audio\\rebyat_otstante_ot_menya_na_2_nedeli-namobilu.com.mp3'],
    r'(поб)|(выигр)': ['audio\\yeto_prosto_ofigenno-namobilu.com.mp3'],
    r'раб': ['audio\\ya_uzhe_nedelyu_na_rabotu_xozhu-namobilu.com.mp3'],
    r'\bлюб(лю)|(ит)\b': ['audio\\pust_rastaet_v_serdce_ldinka_poluchi_moj_valentinka-namobilu.com.mp3'],
    r'\bкто\b': ['audio\\prostokvashino_kto_tam-namobilu.com.mp3'],
    r'\bпотерялся\b': ['audio\\pochemu_tak_chasto_propadaesh-namobilu.com.mp3'],
    r'\bпоня(л)|(тно)\b': ['audio\\nichego_ne_ponyal_no_ochen_interesno-namobilu.com.mp3'],
    r'\b(мур)\b': ['audio\\mur_mur_glamur-namobilu.com.mp3'],
    r'\b(крыса)\b': ['audio\\lya_ty_krysa-namobilu.com.mp3'],
    r'\b(расскажи о себе [её]жа)\b': ['audio\\нет мозга - scanca.net.mp3', 'audio\\немного о себе - scanca.net.mp3',
                                      'audio\\ya_chechenec_menya_zvat_alan-namobilu.com.mp3'],
    r'\b(привет)|(з?дарова?)\b': ['audio\\uaau_privet_chuvak-namobilu.com.mp3']
}

# noinspection SpellCheckingInspection
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'default_search': 'ytsearch'
}


# TODO: Сделать воспроизведение по кодовому слову

# TODO: УСТАРЕЛ класс музыки
class OldMusicCog(Cog, name='Музыка'):
    def __init__(self, bot: Bot):
        super(OldMusicCog, self).__init__(bot)
        self.turn_music = {}

    @commands.Cog.listener('on_message')
    async def on_message(self, message: discord.Message):
        if not self.bot.is_ready():
            return
        if not isinstance(message.guild, discord.Guild):
            return
        if not await self.cog_check(await self.bot.get_context(message)):
            return

        for regex, phrases in CONVERSATION_DATA.items():
            if message.content and re.search(regex, message.content.lower()):
                voice: VoiceClient = message.guild.voice_client
                if (not voice or not voice.is_connected()) and isinstance(message.author, discord.Member):
                    author: discord.Member = message.author
                    author_voice = author.voice
                    if isinstance(author_voice, discord.VoiceState) and (author_voice.channel is not None):
                        voice = await author_voice.channel.connect()

                        await self.start_play(voice, choice(phrases))

                        if voice.is_connected():
                            await voice.disconnect()
                return

    @staticmethod
    async def start_play(voice: VoiceClient, url):
        if voice.is_playing() or voice.is_paused():
            voice.stop()
        voice.play(discord.FFmpegPCMAudio(url))
        while voice.is_playing() or voice.is_connected():
            await asyncio.sleep(1)

    @commands.command()
    @commands.guild_only()
    async def play(self, ctx: commands.Context, *, search: str):
        if not ctx.guild.voice_client:
            voice = await ctx.author.voice.channel.connect()
        else:
            voice: discord.VoiceClient = get(self.bot.voice_clients, guild=ctx.guild)

        ydl_options = YDL_OPTIONS.copy()
        ydl_options['outtmpl'] = f'audio\\yt_song{ctx.guild.id}.mp3'

        if os.path.isfile(ydl_options['outtmpl']):
            os.remove(ydl_options['outtmpl'])

        await ctx.send('Подготовка музыки. Подождите', delete_after=10)

        with YoutubeDL(ydl_options) as ydl:
            info = ydl.extract_info(search if not isinstance(search, str) else search, download=True)

        # noinspection PyUnusedLocal
        url = info['entries'][0]['formats'][0]['url']
        await ctx.send(embed=discord.Embed(description=f'Играет: {info["entries"][0]["title"]}'))

        await self.start_play(voice, ydl_options['outtmpl'])

        if voice.is_connected():
            await voice.disconnect()

        if os.path.isfile(ydl_options['outtmpl']):
            try:
                os.remove(ydl_options['outtmpl'])
            except PermissionError as E:
                print(E)

    @commands.command()
    @commands.guild_only()
    async def play_gamers_dialog(self, ctx: commands.Context):
        await self.play(ctx, url="https://www.youtube.com/watch?v=2IIPwlhuVSE&ab_channel=TheNafig")

    @commands.command()
    @commands.guild_only()
    async def stop(self, ctx: commands.Context):
        voice: discord.VoiceClient = get(self.bot.voice_clients, guild=ctx.guild)
        assert voice.is_playing() or voice.is_paused(), "Сейчас ничего не играет"
        voice.stop()
        await ctx.send(embed=discord.Embed(description='Музыка остановлена'))


class MusicCog(Cog, name='Музыка'):
    def __init__(self, bot: Bot):
        super().__init__(bot)
        self.sessions = {}
        # sessions = { guild_id-int: {"channel": int, "ctrl_msg": msg_id-int, "isPlaying": bool, "stream": obj,
        # "tmp": {"search": [ ...results_of_search... ]}}

    @staticmethod
    async def start_play(voice: VoiceClient, url):
        if voice.is_playing() or voice.is_paused():
            voice.stop()
        voice.play(discord.FFmpegPCMAudio(url))
        while voice.is_playing() or voice.is_connected():
            await asyncio.sleep(1)

    async def clearer(self):
        # Цикл который каждый тик очищает старые сообщения с поиском
        pass

    @commands.command()
    async def music_on(self, ctx: Context):
        if not ctx.guild.voice_client:
            voice = await ctx.author.voice.channel.connect()
        else:
            voice: discord.VoiceClient = get(self.bot.voice_clients, guild=ctx.guild)
            await voice.disconnect()
            voice = await ctx.author.voice.channel.connect()
        await ctx.reply(embed=discord.Embed(title="Успешно", description=f"Я подключился к каналу {voice.channel}"))

    @commands.command()
    async def music_off(self, ctx: Context):
        # Остановка музыки и уход из канала
        if ctx.guild.voice_client:
            voice: discord.VoiceClient = get(self.bot.voice_clients, guild=ctx.guild)
            await voice.disconnect()
        await ctx.reply(embed=discord.Embed(title="Успешно", description="Я покидаю вас..."))

    @commands.command()
    async def music_search(self, ctx: Context, *, search):
        # Поиск музыки в интернете (и её запуск если был
        ydl_options = YDL_OPTIONS.copy()
        ydl_options['outtmpl'] = f'audio\\yt_song{ctx.guild.id}.mp3'
        with YoutubeDL(ydl_options) as ydl:
            info = ydl.extract_info(search if not isinstance(search, str) else search, download=True)

        # noinspection PyUnusedLocal
        url = info['entries'][0]['formats'][0]['url']
        await ctx.send(embed=discord.Embed(description=f'Играет: {info["entries"][0]["title"]}'))
        await self.start_play(get(self.bot.voice_clients, guild=ctx.guild), ydl_options['outtmpl'])

    async def on_raw_reaction_add(self):
        # Включение по реакции и просто управление музыкой
        pass


@plug_func()
def setup(bot: Bot):
    bot.add_cog(MusicCog(bot))

# TODO: нейросеть в чате https://bots.server-discord.com/656962312565030963
# TODO: Ссылка приглашение
