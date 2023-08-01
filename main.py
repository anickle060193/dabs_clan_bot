import asyncio
import logging

import discord

from discord.ext import commands

from diablo_elixir_alerter import DiabloElixirAlerter
from diablo_events_alerter import DiabloEventsAlerter
from introducer import IntroducerCog
from logs import setup_logging
from secret import TOKEN
from tts import TTS

LOG = logging.getLogger( __name__ )

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix='!',
    intents=intents,
)

@bot.event
async def on_ready():
    LOG.info( f'READY: Logged in as {bot.user} (ID: {bot.user.id if bot.user else ""})' )

async def main():
    setup_logging()

    tts = TTS()

    async with bot:
        await bot.add_cog( IntroducerCog( bot, tts ) )
        await bot.add_cog( DiabloElixirAlerter( bot ) )
        await bot.add_cog( DiabloEventsAlerter( bot, tts ) )
        await bot.start( TOKEN )

if __name__ == '__main__':
    try:
        asyncio.run( main() )
    except KeyboardInterrupt:
        pass