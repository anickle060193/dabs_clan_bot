import asyncio
import io
import logging

from datetime import datetime, timedelta
from typing import List, Set

import discord

from discord.ext import tasks, commands

from constants import DIABLO_VOICE_CHANNEL_IDS
from diablo_events import DiabloEvents, get_diablo_events
from tts import TTS
from utils import join_voice_chat, play_voice_channel_audio

LOG = logging.getLogger( __name__ )

BOSS_ALERT_INTERVALS = [
    timedelta( minutes=60 ),
    timedelta( minutes=30 ),
    timedelta( minutes=15 ),
    timedelta( minutes=5 ),
    timedelta( minutes=2 ),
    timedelta( minutes=1 ),
]

LEGION_ALERT_INTERVALS = [
    timedelta( minutes=4, seconds=30 ),
    timedelta( minutes=2 ),
]

HELLTIDE_ALERT_INTERVALS = [
    timedelta( minutes=15 ),
    timedelta( minutes=5 ),
    timedelta( minutes=1 ),
]

class DiabloEventsAlerter( commands.Cog ):
    def __init__( self, bot: commands.Bot, tts: TTS ) -> None:
        self.bot = bot
        self.tts = tts

        self.diablo_voice_channel_ids: Set[ int ] = set()

        self.last_events: DiabloEvents | None = None
        self.last_boss_alert = datetime.min
        self.last_legion_alert = datetime.min
        self.last_helltide_alert = datetime.min

        self.events_checker.start()

    def _check_guild_for_diablo_voice_channel( self, guild: discord.Guild ):
        for channel_id in DIABLO_VOICE_CHANNEL_IDS:
            if channel_id not in self.diablo_voice_channel_ids:
                channel = guild.get_channel( channel_id )
                if isinstance( channel, discord.VoiceChannel ):
                    LOG.info( f'Detected guild ({guild.name} - {guild.id}) with Diablo voice channel ({channel.name} - {channel.id}), adding to Diablo events alerter' )
                    self.diablo_voice_channel_ids.add( channel_id )
                    return

        LOG.info( f'Guild ({guild.name} - {guild.id}) has not Diablo voice channel' )

    async def _perform_event_alert_for_channel( self, channel: discord.VoiceChannel, audio_content: bytes ):
        if all( m.bot for m in channel.members ):
            LOG.info( f'Skipping event alert for empty channel: {channel.name} (ID: {channel.id})' )
            return

        voice_client = await join_voice_chat( self.bot, channel )

        try:
            source = discord.FFmpegPCMAudio( source=io.BytesIO( audio_content ), pipe=True )
            await play_voice_channel_audio( voice_client, source )
        except Exception as ex:
            LOG.error( f'Failed to play event alert audio for channel: {channel.name} (ID: {channel.id})', exc_info=ex )

    async def _perform_event_alerts( self, event_prefix: str, time_till_event: timedelta ):
        channels = ( self.bot.get_channel( cid ) for cid in self.diablo_voice_channel_ids )
        channels = ( c for c in channels if isinstance( c, discord.VoiceChannel ) and len( c.members ) > 0 and not all( m.bot for m in c.members ) )
        channels = list( channels )

        if len( channels ) == 0:
            return

        time: List[ str ] = []

        total_seconds = time_till_event.total_seconds()

        if total_seconds <= 60:
            time_text = 'less than 1 minute'
        else:
            hours = int( total_seconds / 60 / 60 )
            total_seconds -= hours * 60 * 60
            if hours != 0:
                time.append( f'{hours} hours' )

            minutes = int( total_seconds / 60 )
            total_seconds -= minutes * 60
            if minutes != 0:
                time.append( f'{minutes} minutes' )

            seconds = int( total_seconds )
            if seconds != 0:
                time.append( f'{seconds} seconds' )

            time_text = ' '.join( time )

        time_till_event_text = f'{event_prefix} {time_text}'

        LOG.info( f'Event alert text: {time_till_event_text}' )
        audio_content = await self.tts.generate_tts( time_till_event_text, language_code='en-US', voice_name='en-US-Neural2-C' )

        await asyncio.gather( *( self._perform_event_alert_for_channel( c, audio_content ) for c in channels ), return_exceptions=True )

    def _should_alert_event( self, now: datetime, event_time: datetime, last_alert_time: datetime, intervals: List[ timedelta ] ) -> bool:
        if now >= event_time:
            return False

        for interval in sorted( intervals ):
            alert_time = event_time - interval
            if now >= alert_time and last_alert_time < alert_time:
                return True

        return False

    def _get_event_time( self, now: datetime, timestamp: int, expected: int ) -> datetime:
        timestamp_date = datetime.utcfromtimestamp( timestamp )
        if timestamp_date < now:
            return datetime.utcfromtimestamp( expected )
        else:
            return timestamp_date

    async def cog_unload( self ):
        self.events_checker.cancel()

    @commands.Cog.listener()
    async def on_guild_join( self, guild: discord.Guild ):
        self._check_guild_for_diablo_voice_channel( guild )

    @tasks.loop( minutes=1 )
    async def events_checker( self ):
        LOG.info( 'Checking for Diablo events' )

        try:
            events = await get_diablo_events()
        except Exception as ex:
            LOG.warning( f'Failed to retrieve Diablo events', exc_info=ex )
            return

        force_alert = self.last_events is None
        now = datetime.utcnow()

        if self.last_events:
            if events.boss.timestamp != self.last_events.boss.timestamp or events.boss.expected != self.last_events.boss.expected:
                LOG.info( f'Resetting last boss alert time: {self.last_events.boss} -> {events.boss}' )
                self.last_boss_alert = datetime.min

            if events.legion.timestamp != self.last_events.legion.timestamp or events.legion.expected != self.last_events.legion.expected:
                LOG.info( f'Resetting last legion alert time: {self.last_events.legion} -> {events.legion}' )
                self.last_legion_alert = datetime.min

            if events.helltide.timestamp != self.last_events.helltide.timestamp:
                LOG.info( f'Resetting last helltide alert time: {self.last_events.helltide} -> {events.helltide}' )
                self.last_helltide_alert = datetime.min

        boss_time = self._get_event_time( now, events.boss.timestamp, events.boss.expected )
        if force_alert or self._should_alert_event( now, boss_time, self.last_boss_alert, BOSS_ALERT_INTERVALS ):
            LOG.info( f'Boss event alert interval passed, performing event alert for {events.boss} at {boss_time}' )
            self.last_boss_alert = now
            await self._perform_event_alerts( f'{events.boss.expectedName} spawning in {events.boss.territory} {events.boss.zone} in', boss_time - now )

        legion_time = self._get_event_time( now, events.legion.timestamp, events.legion.expected )
        if force_alert or self._should_alert_event( now, legion_time, self.last_legion_alert, LEGION_ALERT_INTERVALS ):
            LOG.info( f'Legion event alert interval passed, performing event alert for {events.legion} at {legion_time}' )
            self.last_legion_alert = now
            await self._perform_event_alerts( f'Legions are gathering in {events.legion.territory} {events.legion.zone} in', legion_time - now )

        helltide_time = self._get_event_time( now, events.helltide.timestamp, events.helltide.timestamp + ( 2 * 60 + 15 ) * 60 )
        if force_alert or self._should_alert_event( now, helltide_time, self.last_helltide_alert, HELLTIDE_ALERT_INTERVALS ):
            LOG.info( f'Helltide event alert interval passed, performing event alert for {events.helltide} at {helltide_time}' )
            self.last_helltide_alert = now
            await self._perform_event_alerts( f'The Helltide will rise in', helltide_time - now )

        self.last_events = events

    @events_checker.before_loop
    async def before_events_checker( self ):
        await self.bot.wait_until_ready()

        for guild in self.bot.guilds:
            self._check_guild_for_diablo_voice_channel( guild )