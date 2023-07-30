import asyncio

import discord

from discord.ext import commands

from diablo_elixir_alerter import DiabloElixirAlerter
from introducer import IntroducerCog
from logs import setup_logging
from secret import TOKEN
from tts import TTS

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix='!',
    intents=intents,
)

@bot.event
async def on_ready():
    print( f'Logged in as {bot.user} (ID: {bot.user.id if bot.user else ""})' )
    print( '-' * 100 )

async def main():
    setup_logging()

    tts = TTS()

    async with bot:
        await bot.add_cog( IntroducerCog( bot, tts ) )
        await bot.add_cog( DiabloElixirAlerter( bot ) )
        await bot.start( TOKEN )

if __name__ == '__main__':
    try:
        asyncio.run( main() )
    except KeyboardInterrupt:
        pass