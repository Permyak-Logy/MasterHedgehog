from typing import Iterable

import discord
from sqlalchemy import orm
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean
import db_session
from db_session import SqlAlchemyBase


class Guild(SqlAlchemyBase):
    __tablename__ = 'guilds'

    id = Column(Integer, primary_key=True, nullable=False)
    owner = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String, nullable=False)

    ban_activity = Column(Boolean, default=False)
    command_prefix = Column(String, nullable=True, default=None)

    language_cmd = Column(String, default="ru")
    language_text = Column(String, default="ru")
    timezone = Column(String, default="Europe/Moscow")
    system_color = Column(String, default="#8A3B03")

    members = orm.relation("Member", back_populates='guild')

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"

    def __str__(self):
        return repr(self)

    @staticmethod
    def get(session: db_session.Session, guild: discord.Guild):
        return session.query(Guild).filter(Guild.id == guild.id).first()

    @staticmethod
    def insert(session: db_session.Session, guild: discord.Guild):
        if Guild.get(session, guild):
            raise ValueError("Такой сервер уже есть")
        g = Guild()
        g.id = guild.id
        g.owner = guild.owner_id
        g.name = guild.name
        session.add(g)
        return g

    @staticmethod
    def update(session: db_session.Session, guild: discord.Guild):
        g = Guild.get(session, guild)
        if not g:
            g = Guild.insert(session, guild)
        else:
            g.id = guild.id
            g.name = guild.name
            g.owner = guild.owner_id
        return g

    @staticmethod
    def delete(session: db_session.Session, guild: discord.Guild):
        g = Guild.get(session, guild)
        if not g:
            raise ValueError("Такого сервера нет в базе")
        session.delete(g)
        return g

    @staticmethod
    def update_all(session: db_session.Session, guilds: Iterable[discord.Guild]):
        for guild in guilds:
            Guild.update(session, guild)
