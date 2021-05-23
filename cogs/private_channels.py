from typing import Optional, List
from typing import Union

import discord
import sqlalchemy
from discord.ext import commands

import db_session
from PLyBot import Bot, get_any
from PLyBot import Cog
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


class PrivateChannelsCog(Cog, name="Приватные каналы"):
    """
    Модуль приватных каналов. С ним вы сможете без труда создавать свои голосовыми каналы и
    управлять ими как админ.
    Предварительно не обходимо создать канал для их создания. (!!хелп set_pcc)

    Работа их очень проста. Вы заходите в голосовой канал, который был указан чуть раннее, он создаёт вашу
    личную берлогу и перемещает вас. Как только там никого не останется он очистется автоматом.
    **Внимание** следует сделать отдельную категорию для приватных каналов (Иначе все голосовые каналы, которые были в
    категории, будут очищаться)
    """

    def __init__(self, bot: Bot):
        super().__init__(bot, cls_config=PrivateChannelsConfig)

    def get_config(self, session: db_session.Session,
                   guild: Union[discord.Guild, int]) -> Optional[PrivateChannelsConfig]:
        return super().get_config(session, guild)

    @commands.command(name='привканал', aliases=['set_pcc', 'private_channel'])
    @commands.guild_only()
    async def set_private_channel_creator(self, ctx: commands.Context, *channels: discord.VoiceChannel):
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
                name = get_any(member.activities, lambda x: isinstance(x, discord.Game)) or member.display_name
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


def setup(bot: Bot):
    bot.add_cog(PrivateChannelsCog(bot))
