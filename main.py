import logging
import os

import discord

from PLyBot import Bot, not_in
from PLyBot.enums import TypeBot


# TODO: Сделать ограничения в функциях событиях при недоступных модулях

def main():
    if os.path.isfile('db\\database.sqlite'):
        os.remove('db\\database.sqlite')

    c_log = logging.StreamHandler()
    f_log = logging.FileHandler('logs\\bot.log', encoding='utf8')
    # noinspection PyArgumentList
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
                        handlers=[c_log, f_log])

    logging.info("Start Program")
    owners = [
        403910550028943361,  # Permyak_Logy
        548412818991349780,  # Evil Glitter
        832894974227251240,  # Glitter Silk
        510033548422545411,  # Mavisels
        576037038042775563,  # Avoidman
    ]

    bot = Bot(
        command_prefix="!!",
        db_file='db\\database.sqlite',
        bot_type=TypeBot.both,
        owner_ids=owners,
        activity=discord.Game("кустики"),
        version="Beta 2021.5.23",
        bot_name="Хог",
        permissions=8
    )

    # cogs = list(map(lambda x: f"cogs.{x[:-3]}",
    #                 filter(not_in([
    #                     '__init__.py', '__pycache__', 'warface.py', 'warframe.py'
    #                 ]), os.listdir('cogs'))))
    # cogs = ['PLyBot.info']
    # bot.load_all_extensions(cogs)

    # noinspection SpellCheckingInspection
    bot.run('NjEzNjQ1NTkyMjQxMTExMDQw.XVz7_g.qj4oltJ5JApCXIW3i5SiHvHJ1xs')


if __name__ == '__main__':
    main()
