from typing import Iterable

import discord
from sqlalchemy import orm, Column, Integer, ForeignKey, String

from db_session import SqlAlchemyBase, Session, ExtraTools


class Guild(SqlAlchemyBase, ExtraTools):
    __tablename__ = 'guilds'

    id = Column(Integer, primary_key=True, nullable=False)

    name = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    mfa_level = Column(Integer, nullable=False)
    verification_level = Column(Integer, nullable=False)
    region = Column(String, nullable=False)
    icon = Column(String, nullable=False)

    afk_channel = Column(Integer, ForeignKey('channels.id'))

    default_role = Column(Integer, ForeignKey('roles.id'))

    members = orm.relation("Member", back_populates='guild')

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"

    def __str__(self):
        return repr(self)

    @staticmethod
    def update_all(session: Session, guilds: Iterable[discord.Guild]):
        ids = set(guild.id for guild in guilds)
        for guild_data in Guild.get_all(session):
            if guild_data.id not in ids:
                # TODO: Очистка участников, ролей и каналов гильдии
                session.delete(guild_data)

        for guild in guilds:
            Guild.update(session, guild)

    @staticmethod
    def get(session: Session, guild: discord.Guild):
        return session.query(Guild).filter(Guild.id == guild.id).first()

    @staticmethod
    def add(session: Session, guild: discord.Guild):
        if Guild.get(session, guild):
            raise ValueError("Такой сервер уже есть")

        guild_data = Guild()
        guild_data.id = guild.id
        guild_data.owner_id = guild.owner_id
        guild_data.name = guild.name
        guild_data.mfa_level = guild.mfa_level
        guild_data.verification_level = guild.verification_level
        guild_data.region = guild.region
        guild_data.icon = guild.icon
        guild_data.afk_channel = guild.afk_channel.id if guild.afk_channel else None
        guild_data.default_role = guild.default_role.id

        session.add(guild_data)
        return guild_data

    @staticmethod
    def update(session: Session, guild: discord.Guild):
        guild_data = Guild.get(session, guild)
        if not guild_data:
            guild_data = Guild.add(session, guild)
        else:
            guild_data.id = guild.id
            guild_data.owner_id = guild.owner_id
            guild_data.name = guild.name
            guild_data.mfa_level = guild.mfa_level
            guild_data.verification_level = guild.verification_level
            guild_data.region = guild.region
            guild_data.icon = guild.icon
            guild_data.afk_channel = guild.afk_channel.id if guild.afk_channel else None
            guild_data.default_role = guild.default_role.id

        return guild_data

    @staticmethod
    def delete(session: Session, guild: discord.Guild):
        guild = Guild.get_guild(session, guild)
        if not guild:
            raise ValueError("Такого сервера нет в базе")
        session.delete(guild)
        return guild
