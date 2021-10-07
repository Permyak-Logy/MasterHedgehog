from typing import Iterable

import discord

from db_session import SqlAlchemyBase, Session, ExtraTools
import sqlalchemy


class Message(SqlAlchemyBase, ExtraTools):
    __tablename__ = "messages"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)

    author = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), nullable=False)
    channel = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('channels.id'))

    content = sqlalchemy.Column(sqlalchemy.String, nullable=False)

    has_mentions = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=False)
    has_mentions_roles = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=False)
    has_mentions_everyone = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=False)

    created_at = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)

    @staticmethod
    def update_all(session: Session, messages: Iterable[discord.Message]):
        ids = set(message.id for message in messages)
        for msg_data in Message.get_all(session):
            if msg_data.id not in ids:
                # TODO: Очистка участников, ролей и каналов гильдии
                session.delete(msg_data)

        for msg in messages:
            Message.update(session, msg)

    @staticmethod
    def get(session: Session, msg: discord.Message):
        return session.query(Message).filter(msg.id == msg.id).first()

    @staticmethod
    def add(session: Session, message: discord.Message):
        if Message.get(session, message):
            raise ValueError("Такое сообщение уже есть")
        msg_data = Message()
        msg_data.id = message.id
        if message.guild:
            msg_data.guild = message.guild.id
        msg_data.author = message.author.id
        msg_data.channel = message.channel.id
        msg_data.content = message.content
        msg_data.has_mentions = bool(message.mentions)
        msg_data.has_mentions_roles = bool(message.role_mentions)
        msg_data.has_mentions_everyone = bool(message.mention_everyone)
        msg_data.timestamp = message.created_at.timestamp()
        session.add(msg_data)
        return msg_data

    @staticmethod
    def update(session: Session, message: discord.Message):
        msg_data = Message.get(session, message)
        if not msg_data:
            msg_data = Message.add(session, message)
        else:
            msg_data.id = message.id
            if message.guild:
                msg_data.guild = message.guild.id
            msg_data.author = message.author.id
            msg_data.channel = message.channel.id
            msg_data.content = message.content
            msg_data.has_mentions = bool(message.mentions)
            msg_data.has_mentions_roles = bool(message.role_mentions)
            msg_data.has_mentions_everyone = bool(message.mention_everyone)
            msg_data.timestamp = message.created_at.timestamp()
        return msg_data

    @staticmethod
    def delete(session: Session, message: discord.Message):
        msg_data = Message.get(session, message)
        if not msg_data:
            raise ValueError("Такого сообщения нет в базе")
        session.delete(msg_data)
        return msg_data
