import datetime
import secrets

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey

import db_session
from PLyBot import Context
from db_session import SqlAlchemyBase


class Permissions:
    VIEW = 1
    EDIT = 2

    @staticmethod
    def make(**flags) -> int:
        flag = 0

        flag |= Permissions.VIEW if flags.pop('view') else 0
        flag |= Permissions.EDIT if flags.pop('edit') else 0

        if flags:
            raise TypeError(f'Передан неизвестный ключ {flags}')

        return flag


# TODO: Доделать
class ApiKey(SqlAlchemyBase):  # TODO: Ассиметричное шифрование добавить
    __tablename__ = 'api_keys'

    key = Column(String, primary_key=True)
    permission = Column(Integer, nullable=False, default=Permissions.make())
    until_active = Column(DateTime)

    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(Integer, nullable=False, default=datetime.datetime.now)
    created_for_guild = Column(Integer, ForeignKey('guilds.id'), nullable=False)

    @staticmethod
    def get(session: db_session.Session, key: str):
        return session.query(ApiKey).filter(ApiKey.key == key).first()

    def gen(self, ctx: Context, permission_flags=0, until_active: datetime.datetime = None):
        self.key = secrets.token_hex(32)
        self.permission = Permissions.make()
        self.until_active = datetime.datetime.now()

        self.created_by = ctx.author.id
        self.created_for_guild = ctx.guild.id

    def __repr__(self):
        return f"ApiKey"

    def __str__(self):
        return repr(self)
