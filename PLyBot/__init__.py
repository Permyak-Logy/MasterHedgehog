from .api import AccessCog, ApiKey, BaseApiBP
from .bot import Bot, Cog, Context
from .extra import Check, HRF, DBTools
from .extra import ONLINE, OFFLINE, IDLE, DND, INVISIBLE, T
from .extra import equal, not_equal, not_in, in_
from .extra import full_using_db, run_if_ready_db, plug_func, plug_afunc
from .extra import get_obj, join_string, get_time_from_string, cast_status_to_int, get_any
from .help import HelpCommand
from .info import InfoCog


def main(*args, db_con: str = None, **kwargs):
    app = Bot(db_con=db_con)
    app.add_cog(InfoCog(app))
    app.add_models(InfoCog(app))
    app.run(*args, **kwargs)
