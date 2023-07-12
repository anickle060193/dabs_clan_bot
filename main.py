import asyncio
import logging
import logging.handlers

from datetime import datetime
from pathlib import Path

import discord

from discord.ext import commands

from introducer import IntroducerCog
from secret import TOKEN

THIS_DIR = Path( __file__ ).parent

LOGS_DIR = THIS_DIR / 'logs'

discord.utils.setup_logging()

logging.getLogger( 'discord.http' ).setLevel( logging.INFO )

logger = logging.getLogger( 'discord' )

LOGS_DIR.mkdir( parents=True, exist_ok=True )
handler = logging.FileHandler(
    filename=LOGS_DIR / 'dabs_clan_discord_bot.{:%Y-%m-%d_%H.%M.%S}.log'.format( datetime.now() ),
    encoding='utf-8',
)

formatter = logging.Formatter( '[{asctime}] [{levelname:<8}] {name}: {message}', datefmt='%Y-%m-%d %H:%M:%S', style='{' )
handler.setLevel( logging.DEBUG )
handler.setFormatter( formatter )
logger.addHandler( handler )

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix='!',
    intents=intents,
)

@bot.event
async def on_ready():
    print( f'Logged in as {bot.user} (ID: {bot.user.id})' )
    print( '-' * 100 )

async def main():
    async with bot:
        await bot.add_cog( IntroducerCog( bot ) )
        await bot.start( TOKEN )

if __name__ == '__main__':
    try:
        asyncio.run( main() )
    except KeyboardInterrupt:
        pass