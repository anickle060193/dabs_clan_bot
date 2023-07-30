import argparse
import asyncio

from pathlib import Path
from typing import List, NamedTuple

from consts import ELIXIR_ALERT_SOUNDS_DIR, INTRO_SOUNDS_DIR, WELCOME_SOUNDS_DIR
from tts import TTS

class TtsConfig( NamedTuple ):
    path: Path
    text: str
    language_code: str
    voice_name: str
    pitch: float | None = None
    speed: float | None = None

DEFAULT_INTROS: List[ TtsConfig ] = [
    TtsConfig(
        path = INTRO_SOUNDS_DIR / 'default.mp3',
        text = 'Someone has joined the chat',
        language_code='en-US',
        voice_name='en-US-Neural2-C',
    ),
    TtsConfig(
        path = WELCOME_SOUNDS_DIR / 'default.mp3',
        text = 'Welcome to the chat',
        language_code='en-US',
        voice_name='en-US-Wavenet-C',
    ),
]

CUSTOM_INTROS: List[ TtsConfig ] = [
    TtsConfig(
        path = INTRO_SOUNDS_DIR / '429914580592885771.mp3',
        text = 'Shini has joined the chat',
        language_code='ja-JP',
        voice_name='ja-JP-Wavenet-A',
        pitch=4,
    ),
    TtsConfig(
        path = WELCOME_SOUNDS_DIR / '429914580592885771.mp3',
        text = 'Welcome Shini-chan to the chat!',
        language_code='ja-JP',
        voice_name='ja-JP-Wavenet-A',
        pitch=3.5,
    ),
]

ELIXIR_ALERTS: List[ TtsConfig ] = [
    TtsConfig(
        path = ELIXIR_ALERT_SOUNDS_DIR / '1.mp3',
        text = 'Don\'t forget to pop a potion!',
        language_code='en-US',
        voice_name='en-US-Neural2-C',
        speed=1.0,
    ),
    TtsConfig(
        path = ELIXIR_ALERT_SOUNDS_DIR / '2.mp3',
        text = 'Don\'t forget to pop a potion!',
        language_code='es-US',
        voice_name='es-US-Neural2-A',
        speed=1.0,
    ),
    TtsConfig(
        path = ELIXIR_ALERT_SOUNDS_DIR / '3.mp3',
        text = 'Don\'t forget to pop a potion!',
        language_code='en-AU',
        voice_name='en-AU-Neural2-A',
        speed=1.25,
    ),
    TtsConfig(
        path = ELIXIR_ALERT_SOUNDS_DIR / '4.mp3',
        text = 'Don\'t forget to pop a potion!',
        language_code='en-GB',
        voice_name='en-GB-Neural2-D',
        speed=1.25,
    ),
    TtsConfig(
        path = ELIXIR_ALERT_SOUNDS_DIR / '5.mp3',
        text = 'Don\'t forget to pop a potion!',
        language_code='ja-JP',
        voice_name='ja-JP-Wavenet-A',
        speed=1.5,
    ),
]

async def generate_tts_mp3s( tts: TTS, tts_configs: List[ TtsConfig ] ):
    for tts_config in tts_configs:
        print( 'Generating', tts_config.path )
        audio_content = await tts.generate_tts(
            text=tts_config.text,
            language_code=tts_config.language_code,
            voice_name=tts_config.voice_name,
            pitch=tts_config.pitch,
            speed=tts_config.speed,
        )

        tts_config.path.write_bytes( audio_content )

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument( '--default-intros', action='store_true' )
    parser.add_argument( '--custom-intros', action='store_true' )
    parser.add_argument( '--elixir-alerts', action='store_true' )
    parser.add_argument( '--all', action='store_true' )
    args = parser.parse_args()

    tts = TTS()

    if args.default_intros or args.all:
        await generate_tts_mp3s( tts, DEFAULT_INTROS )

    if args.custom_intros or args.all:
        await generate_tts_mp3s( tts, CUSTOM_INTROS )

    if args.elixir_alerts or args.all:
        await generate_tts_mp3s( tts, ELIXIR_ALERTS )

if __name__ == '__main__':
    asyncio.run( main() )