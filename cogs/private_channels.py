import asyncio
from typing import Optional, List
from typing import Union

import discord
import sqlalchemy
from discord.ext import commands
from discord_components import Select, SelectOption, Interaction
from flask import Blueprint, jsonify, request

import db_session
from PLyBot import BaseApiBP, JSON_STATUS, JsonParam
from PLyBot import Bot, Cog, Context, get_any, BotEmbed
from PLyBot.const import HeadersApi, Types
from db_session import SqlAlchemyBase, BaseConfigMix, NONE


class PrivateChannelsConfig(SqlAlchemyBase, BaseConfigMix):
    __tablename__ = "private_channels_configs"

    guild_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('guilds.id'),
                                 primary_key=True, nullable=False)
    channels = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    access = sqlalchemy.Column(sqlalchemy.String, nullable=False, default='{}')
    active_until = sqlalchemy.Column(sqlalchemy.Date, nullable=True, default=None)

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
        super().__init__(bot, cls_config=PrivateChannelsConfig, emoji_icon='🔑')
        self.bot.add_cog_blueprint(PrivateChannelsBP(self), url_prefix='/private_channels')

    def get_config(self, session: db_session.Session,
                   guild: Union[discord.Guild, int]) -> Optional[PrivateChannelsConfig]:
        return super().get_config(session, guild)

    @commands.command(name='привканал', aliases=['pcc', 'private_channel'])
    @commands.guild_only()
    async def _cmd_private_channel_creator(self, ctx: Context):
        """
        Отправляет сообщение для контроля приватных каналов
        """
        with db_session.create_session() as session:
            config = self.get_config(session, ctx.guild)
            old_channels = config.get_channels(self.bot)

        custom_id = f"_cmd_pcc:{ctx.message.id}"
        msg: discord.Message = await ctx.reply(
            embed=BotEmbed(ctx=ctx,
                           title="Настройка приватных каналов",
                           description="Выберите голосовые каналы, "
                                       "которые будут установлены "
                                       "как каналы для создания приватных голосовых каналов",
                           colour=self.bot.colour).set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url),
            components=[Select(
                placeholder="Выбери каналы!",
                options=[
                    SelectOption(label=channel.name,
                                 value=channel.id,
                                 emoji="🔊",
                                 description=f"id: {channel.id}" + (
                                     f" категория: {channel.category}" if channel.category else ""),
                                 default=channel in old_channels)
                    for channel in ctx.guild.voice_channels],
                min_values=0,
                max_values=len(ctx.guild.voice_channels),
                custom_id=custom_id)
            ])
        try:
            interaction: Interaction = await self.bot.wait_for(
                "select_option", check=lambda inter: inter.custom_id == custom_id and inter.user == ctx.author,
                timeout=5 * 60
            )
        except asyncio.TimeoutError:
            pass
        else:
            new_channels = list(map(ctx.guild.get_channel, map(int, interaction.values)))
            with db_session.create_session() as session:
                config = self.get_config(session, ctx.guild)
                config.set_channels(*new_channels)
                session.commit()

            embed = BotEmbed(ctx=ctx,
                             title="Успешно!",
                             colour=self.bot.colour,
                             description=(f'Установлены приватные каналы:\n' + "\n".join(
                                 f"\\🔊 {channel}" for channel in new_channels)
                                          if new_channels else "Убраны все голосовые каналы для создания приватных каналов")
                             )

            await interaction.send(embed=embed, ephemeral=True, delete_after=60)
        finally:
            await msg.delete()

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
                    if not category:
                        continue
                    for channel in category.voice_channels:
                        if not channel.members and channel not in channels_add:
                            try:
                                await channel.delete()
                            except discord.errors.NotFound:
                                pass


class PrivateChannelsBP(BaseApiBP):
    blueprint = Blueprint('private_channels_api', __name__)

    CHANNELS_P = JsonParam(
            dtype=Types.voice_channel,
            about=None,
            islist=True)

    def __init__(self, cog: PrivateChannelsCog):
        super(PrivateChannelsBP, self).__init__(cog)

    @staticmethod
    @blueprint.route('/channels', methods=['GET', 'POST'])
    def get_channels_bp():
        with db_session.create_session() as session:
            guild_id = int(request.headers[HeadersApi.GUILD_ID])

            config = PrivateChannelsCog.cog.get_config(session, guild_id)

            if request.method == 'GET':
                channels = config.channels
                return PrivateChannelsBP.CHANNELS_P.make(list(map(int, channels.split(';') if channels else [])))

            elif request.method == 'POST':
                try:
                    channels: List[discord.VoiceChannel] = PrivateChannelsBP.CHANNELS_P.get(request.json)
                except ValueError:
                    return JSON_STATUS(400)
                else:
                    config.set_channels(*channels)
                    session.commit()
                    return JSON_STATUS(202)
        return JSON_STATUS(400)


def setup(bot: Bot):
    bot.add_cog(PrivateChannelsCog(bot))
