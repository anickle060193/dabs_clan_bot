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
INTROS_DIR = SOUNDS_DIR / 'intros'
WELCOMES_DIR = SOUNDS_DIR / 'welcomes'

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

    async def _get_member_sound( self, tts_text_format: str, member: discord.Member, sounds_path: Path, default: str ) -> Path:
        sound_mp3_path = sounds_path / f'{member.id}.mp3'
        if sound_mp3_path.is_file():
            return sound_mp3_path

        member_name = MEMBER_NAME_RE.sub( '', member.nick or member.display_name )
        tts_text = tts_text_format.format( name=member_name )

        try:
            response = await self._generate_tts( tts_text )

            sound_mp3_path.write_bytes( response.audio_content )
        except Exception as ex:
            print( f'Failed to generate TTS for "{tts_text}":', ex )

        return sound_mp3_path

    async def _get_intro_sound( self, member: discord.Member ) -> Path:
        return await self._get_member_sound( '{name} has joined the chat', member, INTROS_DIR, 'default.mp3' )

    def _get_channel_voice_client( self, channel: discord.VoiceChannel ) -> discord.VoiceClient | None:
        return discord.utils.get( self.bot.voice_clients, channel=channel )

    async def _join_voice_chat( self, channel: discord.VoiceChannel ) -> discord.VoiceClient:
        voice_client = self._get_channel_voice_client( channel )
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
            if all( m.bot for m in before.channel.members ):
                voice_client = self._get_channel_voice_client( before.channel )
                if voice_client:
                    await voice_client.disconnect()
            return

        print( member.name, f'(ID: {member.id})', 'joined', after.channel.name, f'(ID: {after.channel.id})' )

        intro_delayer = asyncio.create_task( asyncio.sleep( INTRO_DELAY ) )

        chat_joiner = asyncio.create_task( self._join_voice_chat( after.channel ) )
        sound_creator = asyncio.create_task( self._get_intro_sound( member ) )

        voice_client = await chat_joiner
        sound_mp3_path = await sound_creator

        await intro_delayer

        played_event = asyncio.Event()

        def after_play( ex: Exception | None ):
            if ex:
                print( 'Play error:', ex )

            played_event.set()

        source = discord.PCMVolumeTransformer( discord.FFmpegPCMAudio( source=str( sound_mp3_path ) ) )
        voice_client.play( source, after=after_play )

        await played_event.wait()
        await voice_client.channel.guild.change_voice_state( channel=voice_client.channel, self_mute=True, self_deaf=True )
