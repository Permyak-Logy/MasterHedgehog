from typing import Optional, List
from typing import Union

import discord
import sqlalchemy
from discord.ext import commands
from flask import Blueprint, jsonify, request
from PLyBot.const import HeadersApi
import db_session
from PLyBot import Bot, get_any
from PLyBot import Cog
from PLyBot import BaseApiBP
from db_session import SqlAlchemyBase, BaseConfigMix, NONE, MIN_DATETIME


class PrivateChannelsConfig(SqlAlchemyBase, BaseConfigMix):
    __tablename__ = "private_channels_configs"

    guild_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('guilds.id'),
                                 primary_key=True, nullable=False)
    channels = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    access = sqlalchemy.Column(sqlalchemy.String, nullable=False, default='{}')
    active_until = sqlalchemy.Column(sqlalchemy.Date, nullable=True, default=MIN_DATETIME)

    def set_channels(self, *channels: discord.VoiceChannel):
        for channel in channels:
            if not isinstance(channel, discord.VoiceChannel):
                raise ValueError(f"Указываемый канал не VoiceChannel (got type '{type(channel)}')")

        if not channels:
            self.channels = None
        else:
            self.channels = ";".join(str(channel.id) for channel in channels)

    def get_channels(self, bot: Bot) -> List[discord.VoiceChannel]:
        if self.channels != NONE and self.channels:
            channels = self.channels
            ids = map(int, str(channels).split(';'))
            return list(filter(bool, map(bot.get_channel, ids)))
        return []


# TODO: У дани в Warframe не сделался канал Warframe а сделался Avoidman

class PrivateChannelsCog(Cog, name="Приватные каналы"):
    """
    Модуль приватных каналов. С ним вы сможете без труда создавать свои голосовыми каналы и
    управлять ими как админ.
    Предварительно не обходимо создать канал для их создания. (!!хелп set_pcc)

    Работа их очень проста. Вы заходите в голосовой канал, который был указан чуть раннее, он создаёт вашу
    личную берлогу и перемещает вас. Как только там никого не останется он очистится автоматом.
    **Внимание** следует сделать отдельную категорию для приватных каналов (Иначе все голосовые каналы, которые были в
    категории, будут очищаться)
    """

    def __init__(self, bot: Bot):
        super().__init__(bot, cls_config=PrivateChannelsConfig)
        self.bot.add_cog_blueprint(PrivateChannelsBP(self), url_prefix='/private_channels')

    def get_config(self, session: db_session.Session,
                   guild: Union[discord.Guild, int]) -> Optional[PrivateChannelsConfig]:
        return super().get_config(session, guild)

    @commands.command(name='привканал', aliases=['set_pcc', 'private_channel'])
    @commands.guild_only()
    async def _cmd_set_private_channel_creator(self, ctx: commands.Context, *channels: discord.VoiceChannel):
        """
        Устанавливает канал как канал который создаёт приватные каналы. Если ничего не указать то будет сброшен.
        """
        with db_session.create_session() as session:
            config = self.get_config(session, ctx.guild)
            config.set_channels(*channels)
            session.commit()
        chls_str = ", ".join(str(channel) for channel in channels)

        embed = discord.Embed(
            title="Успешно!",
            colour=self.bot.colour_embeds,
            description=f'Каналы "{chls_str}" установлен как канал для добавления приватных каналов'
        )

        await ctx.send(embed=embed)

    @commands.Cog.listener('on_voice_state_update')
    async def handle_private_channels(self, member: discord.Member, _, after: discord.VoiceClient):
        """
        Обработчик приватных каналов
        """
        if not self.bot.is_ready():
            return
        with db_session.create_session() as session:
            config = self.get_config(session, member.guild)
            channels_add = config.get_channels(self.bot)
            if not channels_add:
                return
            if not config.check_active_until():
                return
            categories = [channel.category for channel in channels_add]
            if after.channel in channels_add:
                name = get_any(member.activities, lambda x: x.type == discord.ActivityType.playing) or \
                       get_any(member.activities, lambda x: isinstance(x, discord.Game)) or member.display_name
                if isinstance(name, discord.Activity):
                    name = name.name
                channel = await after.channel.category.create_voice_channel(name=f"🔻 {name}", user_limit=5)
                try:
                    await channel.set_permissions(member, manage_roles=True,
                                                  manage_channels=True, mute_members=True,
                                                  deafen_members=True, move_members=True)
                    await member.move_to(channel)
                except (discord.errors.HTTPException, discord.errors.NotFound):
                    pass
            elif categories is not None:
                for category in categories:
                    for channel in category.voice_channels:
                        if not channel.members and channel not in channels_add:
                            try:
                                await channel.delete()
                            except discord.errors.NotFound:
                                pass


class PrivateChannelsBP(BaseApiBP):
    blueprint = Blueprint('private_channels_api', __name__)

    def __init__(self, cog):
        super(PrivateChannelsBP, self).__init__(cog)

    @staticmethod
    @blueprint.route('/channels', methods=['GET', 'POST'])
    def get_channels_bp():
        with db_session.create_session() as session:
            guild_id = request.headers[HeadersApi.GUILD_ID]
            api_key = request.headers['api-key']

            config = session.query(PrivateChannelsConfig).filter(
                PrivateChannelsConfig.guild_id == int(guild_id)).first()
            if not config:
                return jsonify(error="bad config-id")
            if request.method == 'GET':
                channels = config.channels
                return jsonify(ids=list(map(int, channels.split(';') if channels else [])))
            elif request.method == 'POST':
                return jsonify(status="ok post")


def setup(bot: Bot):
    bot.add_cog(PrivateChannelsCog(bot))
