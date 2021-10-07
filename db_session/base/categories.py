from typing import Iterable

import discord

from db_session import SqlAlchemyBase, Session
from sqlalchemy import Column, Integer, String, DateTime


class Category(SqlAlchemyBase):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, nullable=False)
    guild_id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String, nullable=False)

    created_at = Column(DateTime)

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id} name='{self.name}')"

    @staticmethod
    def update_all(session: Session, categories: Iterable[discord.CategoryChannel]):
        ids = set(category.id for category in categories)
        for channel_data in Category.get_all(session):
            if channel_data.id not in ids:
                session.delete(channel_data)

        for category in categories:
            Category.update(session, category)

    @staticmethod
    def get(session: Session, category: discord.CategoryChannel):
        return session.query(Category).filter(Category.id == category.id,
                                              Category.guild_id == category.guild.id).first()

    @staticmethod
    def add(session: Session, category: discord.CategoryChannel):
        if Category.get(session, category):
            raise ValueError("Участник уже есть в базе")

        channel_data = Category()
        channel_data.name = category.name
        channel_data.type = category.type

        channel_data.user_id = None
        channel_data.owner_id = None
        channel_data.category_id = None
        channel_data.guild_id = None

        if isinstance(category, discord.DMChannel):
            channel_data.user_id = category.recipient.id
        elif isinstance(category, discord.GroupChannel):
            channel_data.owner_id = category.owner.id
        else:
            channel_data.category_id = category.category_id
            channel_data.guild_id = category.guild.id
            channel_data.created_at = category.created_at

        session.add(channel_data)
        return channel_data

    @staticmethod
    def update(session: Session, category: discord.CategoryChannel):
        channel_data = Category.get(session, category)
        if not channel_data:
            channel_data = Category.add(session, category)
        else:
            channel_data.name = category.name
            channel_data.type = category.type

            channel_data.user_id = None
            channel_data.owner_id = None
            channel_data.category_id = None
            channel_data.guild_id = None

            if isinstance(category, discord.DMChannel):
                channel_data.user_id = category.recipient.id
            elif isinstance(category, discord.GroupChannel):
                channel_data.owner_id = category.owner.id
            else:
                channel_data.category_id = category.category_id
                channel_data.guild_id = category.guild.id
        return channel_data

    @staticmethod
    def delete(session: Session, category: discord.CategoryChannel):
        channel_data = Category.get(session, category)
        if not channel_data:
            raise ValueError("Такого участника нет в базе")
        session.delete(channel_data)
        return channel_data
