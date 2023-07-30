import asyncio
import random

from datetime import datetime, timedelta

import discord

from discord.ext import tasks, commands

from consts import ELIXIR_ALERT_SOUNDS_DIR
from utils import join_voice_chat

DIABLO_VOICE_CHANNEL_IDS = [
    1088975077179150479, # DABS Clan - diablo4-party-channel
    1128140152418611221, # anickle060193's Test Server - Other Channel
]

AFTER_JOIN_ALERT_DELAY = timedelta( minutes=5 )
ALERT_INTERVAL = timedelta( minutes=15 )

class DiabloElixirAlerter( commands.Cog ):
    def __init__( self, bot: commands.Bot ) -> None:
        self.bot = bot
        self.next_alert_time = dict( ( cid, datetime.min ) for cid in DIABLO_VOICE_CHANNEL_IDS )

        self.elixir_alert.start()

    def cog_unload( self ):
        self.elixir_alert.cancel()

    @tasks.loop( minutes=1 )
    async def elixir_alert( self ):
        await asyncio.gather( *( self._perform_elixir_alert_safe( cid ) for cid in self.next_alert_time.keys() ), return_exceptions=True )

    @elixir_alert.before_loop
    async def before_elixir_alert( self ):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_voice_state_update( self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState ):
        if member.bot:
            return
        if before.channel == after.channel:
            return

        if before.channel and before.channel.id in self.next_alert_time:
            await self._perform_elixir_alert( before.channel.id )
        elif after.channel and after.channel.id in self.next_alert_time:
            await self._perform_elixir_alert( after.channel.id )

    async def _perform_elixir_alert_safe( self, channel_id: int ):
        try:
            await self._perform_elixir_alert( channel_id )
        except Exception as ex:
            print( 'Failed to perform elixir alert for channel:', channel_id, ex )

    async def _perform_elixir_alert( self, channel_id: int ):
        print( 'Performing elixir alert:', channel_id )

        if channel_id not in self.next_alert_time:
            print( 'Unknown channel ID:', channel_id )
            return

        channel = self.bot.get_channel( channel_id )
        if not isinstance( channel, ( discord.VoiceChannel, discord.StageChannel ) ):
            if channel:
                print( 'Channel is not a voice channel:', channel )
            else:
                print( 'Could not find voice channel:', channel_id )
            return

        if len( channel.members ) == 0 or all( m.bot for m in channel.members ):
            if self.next_alert_time[ channel_id ] != datetime.min:
                print( 'Empty channel detected:', channel_id )
                self.next_alert_time[ channel_id ] = datetime.min
            return

        if self.next_alert_time[ channel_id ] == datetime.min:
            print( 'First member join detected:', channel_id )
            self.next_alert_time[ channel_id ] = datetime.now() + AFTER_JOIN_ALERT_DELAY
            return

        now = datetime.now()
        if self.next_alert_time[ channel_id ] > now:
            print( 'Waiting for alert time:', channel_id, ( self.next_alert_time[ channel_id ] - now ), 'remaining' )
            return

        print( 'Playing elixir alert:', channel_id )
        self.next_alert_time[ channel_id ] = now + ALERT_INTERVAL

        voice_client = await join_voice_chat( self.bot, channel )

        alert_sound_mp3_path = random.choice( list( ELIXIR_ALERT_SOUNDS_DIR.glob( '*.mp3' ) ) )

        def after_play( ex: Exception | None ):
            if ex:
                print( 'Failed to play elixir alert:', alert_sound_mp3_path, ex )

        source = discord.PCMVolumeTransformer( discord.FFmpegPCMAudio( source=str( alert_sound_mp3_path ) ) )
        voice_client.play( source, after=after_play )