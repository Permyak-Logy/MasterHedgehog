import datetime
import sqlalchemy
from db_session import SqlAlchemyBase
from sqlalchemy import orm


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
