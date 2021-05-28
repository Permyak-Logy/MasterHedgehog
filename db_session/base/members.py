import datetime
from typing import List

import discord
from sqlalchemy import orm, Column, Integer, String, DateTime, ForeignKey

from db_session import SqlAlchemyBase
from db_session.const import MIN_DATETIME


class Member(SqlAlchemyBase):
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
