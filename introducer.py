import asyncio

from pathlib import Path
from typing import Any, Coroutine, Dict

import discord

from discord.ext import commands
from discord.ext.commands.context import Context

THIS_DIR = Path( __file__ ).parent
FFMPEG_EXE = THIS_DIR / 'ffmpeg/ffmpeg.exe'

SOUNDS_DIR = THIS_DIR / 'sounds'

USER_SOUNDS: Dict[ int, Path ] = {
    429914580592885771: SOUNDS_DIR / 'shini.mp3',
}

DEFAULT_SOUND = SOUNDS_DIR / 'default.mp3'

class IntroducerCog( commands.Cog ):
    def __init__( self, bot: commands.Bot ) -> None:
        self.bot = bot

    async def cog_command_error( self, ctx: Context, error: Exception ) -> Coroutine[ Any, Any, None ]:
        print( f'COG {self.__cog_name__} COMMAND ERROR: {error}' )

    @commands.Cog.listener()
    async def on_voice_state_update( self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState ):
        if member.bot:
            return

        if before.channel != after.channel:
            if after.channel:
                print( member.name, f'(ID: {member.id})', 'joined', after.channel.name )

                voice_client: discord.VoiceClient | None = discord.utils.get( self.bot.voice_clients, channel=after.channel )
                if voice_client is None:
                    voice_client = discord.utils.get( self.bot.voice_clients, guild=after.channel.guild )
                    if voice_client is not None:
                        await voice_client.disconnect()

                    voice_client = await after.channel.connect( self_mute=False, self_deaf=True )
                else:
                    await voice_client.channel.guild.change_voice_state( channel=voice_client.channel, self_mute=False, self_deaf=True )

                # if all( m.bot or m == member for m in after.channel.members ):
                #     return

                played_event = asyncio.Event()

                def after_play( ex: Exception | None ):
                    if ex:
                        print( 'Play error:', ex )

                    played_event.set()

                sound_mp3 = USER_SOUNDS.get( member.id, DEFAULT_SOUND )
                source = discord.PCMVolumeTransformer( discord.FFmpegPCMAudio( source=sound_mp3, executable=FFMPEG_EXE ) )
                voice_client.play( source, after=after_play )

                await played_event.wait()
                await voice_client.channel.guild.change_voice_state( channel=voice_client.channel, self_mute=True, self_deaf=True )
