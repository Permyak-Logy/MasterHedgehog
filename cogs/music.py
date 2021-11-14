import asyncio

import discord
import youtube_dl

from discord.ext import commands
from discord.utils import get

from PLyBot import Bot, Cog, Context


class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_FORMAT_OPTIONS = {
        'format': 'bestaudio/best',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
    }
    FFMPEG_OPTIONS = {
        'options': '-vn'
    }

    # Suppress noise about console usage from errors
    youtube_dl.utils.bug_reports_message = lambda: ''

    ytdl = youtube_dl.YoutubeDL(YTDL_FORMAT_OPTIONS)

    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: cls.ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else YTDLSource.ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **cls.FFMPEG_OPTIONS), data=data)


class MusicCog(Cog):
    # TODO: Сделать обновление плейера при завершении игры музыки

    def __init__(self, bot: Bot):
        super().__init__(bot)
        self.__online_music_players = {}

    @commands.command()
    async def join(self, ctx: Context, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()

    @commands.command()
    async def play(self, ctx: Context, *, url):
        """Streams from a url (same as yt, but doesn't predownload)"""

        if ctx.voice_client is None:
            assert ctx.author.voice, "Author not connected to a voice channel."
            await ctx.author.voice.channel.connect()

        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

        msg: discord.Message = await ctx.send(embed=discord.Embed(
            title='Муз плейер',
            description=f'Играет: {player.title}').add_field(name='Статус', value='🟢 Играет'))

        await msg.add_reaction('⏯️')
        await msg.add_reaction('⏹️')
        self.__online_music_players[ctx.guild.id] = msg.id

    @commands.command()
    async def volume(self, ctx: Context, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")

    @commands.command()
    async def stop(self, ctx: Context):
        """Stops and disconnects the bot from voice"""

        await ctx.voice_client.disconnect()

    @commands.Cog.listener('on_raw_reaction_add')
    async def on_using_player(self, payload: discord.RawReactionActionEvent):
        if self.__online_music_players.get(payload.guild_id) != payload.message_id:
            return

        try:
            msg: discord.Message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        except (discord.NotFound, AttributeError):
            return
        await msg.remove_reaction(payload.emoji, payload.member)
        if payload.member == self.bot.user:
            return

        voice_client: discord.VoiceClient = msg.guild.voice_client
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            if payload.emoji.name == '⏯️':
                if voice_client.is_paused():
                    voice_client.resume()
                else:
                    voice_client.pause()
            elif payload.emoji.name == '⏹️':
                voice_client.stop()
            else:
                return

        await self.update_status_player(msg)

    async def update_status_player(self, message: discord.Message):
        voice_client: discord.VoiceClient = message.guild.voice_client
        embed = message.embeds[0]
        embed.clear_fields()
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            embed.add_field(name='Статус', value=(
                '🟢 Играет' if not voice_client.is_paused() else '🟠 Пауза'))
        else:
            embed.add_field(name='Статус', value='🔴 Кончилась')
            del self.__online_music_players[message.guild.id]

        await message.edit(embed=embed)


def setup(bot: Bot):
    bot.add_cog(MusicCog(bot))
