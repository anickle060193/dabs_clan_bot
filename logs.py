import logging

from datetime import datetime

import discord

from consts import LOGS_DIR

def setup_logging():
    stream_handler = logging.StreamHandler()

    discord.utils.setup_logging( root=True, handler=stream_handler, level=logging.DEBUG )

    stream_handler.setLevel( logging.INFO )

    logger = logging.getLogger()

    formatter = logging.Formatter( '[{asctime}] [{levelname:<8}] {name}: {message}', datefmt='%Y-%m-%d %H:%M:%S', style='{' )

    LOGS_DIR.mkdir( parents=True, exist_ok=True )
    file_handler = logging.FileHandler(
        filename=LOGS_DIR / 'dabs_clan_discord_bot.{:%Y-%m-%d_%H.%M.%S}.log'.format( datetime.now() ),
        encoding='utf-8',
    )
    file_handler.setLevel( logging.DEBUG )
    file_handler.setFormatter( formatter )
    logger.addHandler( file_handler )