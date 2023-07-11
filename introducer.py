from pathlib import Path
from typing import Any, Coroutine, Dict

import discord

from discord.ext import commands
from discord.ext.commands.context import Context

THIS_DIR = Path( __file__ ).parent
FFMPEG_EXE = THIS_DIR / 'ffmpeg/ffmpeg.exe'

SOUNDS_DIR = THIS_DIR / 'sounds'

USER_SOUNDS: Dict[ int, Path ] = {
}

DEFAULT_JOIN_SOUND = SOUNDS_DIR / 'default_join.mp3'

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

                voice_client = discord.utils.get( self.bot.voice_clients, channel=after.channel )
                if voice_client is None:
                    voice_client = discord.utils.get( self.bot.voice_clients, guild=after.channel.guild )
                    if voice_client is not None:
                        await voice_client.disconnect()
                        voice_client = None

                    voice_client = await after.channel.connect( self_deaf=True )

                # if all( m.bot or m == member for m in after.channel.members ):
                #     return

                sound_mp3 = USER_SOUNDS.get( member.id, DEFAULT_JOIN_SOUND )
                source = discord.PCMVolumeTransformer( discord.FFmpegPCMAudio( source=sound_mp3, executable=FFMPEG_EXE ) )
                voice_client.play( source, after=lambda e: print( f'Player error: {e}' ) if e else None )