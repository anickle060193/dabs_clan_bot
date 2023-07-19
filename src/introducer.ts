import { Client } from 'discord.js';
import { AudioPlayerStatus, createAudioPlayer, createAudioResource, joinVoiceChannel } from '@discordjs/voice';

export function registerIntroducer( client: Client )
{
  client.on( 'voiceStateUpdate', ( oldState, newState ) =>
  {
    if( !newState.member )
    {
      return;
    }

    if( newState.member.user.bot )
    {
      return;
    }

    if( oldState.channel?.id === newState.channel?.id )
    {
      return;
    }

    if( !newState.channel )
    {
      return;
    }

    console.info( `${newState.member.user.tag} (ID: ${newState.member.id}) joined ${newState.guild.name} (ID: ${newState.guild.id}) - ${newState.channel.name} (ID:${newState.channel.id})` );

    const voiceChannel = newState.channel;

    const voiceConnection = joinVoiceChannel( {
      guildId: voiceChannel.guild.id,
      channelId: voiceChannel.id,
      adapterCreator: voiceChannel.guild.voiceAdapterCreator,
      selfDeaf: true,
      selfMute: false,
    } );

    const soundPath = 'sounds/default.mp3';

    const player = createAudioPlayer();

    player.on( 'error', ( error ) =>
    {
      console.error( 'Failed to play introduction:', soundPath, error );
    } );

    const subscription = voiceConnection.subscribe( player );
    if( !subscription )
    {
      console.warn( 'Failed to subscribe voice connection to player.' );
      return;
    }

    console.info( 'Playing introduction:', soundPath );
    const resource = createAudioResource( soundPath );
    player.play( resource );

    player.once( AudioPlayerStatus.Idle, () =>
    {
      console.info( 'Done playing introduction:', soundPath );
      player.stop();
      subscription.unsubscribe();
    } );
  } );
}
