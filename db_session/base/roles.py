from db_session import SqlAlchemyBase, Session, ExtraTools
from sqlalchemy import Integer, String, ForeignKey, Column, DateTime
from typing import Iterable
import discord


class Role(SqlAlchemyBase, ExtraTools):
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, ForeignKey('guilds.id'))
    name = Column(String)
    created_at = Column(DateTime, nullable=False)

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id} name='{self.name}')"

    @staticmethod
    def update_all(session: Session, roles: Iterable[discord.Role]):
        ids = set(role.id for role in roles)
        for role_data in Role.get_all(session):
            if role_data.id not in ids:
                session.delete(role_data)

        for role in roles:
            Role.update(session, role)

    @staticmethod
    def get(session: Session, role: discord.Role):
        return session.query(Role).filter(Role.id == role.id, Role.guild_id == role.guild.id).first()

    @staticmethod
    def add(session: Session, role: discord.Role):
        if Role.get(session, role):
            raise ValueError("Участник уже есть в базе")

        role_data = Role()
        role_data.guild_id = role.guild.id
        role_data.name = role.name
        role_data.created_at = role.created_at

        session.add(role_data)
        return role_data

    @staticmethod
    def update(session: Session, role: discord.Role):
        role_data = Role.get(session, role)
        if not role_data:
            role_data = Role.add(session, role)
        else:
            role_data.guild_id = role.guild.id
            role_data.name = role.name
            role_data.created_at = role.created_at
        return role_data

    @staticmethod
    def delete(session: Session, role: discord.Role):
        role_data = Role.get(session, role)
        if not role_data:
            raise ValueError("Такого участника нет в базе")
        session.delete(role_data)
        return role_data
