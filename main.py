import asyncio

import discord

from discord.ext import commands

from introducer import IntroducerCog
from secret import TOKEN

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
    asyncio.run( main() )