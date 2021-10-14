import datetime
from typing import Iterable, List

import discord
import sqlalchemy
from sqlalchemy import orm

from db_session import SqlAlchemyBase
from db_session.const import MIN_DATETIME
from PLyBot.extra import cast_status_to_int
import db_session


class Member(SqlAlchemyBase):
    __tablename__ = 'members'

    id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'),
                           primary_key=True, nullable=False)
    guild_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('guilds.id'),
                                 primary_key=True, nullable=False)
    display_name = sqlalchemy.Column(sqlalchemy.String, nullable=False)

    joined_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)

    roles = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    status = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)

    last_activity = sqlalchemy.Column(sqlalchemy.DateTime, default=MIN_DATETIME)

    joined = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=True)

    guild = orm.relation('Guild')
    user = orm.relation('User')

    def __repr__(self):
        return f"Member(id={self.id} guild={self.guild} balance={self.get_balance()})"

    def __str__(self):
        return repr(self)

    def get_roles(self, bot: discord.Client) -> List[discord.Role]:
        guild: discord.Guild = bot.get_guild(self.guild_id)
        if guild is None:
            return []
        roles = self.roles
        return list(filter(bool, map(guild.get_role, map(int, (roles or "").split(";")))))

    def set_roles(self, roles: list):
        if roles:
            self.roles = ";".join(map(str, map(lambda r: r.id, roles)))
        else:
            self.roles = None

    @staticmethod
    def get(session: db_session.Session, member: discord.Member):
        return session.query(Member).filter(Member.id == member.id, Member.guild_id == member.guild.id).first()

    @staticmethod
    def insert(session: db_session.Session, member: discord.Member):
        if Member.get(session, member):
            raise ValueError("Участник уже есть в базе")
        m = Member()
        m.id = member.id
        m.guild_id = member.guild.id
        m.display_name = member.display_name
        m.joined_at = member.joined_at
        m.set_roles(member.roles)
        m.status = cast_status_to_int(member.status)
        m.joined = True
        session.add(m)
        return m

    @staticmethod
    def update(session: db_session.Session, member: discord.Member):
        m = Member.get(session, member)
        if not m:
            m = Member.insert(session, member)
        else:
            m.name = str(member)
            m.bot = member.bot
            m.guild_name = member.guild.name
            m.display_name = member.display_name
            m.created_at = member.created_at
            m.joined_at = member.joined_at
            m.status = cast_status_to_int(member.status)
            m.set_roles(member.roles)
            m.joined = True
        return m

    @staticmethod
    def delete(session: db_session.Session, member: discord.Member):
        m = Member.get(session, member)
        if not m:
            raise ValueError("Такого участника нет в базе")
        session.delete(m)
        return m

    @staticmethod
    def update_all(session: db_session.Session, members: Iterable[discord.Member]):
        ids = set((member.id, member.guild.id) for member in members)
        for member_data in Member.get_all(session):
            if (member_data.id, member_data.guild_id) not in ids:
                session.delete(member_data)

        for member in members:
            Member.update(session, member)