import fs from 'node:fs';
import path from 'node:path';

import { Client, GuildMember } from 'discord.js';
import { AudioPlayerStatus, createAudioPlayer, createAudioResource, joinVoiceChannel } from '@discordjs/voice';

import { ttsClient } from './tts';

const SOUNDS_DIRECTORY = 'sounds';

async function getIntroductionSound( member: GuildMember ): Promise<string>
{
  const name = ( member.nickname ?? member.displayName ).replace( /\d*$/, '' );

  const filename = path.resolve( path.join( SOUNDS_DIRECTORY, member.id + '.opus' ) );

  try
  {
    if( ( await fs.promises.stat( filename ) ).isFile() )
    {
      return filename;
    }
  }
  catch( e )
  {
    console.log( 'Introduction does not exist for:', member.displayName );
  }

  try
  {
    const [ response ] = await ttsClient.synthesizeSpeech( {
      input: {
        text: `${name} has joined the chat`,
      },
      voice: {
        languageCode: 'en-US',
        name: 'en-US-Wavenet-F',
      },
      audioConfig: {
        audioEncoding: 'OGG_OPUS',
        effectsProfileId: [
          'headphone-class-device',
        ],
      },
    } );

    if( response.audioContent === null
      || response.audioContent === undefined )
    {
      throw new Error( 'TTS response has no audio content.' );
    }

    await fs.promises.writeFile( filename, response.audioContent, { encoding: 'binary' } );

    return filename;
  }
  catch( e )
  {
    console.warn( 'Failed to generate TTS introduction:', e );
  }

  return path.resolve( path.join( SOUNDS_DIRECTORY, 'default.opus' ) );
}

export function registerIntroducer( client: Client )
{
  client.on( 'voiceStateUpdate', async ( oldState, newState ) =>
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

    const soundFilename = await getIntroductionSound( newState.member );

    const player = createAudioPlayer();

    player.on( 'error', ( error ) =>
    {
      console.error( 'Failed to play introduction:', soundFilename, error );
    } );

    const subscription = voiceConnection.subscribe( player );
    if( !subscription )
    {
      console.warn( 'Failed to subscribe voice connection to player.' );
      return;
    }

    console.info( 'Playing introduction:', soundFilename );
    const resource = createAudioResource( soundFilename );
    player.play( resource );

    player.once( AudioPlayerStatus.Idle, () =>
    {
      console.info( 'Done playing introduction:', soundFilename );
      player.stop();
      subscription.unsubscribe();
    } );
  } );
}
