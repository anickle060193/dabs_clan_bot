import asyncio
import re

from pathlib import Path
from typing import Any, Coroutine

import discord

from discord.ext import commands
from discord.ext.commands.context import Context
from google.cloud import texttospeech_v1 as gtts

THIS_DIR = Path( __file__ ).parent

SOUNDS_DIR = THIS_DIR / 'sounds'

DEFAULT_INTRODUCTION_PATH = SOUNDS_DIR / 'default.mp3'

INTRO_DELAY = 0.5

MEMBER_NAME_RE = re.compile( r'\d*$' )

class IntroducerCog( commands.Cog ):
    def __init__( self, bot: commands.Bot ) -> None:
        self.bot = bot
        self.gtts_client = gtts.TextToSpeechAsyncClient()

    async def _generate_tts( self, text: str ) -> gtts.SynthesizeSpeechResponse:
        tts_input = gtts.SynthesisInput()
        tts_input.text = text

        audio_config = gtts.AudioConfig()
        audio_config.audio_encoding = 'MP3'
        audio_config.effects_profile_id = [ 'headphone-class-device' ]

        voice = gtts.VoiceSelectionParams()
        voice.language_code = 'en-US'
        voice.name = 'en-US-Wavenet-F'

        request = gtts.SynthesizeSpeechRequest(
            input=tts_input,
            audio_config=audio_config,
            voice=voice,
        )

        return await self.gtts_client.synthesize_speech( request=request )

    async def _get_introduction_sound( self, member: discord.Member ) -> Path:
        introduction_mp3_path = SOUNDS_DIR / f'{member.id}.mp3'
        if introduction_mp3_path.is_file():
            return introduction_mp3_path

        try:
            print( 'Generating introduction for', member.name )
            member_name = MEMBER_NAME_RE.sub( '', member.nick or member.display_name )

            response = await self._generate_tts( f'{member_name} has joined the chat' )

            introduction_mp3_path.write_bytes( response.audio_content )

            return introduction_mp3_path
        except Exception as ex:
            print( 'Failed to generate TTS intro for', member.name, ':', ex )

        return DEFAULT_INTRODUCTION_PATH

    async def _join_voice_chat( self, channel: discord.VoiceChannel ) -> discord.VoiceClient:
        voice_client: discord.VoiceClient | None = discord.utils.get( self.bot.voice_clients, channel=channel )
        if voice_client is None:
            voice_client = discord.utils.get( self.bot.voice_clients, guild=channel.guild )
            if voice_client is not None:
                await voice_client.disconnect()

            voice_client = await channel.connect( self_mute=False, self_deaf=True )
        else:
            await voice_client.channel.guild.change_voice_state( channel=voice_client.channel, self_mute=False, self_deaf=True )

        return voice_client

    async def cog_command_error( self, ctx: Context, error: Exception ) -> Coroutine[ Any, Any, None ]:
        print( f'COG {self.__cog_name__} COMMAND ERROR: {error}' )

    @commands.Cog.listener()
    async def on_voice_state_update( self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState ):
        if member.bot:
            return
        if before.channel == after.channel:
            return
        if not after.channel:
            return

        print( member.name, f'(ID: {member.id})', 'joined', after.channel.name, f'(ID: {after.channel.id})' )

        intro_delayer = asyncio.create_task( asyncio.sleep( INTRO_DELAY ) )

        voice_client = await self._join_voice_chat( after.channel )

        # if all( m.bot or m == member for m in after.channel.members ):
        #     return

        introduction_mp3_path = await self._get_introduction_sound( member )

        await intro_delayer

        played_event = asyncio.Event()

        def after_play( ex: Exception | None ):
            if ex:
                print( 'Play error:', ex )

            played_event.set()

        source = discord.PCMVolumeTransformer( discord.FFmpegPCMAudio( source=str( introduction_mp3_path ) ) )
        voice_client.play( source, after=after_play )

        await played_event.wait()
        await voice_client.channel.guild.change_voice_state( channel=voice_client.channel, self_mute=True, self_deaf=True )
