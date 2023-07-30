import asyncio
import logging
import random

from datetime import datetime, timedelta
from typing import Dict

import discord

from discord.ext import tasks, commands

from consts import ELIXIR_ALERT_SOUNDS_DIR
from utils import join_voice_chat

LOG = logging.getLogger( __name__ )

DIABLO_VOICE_CHANNEL_IDS = [
    1088975077179150479, # DABS Clan - diablo4-party-channel
    1128140152418611221, # anickle060193's Test Server - Other Channel
]

AFTER_JOIN_ALERT_DELAY = timedelta( minutes=1 )
ALERT_INTERVAL = timedelta( minutes=15 )

class DiabloElixirAlerter( commands.Cog ):
    def __init__( self, bot: commands.Bot ) -> None:
        self.bot = bot
        self.next_alert_time: Dict[ int, datetime ] = {}

        self.elixir_alert.start()

    def _set_guild_next_alert_time( self, guild: discord.Guild ):
        for channel_id in DIABLO_VOICE_CHANNEL_IDS:
            if channel_id not in self.next_alert_time:
                channel = guild.get_channel( channel_id )
                if isinstance( channel, discord.VoiceChannel ):
                    LOG.info( f'Detected guild ({guild.name} - {guild.id}) with Diablo voice channel ({channel.name} - {channel.id}), adding next alert time' )
                    self.next_alert_time[ channel_id ] = datetime.min
                    return

        LOG.info( f'Guild ({guild.name} - {guild.id}) has not Diablo voice channel' )

    async def cog_unload( self ):
        self.elixir_alert.cancel()

    @commands.Cog.listener()
    async def on_guild_join( self, guild: discord.Guild ):
        self._set_guild_next_alert_time( guild )

    @tasks.loop( minutes=1 )
    async def elixir_alert( self ):
        await asyncio.gather( *( self._perform_elixir_alert_safe( cid ) for cid in self.next_alert_time.keys() ), return_exceptions=True )

    @elixir_alert.before_loop
    async def before_elixir_alert( self ):
        await self.bot.wait_until_ready()

        for guild in self.bot.guilds:
            self._set_guild_next_alert_time( guild )

    @commands.Cog.listener()
    async def on_voice_state_update( self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState ):
        if member.bot:
            return
        if before.channel == after.channel:
            return

        if before.channel and before.channel.id in self.next_alert_time:
            await self._perform_elixir_alert_safe( before.channel.id )
        elif after.channel and after.channel.id in self.next_alert_time:
            await self._perform_elixir_alert_safe( after.channel.id, new_member=True )

    async def _perform_elixir_alert_safe( self, channel_id: int, new_member: bool = False ):
        try:
            await self._perform_elixir_alert( channel_id, new_member=new_member )
        except Exception as ex:
            LOG.error( f'Failed to perform elixir alert for channel: {channel_id}', exc_info=ex )

    async def _perform_elixir_alert( self, channel_id: int, new_member: bool = False ):
        LOG.debug( f'Performing elixir alert: {channel_id}' )

        if channel_id not in self.next_alert_time:
            LOG.warning( f'Unknown channel ID: {channel_id}' )
            return

        channel = self.bot.get_channel( channel_id )
        if not isinstance( channel, ( discord.VoiceChannel, discord.StageChannel ) ):
            if channel:
                LOG.warning( f'Channel is not a voice channel: {channel_id}' )
            else:
                LOG.warning( f'Could not find voice channel: {channel_id}' )
            return

        if len( channel.members ) == 0 or all( m.bot for m in channel.members ):
            if self.next_alert_time[ channel_id ] != datetime.min:
                LOG.info( f'Empty channel detected: {channel_id}' )
                self.next_alert_time[ channel_id ] = datetime.min
            return

        if new_member or self.next_alert_time[ channel_id ] == datetime.min:
            LOG.info( f'First member join detected: {channel_id}' )
            self.next_alert_time[ channel_id ] = datetime.now() + AFTER_JOIN_ALERT_DELAY
            return

        now = datetime.now()
        if self.next_alert_time[ channel_id ] > now:
            LOG.debug( f'Waiting for alert time: {channel_id} - {( self.next_alert_time[ channel_id ] - now )} remaining' )
            return

        LOG.info( f'Playing elixir alert: {channel_id}' )
        self.next_alert_time[ channel_id ] = now + ALERT_INTERVAL

        voice_client = await join_voice_chat( self.bot, channel )

        alert_sound_mp3_path = random.choice( list( ELIXIR_ALERT_SOUNDS_DIR.glob( '*.mp3' ) ) )

        def after_play( ex: Exception | None ):
            if ex:
                LOG.error( f'Failed to play elixir alert: {channel_id} - {alert_sound_mp3_path}', exc_info=ex )

        source = discord.PCMVolumeTransformer( discord.FFmpegPCMAudio( source=str( alert_sound_mp3_path ) ) )
        voice_client.play( source, after=after_play )