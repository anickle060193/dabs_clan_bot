import asyncio
import re

from pathlib import Path

import discord

from discord.ext import commands

from consts import SOUNDS_DIR
from tts import TTS
from utils import get_channel_voice_client, join_voice_chat

INTROS_DIR = SOUNDS_DIR / 'intros'
WELCOMES_DIR = SOUNDS_DIR / 'welcomes'

INTRO_DELAY = 0.5

MEMBER_NAME_RE = re.compile( r'\d*$' )

class IntroducerCog( commands.Cog ):
    def __init__( self, bot: commands.Bot, tts: TTS ) -> None:
        self.bot = bot
        self.tts = tts

    async def _get_member_sound( self, tts_text_format: str, member: discord.Member, sounds_path: Path, default_sound: str ) -> Path:
        sound_mp3_path = sounds_path / f'{member.id}.mp3'
        if sound_mp3_path.is_file():
            return sound_mp3_path

        member_name = MEMBER_NAME_RE.sub( '', member.nick or member.display_name )
        tts_text = tts_text_format.format( name=member_name )

        try:
            audio_content = await self.tts.generate_tts( tts_text, language_code='en-US', voice_name='en-US-Wavenet-F' )
            sound_mp3_path.write_bytes( audio_content )
        except Exception as ex:
            print( f'Failed to generate TTS for "{tts_text}":', ex )

        return sounds_path / default_sound

    async def _get_intro_sound( self, member: discord.Member, welcome=False ) -> Path:
        if welcome:
            text_format = 'Welcome {name}'
            sounds_dir = WELCOMES_DIR
        else:
            text_format = '{name} has joined the chat'
            sounds_dir = INTROS_DIR

        return await self._get_member_sound( text_format, member, sounds_dir, 'default.mp3' )

    @commands.Cog.listener()
    async def on_voice_state_update( self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState ):
        if member.bot:
            return
        if before.channel == after.channel:
            return

        if not after.channel:
            if before.channel:
                if all( m.bot for m in before.channel.members ):
                    voice_client = get_channel_voice_client( self.bot, before.channel )
                    if voice_client:
                        await voice_client.disconnect()
            return

        print( member.name, f'(ID: {member.id})', 'joined', after.channel.name, f'(ID: {after.channel.id})' )

        welcome = all( m.bot or m == member for m in after.channel.members )

        intro_delayer = asyncio.create_task( asyncio.sleep( INTRO_DELAY ) )

        chat_joiner = asyncio.create_task( join_voice_chat( self.bot, after.channel ) )
        sound_creator = asyncio.create_task( self._get_intro_sound( member, welcome=welcome ) )

        voice_client = await chat_joiner
        sound_mp3_path = await sound_creator

        await intro_delayer

        def after_play( ex: Exception | None ):
            if ex:
                print( 'Failed to play intro:', sound_mp3_path, ex )

        source = discord.PCMVolumeTransformer( discord.FFmpegPCMAudio( source=str( sound_mp3_path ) ) )
        voice_client.play( source, after=after_play )
