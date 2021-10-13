import discord
import sqlalchemy

import db_session
from db_session import SqlAlchemyBase


class Message(SqlAlchemyBase):
    __tablename__ = "messages"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)

    guild = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('guilds.id'))
    author = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('members.id'), nullable=False)
    channel = sqlalchemy.Column(sqlalchemy.Integer)

    content = sqlalchemy.Column(sqlalchemy.String, nullable=False)

    has_mentions = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=False)
    has_mentions_roles = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=False)
    has_mentions_everyone = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=False)

    timestamp = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)

    @staticmethod
    def get(session: db_session.Session, message: discord.Message):
        return session.query(Message).filter(Message.id == message.id).first()

    @staticmethod
    def insert(session: db_session.Session, message: discord.Message):
        if Message.get(session, message):
            raise ValueError("Такое сообщение уже есть")
        msg = Message()
        msg.id = message.id
        if message.guild:
            msg.guild = message.guild.id
        msg.author = message.author.id
        msg.channel = message.channel.id
        msg.content = message.content
        msg.has_mentions = bool(message.mentions)
        msg.has_mentions_roles = bool(message.role_mentions)
        msg.has_mentions_everyone = bool(message.mention_everyone)
        msg.timestamp = message.created_at.timestamp()

        session.add(msg)
        return msg

    @staticmethod
    def update(session: db_session.Session, message: discord.Message):
        msg = Message.get(session, message)
        if not msg:
            msg = Message.insert(session, message)
        else:
            msg.id = message.id
            if message.guild:
                msg.guild = message.guild.id
            msg.author = message.author.id
            msg.channel = message.channel.id
            msg.content = message.content
            msg.has_mentions = bool(message.mentions)
            msg.has_mentions_roles = bool(message.role_mentions)
            msg.has_mentions_everyone = bool(message.mention_everyone)
            msg.timestamp = message.created_at.timestamp()
        return msg

    @staticmethod
    def delete(session: db_session.Session, message: discord.Message):
        m = Message.get(session, message)
        if not m:
            raise ValueError("Такого сообщения нет в базе")
        session.delete(m)
        return m
