import asyncio

import discord

from discord.ext import commands

def get_channel_voice_client( bot: commands.Bot, channel: discord.VoiceChannel | discord.StageChannel ) -> discord.VoiceClient | None:
    return discord.utils.get( bot.voice_clients, channel=channel ) # type: ignore

async def join_voice_chat( bot: commands.Bot, channel: discord.VoiceChannel | discord.StageChannel ) -> discord.VoiceClient:
        voice_client: discord.VoiceClient | None = get_channel_voice_client( bot, channel )
        if voice_client is None:
            voice_client = discord.utils.get( bot.voice_clients, guild=channel.guild ) # type: ignore
            if voice_client is not None:
                await voice_client.disconnect()

            voice_client = await channel.connect( self_mute=False, self_deaf=True )
        else:
            await voice_client.channel.guild.change_voice_state( channel=voice_client.channel, self_mute=False, self_deaf=True )

        return voice_client

async def play_voice_channel_audio( voice_client: discord.VoiceClient, source: discord.AudioSource ):
        while voice_client.is_playing():
             await asyncio.sleep( 0.25 )

        future = asyncio.get_running_loop().create_future()

        def after_play( ex: Exception | None ):
            if ex:
                future.set_exception( ex )
            else:
                future.set_result( None )

        voice_client.play( source, after=after_play )

        await future