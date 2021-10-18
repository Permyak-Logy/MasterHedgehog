import json
import logging
import os

import discord

from PLyBot import Bot, not_in
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
        activity=discord.Game(bot_conf['game_activity']),
        bot_name=bot_conf['bot_name'],
        turn_on_api_server=bot_conf.get('turn_on_api_server', False),

        bot_type=TypeBot.both,
        permissions=8,  # == Администратор
        version="Beta 0.10.1"  # Дата 18.10.2021
    )

    cogs_names = filter(not_in(['__init__.py', '__pycache__'] + ['warface.py', 'warframe.py']),
                        os.listdir('cogs'))
    cogs = list(map(lambda x: f"cogs.{x[:-3]}", cogs_names))

    cogs.append('PLyBot.info')
    cogs.append('PLyBot.api')
    bot.load_all_extensions(cogs)

    with open('token.txt', encoding='utf8') as token_file:
        bot.run(token_file.read())


if __name__ == '__main__':
    main()
