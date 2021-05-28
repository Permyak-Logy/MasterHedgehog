from db_session import SqlAlchemyBase
from sqlalchemy import Column, Integer, String, ForeignKey


class Channel(SqlAlchemyBase):
    __tablename__ = 'channels'

    id = Column(Integer)
    name = Column(String)
    type = Column(Integer)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # Для DMChannel

    owner_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # Для GroupChannel

    # Для остальных
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    guild_id = Column(Integer, ForeignKey('guilds.id'), nullable=True)

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id} name='{self.name}')"
