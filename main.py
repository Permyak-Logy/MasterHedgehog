import datetime
import json
import logging
import os
import sys

import discord
from discord.ext import commands

from PLyBot import Bot, not_in, HelpCommand, in_
from PLyBot.enums import TypeBot

with open('config.json', encoding='utf8') as conf_file:
    CONFIG = json.load(conf_file)


def init_logging(logging_conf: dict):
    handlers_log = []
    if logging_conf['output']['console']:
        handlers_log.append(logging.StreamHandler())
    if logging_conf['output']['file']:
        handlers_log.append(logging.FileHandler(CONFIG['logging']['output']['file'], encoding='utf8'))
    logging.basicConfig(level=logging.INFO, format=CONFIG['logging']['format'],
                        handlers=handlers_log)


def get_cogs():
    cogs_names = filter(not_in(['__init__.py', '__pycache__'] + [
        'warframe.py', 'APs.py', 'game_activity.py', 'statistic.py', 'bodyguard.py', 'developer.py',
    'private_channels.py']),
                        os.listdir('cogs'))
    cogs_names = []
    cogs = list(map(lambda x: f"cogs.{x[:-3]}", cogs_names)) + ['PLyBot.info']  # , 'PLyBot.api']
    return cogs


def get_cogs2():
    cogs_names = filter(in_(["bodyguard.py", "developer.py", "private_channels.py"]), os.listdir('cogs'))
    cogs = list(map(lambda x: f"cogs.{x[:-3]}", cogs_names)) + ['PLyBot.info', 'PLyBot.api']
    return cogs


def main():
    logging_conf: dict = CONFIG['logging']
    bot_conf: dict = CONFIG['bot']
    users_conf: dict = CONFIG['users']

    init_logging(logging_conf)
    logging.info("Start Program")

    bot = Bot(
        command_prefix=bot_conf['command_prefix'],
        db_con=bot_conf['db_con'],
        turn_on_api_server=bot_conf.get('turn_on_api_server', False),
        permissions=bot_conf['permissions'],

        activity=discord.Game(bot_conf['game_activity']),
        bot_name=bot_conf['bot_name'],

        root_id=users_conf['root'],
        owner_ids=users_conf['admins'],

        version=("Beta 0.15.5", datetime.date(day=19, month=3, year=2022)),
        footer=bot_conf['footer'],
        colour=discord.Colour.from_rgb(*bot_conf['colour']),

        ignore_errors=(commands.CommandNotFound,),  # commands.CheckFailure),
        bot_type=TypeBot.both,
        help_command=HelpCommand(width=70),
        rebooted='--rebooted' in sys.argv,
    )

    bot.load_all_extensions(get_cogs())

    with open('token.txt', encoding='utf8') as token_file:
        bot.run(token_file.read())


if __name__ == '__main__':
    main()
