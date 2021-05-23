from .bot import Bot, Cog, Context
from .extra import *
from .help import HelpCommand
from .info import InfoCog


def main(*args, db_file: str = None, **kwargs):
    app = Bot(db_file=db_file)
    app.add_cog(InfoCog(app))
    app.run(*args, **kwargs)
