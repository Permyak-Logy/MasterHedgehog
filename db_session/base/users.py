import datetime
from typing import Iterable
from typing import Union

import discord
import sqlalchemy
from sqlalchemy import orm

import db_session
from db_session import SqlAlchemyBase


class User(SqlAlchemyBase):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, nullable=False)
    nick = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    bot = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False)
    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)
    member = orm.relation('Member', back_populates='user')

    def __repr__(self):
        return f"User(id={self.id} bot={self.bot})"

    def __str__(self):
        return repr(self)

    @staticmethod
    def get(session: db_session.Session, user: Union[discord.User, discord.Member]):
        return session.query(User).filter(User.id == user.id).first()

    @staticmethod
    def insert(session: db_session.Session, user: Union[discord.User, discord.Member]):
        if User.get(session, user):
            raise ValueError("Участник уже в базе")
        u = User()
        u.id = user.id
        u.nick = str(user)
        u.bot = user.bot
        u.created_at = user.created_at
        session.add(u)
        return u

    @staticmethod
    def update(session: db_session.Session, user: Union[discord.User, discord.Member]):
        u = User.get(session, user)
        if not u:
            u = User.insert(session, user)
        else:
            u.id = user.id
            u.nick = str(user)
            u.bot = user.bot
            u.created_at = user.created_at
        return u

    @staticmethod
    def delete(session: db_session.Session, user: Union[discord.User, discord.Member]):
        u = User.get(session, user)
        if not u:
            raise ValueError("Такого участника нет в базе")
        session.delete(u)
        return u

    @staticmethod
    def update_all(session: db_session.Session, users: Iterable[discord.User]):
        for user in users:
            User.update(session, user)
