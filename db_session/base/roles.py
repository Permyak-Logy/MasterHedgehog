from db_session import SqlAlchemyBase
from sqlalchemy import Integer, String, ForeignKey, Column


class Role(SqlAlchemyBase):
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, ForeignKey('guilds.id'))
    name = Column(String)
    created_at = Column(Integer, nullable=False)
