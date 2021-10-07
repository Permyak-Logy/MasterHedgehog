from db_session import SqlAlchemyBase
import sqlalchemy


class Message(SqlAlchemyBase):
    __tablename__ = "messages"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)

    author = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), nullable=False)
    channel = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('channels.id'))

    content = sqlalchemy.Column(sqlalchemy.String, nullable=False)

    has_mentions = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=False)
    has_mentions_roles = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=False)
    has_mentions_everyone = sqlalchemy.Column(sqlalchemy.Boolean, nullable=False, default=False)

    created_at = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
