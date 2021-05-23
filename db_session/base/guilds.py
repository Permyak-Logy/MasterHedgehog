from db_session import SqlAlchemyBase
import sqlalchemy
from sqlalchemy import orm


class Guild(SqlAlchemyBase):
    __tablename__ = 'guilds'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, nullable=False)
    owner = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), nullable=False)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=False)

    ban_activity = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    members = orm.relation("Member", back_populates='guild')

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"

    def __str__(self):
        return repr(self)
