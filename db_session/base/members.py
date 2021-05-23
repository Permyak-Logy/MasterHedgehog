import datetime
from typing import List

import discord
import sqlalchemy
from sqlalchemy import orm

from db_session import SqlAlchemyBase
from db_session.const import MIN_DATETIME


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

    cash = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, default=0)
    deposit = sqlalchemy.Column(sqlalchemy.BIGINT, nullable=False, default=0)

    last_activity = sqlalchemy.Column(sqlalchemy.DateTime, default=MIN_DATETIME)

    joined = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=True)

    guild = orm.relation('Guild')
    user = orm.relation('User')

    # feature = orm.relationship("FeatureMember", uselist=False, back_populates="member")
    # balance = orm.relationship("Balance", uselist=False, back_populates="member")

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
