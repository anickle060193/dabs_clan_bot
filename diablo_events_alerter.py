import asyncio
import io
import logging

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Sequence

import discord

from discord.ext import tasks, commands

from constants import DIABLO_VOICE_CHANNEL_IDS
from diablo_events import HELLTIDE_ZONE_NAMES, DiabloBossEvent, DiabloEvents, DiabloHelltideEvent, DiabloLegionEvent, get_diablo_events
from tts import TTS
from utils import join_voice_chat, play_voice_channel_audio

LOG = logging.getLogger( __name__ )

BOSS_ALERT_INTERVALS = [
    timedelta( minutes=60 ),
    timedelta( minutes=30 ),
    timedelta( minutes=15 ),
    timedelta( minutes=5 ),
    timedelta( minutes=1 ),
]

LEGION_ALERT_INTERVALS = [
    timedelta( minutes=3, seconds=30 ),
]

HELLTIDE_ALERT_INTERVALS = [
    timedelta( minutes=1 ),
]

DiabloEvent = DiabloBossEvent | DiabloLegionEvent | DiabloHelltideEvent

@dataclass
class DiabloEventAlert:
    event: DiabloEvent
    text: str
    event_time: datetime
    alert_time: datetime

def get_event_time( now: datetime, timestamp: int, expected: int ) -> datetime:
    timestamp_date = datetime.fromtimestamp( timestamp, timezone.utc )
    if timestamp_date < now:
        return datetime.fromtimestamp( expected, tz=timezone.utc )
    else:
        return timestamp_date

def diablo_events_to_alerts( now: datetime, last_alert_time: datetime, events: DiabloEvents ) -> list[ DiabloEventAlert ]:
    alerts: list[ DiabloEventAlert ] = []

    boss_time = get_event_time( now, events.boss.timestamp, events.boss.expected )
    boss_text = f'{events.boss.expectedName} spawning in {events.boss.territory} {events.boss.zone} in'

    legion_time = get_event_time( now, events.legion.timestamp, events.legion.expected )
    legion_text = f'Legions are gathering in {events.legion.territory} {events.legion.zone} in'

    helltide_time = get_event_time( now, events.helltide.timestamp, events.helltide.timestamp + ( 2 * 60 + 15 ) * 60 )
    helltide_zone = HELLTIDE_ZONE_NAMES.get( events.helltide.zone, 'Sanctuary' )
    helltide_text = f'The Helltide will rise in {helltide_zone} in'

    alert_configs: Sequence[ tuple[ DiabloEvent, datetime, str, list[ timedelta ] ] ] = (
        ( events.boss, boss_time, boss_text, BOSS_ALERT_INTERVALS ),
        ( events.legion, legion_time, legion_text, LEGION_ALERT_INTERVALS ),
        ( events.helltide, helltide_time, helltide_text, HELLTIDE_ALERT_INTERVALS ),
    )

    for event, event_time, event_text, alert_intervals in alert_configs:
        for interval in sorted( alert_intervals ):
            alert_time = event_time - interval
            if alert_time < last_alert_time:
                continue

            alerts.append( DiabloEventAlert(
                event=event,
                text=event_text,
                event_time=event_time,
                alert_time=event_time - interval,
            ) )
            break

    sorted_alerts = sorted( alerts, key=lambda a: a.alert_time )

    return sorted_alerts

def format_event_time_till( time_till_event: timedelta ) -> str:
    time: list[ str ] = []

    total_seconds = time_till_event.total_seconds() - 5

    if total_seconds <= 60:
        return 'less than 1 minute'

    hours = int( total_seconds / 60 / 60 )
    total_seconds -= hours * 60 * 60
    if hours != 0:
        time.append( f'{hours} hours' )

    minutes = int( total_seconds / 60 )
    total_seconds -= minutes * 60
    if minutes != 0:
        time.append( f'{minutes} minutes' )

    if hours == 0 and minutes < 30:
        seconds = int( total_seconds )
        if seconds != 0:
            time.append( f'{seconds} seconds' )

    return ' '.join( time )

class DiabloEventsAlerter( commands.Cog ):
    def __init__( self, bot: commands.Bot, tts: TTS ) -> None:
        self.bot = bot
        self.tts = tts

        self.diablo_voice_channel_ids: set[ int ] = set()

        self.events: DiabloEvents | None = None
        self.alerts: list[ DiabloEventAlert ] | None = None
        self.last_alert_time: datetime = datetime.min.replace( tzinfo=timezone.utc )
        self.first_alert = True

        self.events_retrieved = asyncio.Event()

        self.events_retriever.start()
        self.events_alerter.start()

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

        time_till_text = format_event_time_till( time_till_event )
        time_till_event_text = f'{event_prefix} {time_till_text}'

        LOG.info( f'Event alert text: {time_till_event_text}' )
        audio_content = await self.tts.generate_tts( time_till_event_text, language_code='en-US', voice_name='en-US-Neural2-C' )

        await asyncio.gather( *( self._perform_event_alert_for_channel( c, audio_content ) for c in channels ), return_exceptions=True )

    async def cog_unload( self ):
        self.events_retriever.cancel()
        self.events_alerter.cancel()

    @commands.Cog.listener()
    async def on_guild_join( self, guild: discord.Guild ):
        self._check_guild_for_diablo_voice_channel( guild )

    @commands.Cog.listener()
    async def on_ready( self ):
        for guild in self.bot.guilds:
            self._check_guild_for_diablo_voice_channel( guild )

    @tasks.loop( seconds=10 )
    async def events_alerter( self ):
        if not self.events:
            LOG.warning( 'No Diablo event set' )
            return

        now = datetime.now( tz=timezone.utc )

        LOG.debug( f'Checking for Diablo event alerts: {now}' )

        alerts = diablo_events_to_alerts( now, self.last_alert_time, self.events )

        for alert in alerts:
            if self.first_alert or alert.alert_time <= now:
                LOG.info( f'Performing event alert: now={now}, alert={alert}' )
                await self._perform_event_alerts( alert.text, alert.event_time - now )

        self.last_alert_time = now
        self.first_alert = False

    @events_alerter.before_loop
    async def before_events_alerter( self ):
        await self.bot.wait_until_ready()

        await self.events_retrieved.wait()

    @tasks.loop( minutes=1 )
    async def events_retriever( self ):
        LOG.debug( f'Retrieving Diablo events: {datetime.now( tz=timezone.utc )}' )

        try:
            events = await get_diablo_events()
            if events != self.events:
                LOG.debug( f'New Diablo events retrieved: {events}' )
                self.events = events
                self.events_retrieved.set()
        except Exception as ex:
            LOG.warning( f'Failed to retrieve Diablo events', exc_info=ex )

    @events_retriever.before_loop
    async def before_events_retriever( self ):
        await self.bot.wait_until_ready()