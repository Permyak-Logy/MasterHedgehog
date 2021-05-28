from typing import Union, Iterable

import discord

from db_session import SqlAlchemyBase, Session, ExtraTools
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime

ChannelType = Union[
        discord.TextChannel, discord.VoiceChannel, discord.DMChannel, discord.GroupChannel, discord.StoreChannel]


class Channel(SqlAlchemyBase, ExtraTools):
    __tablename__ = 'channels'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    type = Column(Integer)
    created_at = Column(DateTime)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # Для DMChannel

    owner_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # Для GroupChannel

    # Для остальных
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    guild_id = Column(Integer, ForeignKey('guilds.id'), nullable=True)

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id} name='{self.name}')"

    @staticmethod
    def update_all(session: Session, channels: Iterable[ChannelType]):
        ids = set(channel.id for channel in channels)
        for channel_data in Channel.get_all(session):
            if channel_data.id not in ids:
                session.delete(channel_data)

        for channel in channels:
            Channel.update(session, channel)

    @staticmethod
    def get(session: Session, channel: ChannelType):
        return session.query(Channel).filter(Channel.id == channel.id, Channel.guild_id == channel.guild.id).first()

    @staticmethod
    def add(session: Session, channel: ChannelType):
        if Channel.get(session, channel):
            raise ValueError("Участник уже есть в базе")

        channel_data = Channel()
        channel_data.name = channel.name
        channel_data.type = channel.type

        channel_data.user_id = None
        channel_data.owner_id = None
        channel_data.category_id = None
        channel_data.guild_id = None

        if isinstance(channel, discord.DMChannel):
            channel_data.user_id = channel.recipient.id
        elif isinstance(channel, discord.GroupChannel):
            channel_data.owner_id = channel.owner.id
        else:
            channel_data.category_id = channel.category_id
            channel_data.guild_id = channel.guild.id
            channel_data.created_at = channel.created_at

        session.add(channel_data)
        return channel_data

    @staticmethod
    def update(session: Session, channel: ChannelType):
        channel_data = Channel.get(session, channel)
        if not channel_data:
            channel_data = Channel.add(session, channel)
        else:
            channel_data.name = channel.name
            channel_data.type = channel.type

            channel_data.user_id = None
            channel_data.owner_id = None
            channel_data.category_id = None
            channel_data.guild_id = None

            if isinstance(channel, discord.DMChannel):
                channel_data.user_id = channel.recipient.id
            elif isinstance(channel, discord.GroupChannel):
                channel_data.owner_id = channel.owner.id
            else:
                channel_data.category_id = channel.category_id
                channel_data.guild_id = channel.guild.id
        return channel_data

    @staticmethod
    def delete(session: Session, channel: ChannelType):
        channel_data = Channel.get(session, channel)
        if not channel_data:
            raise ValueError("Такого участника нет в базе")
        session.delete(channel_data)
        return channel_data
