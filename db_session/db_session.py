import logging
import os

import sqlalchemy as sa
import sqlalchemy.ext.declarative as dec
import sqlalchemy.orm as orm
from sqlalchemy.orm import Session

from .const import MAX_BIGINT, MIN_BIGINT

logging = logging.getLogger(__name__)

SqlAlchemyBase = dec.declarative_base()

SqlAlchemyBase.get_all = classmethod(lambda cls, session: session.query(cls).all())

# noinspection PyTypeChecker
__factory: orm.sessionmaker = None


def __enter__(self: Session) -> Session:
    return self


def __exit__(self: Session, *_, **__):
    self.close()


Session.__enter__ = __enter__
Session.__exit__ = __exit__


class ExtraTools:
    # @classmethod
    # def get_all(cls, session: Session) -> list:
    #     return session.query(cls).all()
    pass

# noinspection PyUnresolvedReferences
def global_init(db_file, models: dict = None):
    global __factory

    if __factory:
        # TODO: Перезагрузка базы данных
        raise RuntimeError("База данных уже инициированна")

    if not db_file or not db_file.strip():
        raise Exception("Необходимо указать файл базы данных.")

    from . import __all_models
    if models:
        for key, val in models.items():
            setattr(__all_models, key, val)

    directory = os.path.split(db_file)[0]
    if directory and not os.path.isdir(directory):
        os.mkdir(directory)

    conn_str = f'sqlite:///{db_file.strip()}?check_same_thread=False'
    logging.info(f"Подключение к базе данных по адресу {conn_str}")

    engine = sa.create_engine(conn_str, echo=False)
    __factory = orm.sessionmaker(bind=engine)

    SqlAlchemyBase.metadata.create_all(engine)


def bigint(value: int) -> int:
    return max(MIN_BIGINT, min(value, MAX_BIGINT))


def create_session() -> Session:
    global __factory
    return __factory()
