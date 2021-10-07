import datetime
from typing import Iterable, Union

import discord
import sqlalchemy
from sqlalchemy import orm

from db_session import SqlAlchemyBase, Session, ExtraTools


class User(SqlAlchemyBase, ExtraTools):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, nullable=False)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    discriminator = sqlalchemy.Column(sqlalchemy.String, nullable=False)

    bot = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False)
    created_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)
    member = orm.relation('Member', back_populates='user')

    def __repr__(self):
        return f"User(id={self.id} bot={self.bot})"

    def __str__(self):
        return repr(self)

    @staticmethod
    def update_all(session: Session, users: Iterable[discord.User]):
        ids = set(user.id for user in users)
        for user_data in User.get_all(session):
            if user_data.id not in ids:
                session.delete(user_data)

        for user in users:
            User.update(session, user)

    @staticmethod
    def get(session: Session, user: Union[discord.User, discord.Member]):
        return session.query(User).filter(User.id == user.id).first()

    @staticmethod
    def add(session: Session, user: Union[discord.User, discord.Member]):
        if User.get(session, user):
            raise ValueError("Участник уже в базе")
        user_data = User()
        user_data.id = user.id
        user_data.name = user.name
        user_data.discriminator = user.discriminator
        user_data.bot = user.bot
        user_data.created_at = user.created_at
        session.add(user_data)
        return user_data

    @staticmethod
    def update(session: Session, user: Union[discord.User, discord.Member]):
        user_data = User.get(session, user)
        if not user_data:
            user_data = User.add(session, user)
        else:
            user_data.id = user.id
            user_data.name = user.name
            user_data.discriminator = user.discriminator
            user_data.bot = user.bot
            user_data.created_at = user.created_at
        return user_data

    @staticmethod
    def delete(session: Session, user: Union[discord.User, discord.Member]):
        user_data = User.get(session, user)
        if not user_data:
            raise ValueError("Такого участника нет в базе")
        session.delete(user_data)
        return user_data
