import datetime
from typing import Iterable

import discord
from sqlalchemy import orm, Column, Integer, String, DateTime, ForeignKey

from db_session import SqlAlchemyBase, Session, ExtraTools
from db_session.const import MIN_DATETIME


class Member(SqlAlchemyBase, ExtraTools):
    __tablename__ = 'members'
    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    guild_id = Column(Integer, ForeignKey('guilds.id'), nullable=False)
    display_name = Column(String, nullable=False)

    joined_at = Column(DateTime, default=datetime.datetime.now, nullable=False)
    
    desktop_status = Column(String)
    mobile_status = Column(String)
    web_status = Column(String)

    last_activity = Column(DateTime, default=MIN_DATETIME)

    guild = orm.relation('Guild')
    user = orm.relation('User')

    # feature = orm.relationship("FeatureMember", uselist=False, back_populates="member")
    # balance = orm.relationship("Balance", uselist=False, back_populates="member")

    def __repr__(self):
        return f"Member(id={self.id} guild={self.guild} balance={self.get_balance()})"

    def __str__(self):
        return repr(self)

    @staticmethod
    def update_all(session: Session, members: Iterable[discord.Member]):
        ids = set((member.id, member.guild.id) for member in members)
        for member_data in Member.get_all(session):
            if (member_data.user_id, member_data.guild_id) not in ids:
                session.delete(member_data)

        for member in members:
            Member.update(session, member)

    @staticmethod
    def get(session: Session, member: discord.Member):
        return session.query(Member).filter(Member.id == member.id, Member.guild_id == member.guild.id).first()

    @staticmethod
    def add(session: Session, member: discord.Member):
        if Member.get(session, member):
            raise ValueError("Участник уже есть в базе")
        member_data = Member()
        member_data.user_id = member.id
        member_data.guild_id = member.guild.id
        member_data.display_name = member.display_name
        member_data.joined_at = member.joined_at
        member_data.desktop_status = member.desktop_status
        member_data.mobile_status = member.mobile_status
        member_data.web_status = member.web_status

        session.add(member_data)
        return member_data

    @staticmethod
    def update(session: Session, member: discord.Member):
        member_data = Member.get(session, member)
        if not member_data:
            member_data = Member.add(session, member)
        else:
            member_data.user_id = member.id
            member_data.guild_id = member.guild.id
            member_data.display_name = member.display_name
            member_data.joined_at = member.joined_at
            member_data.desktop_status = member.desktop_status
            member_data.mobile_status = member.mobile_status
            member_data.web_status = member.web_status
        return member_data

    @staticmethod
    def delete(session: Session, member: discord.Member):
        member_data = Member.get(session, member)
        if not member_data:
            raise ValueError("Такого участника нет в базе")
        session.delete(member_data)
        return member_data

