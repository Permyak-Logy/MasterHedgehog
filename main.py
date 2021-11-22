import datetime
import json
import logging
import os

import discord
from discord.ext import commands

from PLyBot import Bot, not_in, HelpCommand
from PLyBot.enums import TypeBot

with open('config.json', encoding='utf8') as conf_file:
    CONFIG = json.load(conf_file)


def main():
    logging_conf: dict = CONFIG['logging']
    handlers_log = []
    if logging_conf['output']['console']:
        handlers_log.append(logging.StreamHandler())
    if logging_conf['output']['file']:
        handlers_log.append(logging.FileHandler(CONFIG['logging']['output']['file'], encoding='utf8'))
    logging.basicConfig(level=logging.INFO, format=CONFIG['logging']['format'],
                        handlers=handlers_log)
    logging.info("Start Program")

    bot_conf: dict = CONFIG['bot']
    bot = Bot(
        command_prefix=bot_conf['command_prefix'],
        db_con=bot_conf['db_con'],
        owner_ids=CONFIG['admins'],
        root_id=CONFIG['root'],
        activity=discord.Game(bot_conf['game_activity']),
        bot_name=bot_conf['bot_name'],
        turn_on_api_server=bot_conf.get('turn_on_api_server', False),
        footer=("PyPLy © | Сделано в России! 👀",
                "https://cdn.discordapp.com/avatars/403910550028943361/3e5168bf62228b8e3f3ac58da97b563b.webp"),
        help_command=HelpCommand(width=70),
        bot_type=TypeBot.both,
        ignore_errors=(commands.CommandNotFound, commands.CheckFailure),
        permissions=8, version=("Beta 0.13", datetime.date(day=21, month=11, year=2021))
    )

    # noinspection SpellCheckingInspection
    cogs_names = filter(not_in(['__init__.py', '__pycache__'] + ['warframe.py', 'APs.py', 'game_activity.py']),
                        os.listdir('cogs'))
    cogs = list(map(lambda x: f"cogs.{x[:-3]}", cogs_names)) + ['PLyBot.info', 'PLyBot.api']
    bot.load_all_extensions(cogs)

    with open('token.txt', encoding='utf8') as token_file:
        bot.run(token_file.read())


if __name__ == '__main__':
    main()
