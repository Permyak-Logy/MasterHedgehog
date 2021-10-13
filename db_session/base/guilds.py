from db_session import SqlAlchemyBase
import sqlalchemy
from sqlalchemy import orm
import db_session
import discord


class Guild(SqlAlchemyBase):
    __tablename__ = 'guilds'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, nullable=False)
    owner = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), nullable=False)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=False)

    ban_activity = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
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
