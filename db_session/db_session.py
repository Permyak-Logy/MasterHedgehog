import logging

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


# __enter__ и __exit__ для функционирования с with для сессий
def __enter__(self: Session) -> Session:
    return self


def __exit__(self: Session, *_, **__):
    self.close()


Session.__enter__ = __enter__
Session.__exit__ = __exit__


class ExtraTools:
    pass


# noinspection PyUnresolvedReferences
def global_init(conn_str, models: dict = None):
    global __factory

    if __factory:
        # TODO: Перезагрузка базы данных
        raise RuntimeError("База данных уже инициирована")

    if not conn_str or not conn_str.strip():
        raise Exception("Необходимо указать подключение к базе данных.")

    from . import __all_models
    if models:
        for key, val in models.items():
            setattr(__all_models, key, val)

    logging.info(f"Подключение к базе данных по адресу {conn_str}")

    engine = sa.create_engine(conn_str, echo=False, pool_pre_ping=True)
    __factory = orm.sessionmaker(bind=engine)

    SqlAlchemyBase.metadata.create_all(engine)


def bigint(value: int) -> int:
    return max(MIN_BIGINT, min(value, MAX_BIGINT))


def create_session(**kwargs) -> Session:
    global __factory
    return __factory(**kwargs)
