from db_session import SqlAlchemyBase
from sqlalchemy import Column, Integer, String


class Categories(SqlAlchemyBase):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, nullable=False)
    guild_id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String, nullable=False)

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id} name={self.name})"
