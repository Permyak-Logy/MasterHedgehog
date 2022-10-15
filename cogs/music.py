import asyncio

import discord
import sqlalchemy
import youtube_dl
from discord.ext import commands

from PLyBot import Bot, Cog, Context, BotEmbed
from db_session import SqlAlchemyBase, BaseConfigMix


class YTDLSource(discord.PCMVolumeTransformer):
    # noinspection SpellCheckingInspection
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
        self.thumbnail = data.get('thumbnail')
        self.channel = data.get('channel')
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


class MusicConfig(SqlAlchemyBase, BaseConfigMix):
    __tablename__ = "music_configs"

    guild_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('guilds.id'),
                                 primary_key=True, nullable=False)
    access = sqlalchemy.Column(sqlalchemy.String, nullable=False, default='{}')
    active_until = sqlalchemy.Column(sqlalchemy.Date, nullable=True, default=None)


# TODO: Сделать через discord_components
class MusicCog(Cog, name='Музыка YouTube'):
    # TODO: Сделать обновление плейера при завершении игры музыки

    def __init__(self, bot: Bot):
        super().__init__(bot, cls_config=MusicConfig, emoji_icon='🎧')
        self.__online_music_players = {}

    @commands.group(name='музыка', aliases=['music'])
    @commands.guild_only()
    async def _group_music(self, ctx: Context):
        """Команды для управления музыкой"""
        await ctx.just_send_help()

    @_group_music.command('сюда', aliases=['join'])
    @commands.guild_only()
    async def _cmd_music_join(self, ctx: Context, *, channel: discord.VoiceChannel = None):
        """Присоединяется к голосовому каналу"""
        assert channel, "Не указан голосовой канал для присоединения"
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()

    @_group_music.command(name='играть', aliases=['play'])
    @commands.guild_only()
    async def _cmd_music_play(self, ctx: Context, *, url: str):
        """Воспроизводит музыку по указанной ссылке или названию"""

        if ctx.voice_client is None:
            assert ctx.author.voice, "Author not connected to a voice channel."
            await ctx.author.voice.channel.connect()

        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

        emb = BotEmbed(ctx=ctx,
                       title='Муз плейер',
                       description=f'**Играет:** {player.title}',
                       colour=self.bot.colour
                       )
        emb.add_field(
            name='Статус', value='🟢 Играет').add_field(
            name="Громкость", value=str(round(ctx.voice_client.source.volume * 100)) + "%")
        emb.set_thumbnail(url=player.thumbnail)
        emb.set_footer()
        msg: discord.Message = await ctx.send(embed=emb)

        await msg.add_reaction('⏯️')
        await msg.add_reaction('⏹️')
        await msg.add_reaction('🔉')
        await msg.add_reaction('🔊')
        self.__online_music_players[ctx.guild.id] = msg.id

    @_group_music.command(name='громкость', aliases=['volume'])
    @commands.guild_only()
    async def _cmd_music_volume(self, ctx: Context, volume: int):
        """Изменяет уровень громкости"""

        if ctx.voice_client is None:
            return await ctx.reply("Я не сижу сейчас в голосовом канале")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Изменена громкость на {volume}%")

    @_group_music.command(name='стоп', aliases=['stop'])
    @commands.guild_only()
    async def _cmd_music_stop(self, ctx: Context):
        """Останавливает музыку и выходит из канала"""
        assert ctx.voice_client, "Я не сижу щас в голосовом канале"
        if ctx.voice_client:
            await ctx.voice_client.disconnect()

    @commands.Cog.listener('on_raw_reaction_add')
    async def _listener_using_music_player(self, payload: discord.RawReactionActionEvent):
        if self.__online_music_players.get(payload.guild_id) != payload.message_id:
            return

        try:
            msg: discord.Message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        except (discord.NotFound, AttributeError):
            return

        if payload.member.bot:
            return
        await msg.remove_reaction(payload.emoji, payload.member)

        voice_client: discord.VoiceClient = msg.guild.voice_client
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            if payload.emoji.name == '⏯️':
                if voice_client.is_paused():
                    voice_client.resume()
                else:
                    voice_client.pause()
            elif payload.emoji.name == '⏹️':
                voice_client.stop()
            elif payload.emoji.name == '🔉':
                voice_client.source.volume = max(0., voice_client.source.volume - 0.1)
            elif payload.emoji.name == '🔊':
                voice_client.source.volume = min(1., voice_client.source.volume + 0.1)
            else:
                return

        await self.update_status_music_player(msg)

    async def update_status_music_player(self, message: discord.Message):
        voice_client: discord.VoiceClient = message.guild.voice_client
        embed = message.embeds[0]
        embed.clear_fields()
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            embed.add_field(name='Статус', value=(
                '🟢 Играет' if not voice_client.is_paused() else '🟠 Пауза'))
            embed.add_field(name="Громкость", value=str(round(voice_client.source.volume * 100)) + "%")
        else:
            embed.add_field(name='Статус', value='🔴 Кончилась')
            embed.add_field(name="Громкость", value='---')
            del self.__online_music_players[message.guild.id]

        await message.edit(embed=embed)


async def setup(bot: Bot):
    await bot.add_cog(MusicCog(bot))
