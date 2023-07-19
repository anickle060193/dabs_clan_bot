import { Client, Events, GatewayIntentBits } from 'discord.js';

import 'dotenv/config';

import { registerIntroducer } from './introducer';

const DISCORD_BOT_TOKEN = process.env[ 'DISCORD_BOT_TOKEN' ];
if( !DISCORD_BOT_TOKEN )
{
  throw new Error( 'DISCORD_BOT_TOKEN not set.' );
}

const client = new Client( {
  intents: [ GatewayIntentBits.Guilds, GatewayIntentBits.GuildVoiceStates ],
} );

client.once( Events.ClientReady, ( c ) =>
{
  console.info( 'Ready! Logged in as:', c.user.tag );
} );

// client.on( Events.Debug, ( m ) => console.debug( m ) );
client.on( Events.Warn, ( m ) => console.warn( m ) );
client.on( Events.Error, ( m ) => console.error( m ) );

registerIntroducer( client );

void client.login( DISCORD_BOT_TOKEN );

process.on( 'exit', () =>
{
  console.info( 'Destroying client...' );
  client.destroy();
} );
