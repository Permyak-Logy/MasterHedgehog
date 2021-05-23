from db_session import SqlAlchemyBase
import sqlalchemy


class Message(SqlAlchemyBase):
    __tablename__ = "messages"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)

    guild = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('guilds.id'))
    author = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('members.id'), nullable=False)
    channel = sqlalchemy.Column(sqlalchemy.Integer)

    content = sqlalchemy.Column(sqlalchemy.String, nullable=False)

    has_mentions = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=False)
    has_mentions_roles = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=False)
    has_mentions_everyone = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=False)

    timestamp = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
