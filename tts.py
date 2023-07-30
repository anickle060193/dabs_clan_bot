from google.cloud import texttospeech_v1 as gtts

class TTS:
    def __init__( self ) -> None:
        self.gtts_client = gtts.TextToSpeechAsyncClient()

    async def generate_tts( self, text: str, *, language_code: str = 'en-US', voice_name: str = 'en-US-Neural2-C', pitch: float | None = None, speed: float | None = None ) -> bytes:
        tts_input = gtts.SynthesisInput()
        tts_input.text = text

        audio_config = gtts.AudioConfig()
        audio_config.audio_encoding = gtts.AudioEncoding.MP3
        audio_config.effects_profile_id = [ 'headphone-class-device' ]
        if pitch is not None:
            audio_config.pitch = pitch
        if speed is not None:
            audio_config.speaking_rate = speed

        voice = gtts.VoiceSelectionParams()
        voice.language_code = language_code
        voice.name = voice_name

        request = gtts.SynthesizeSpeechRequest(
            input=tts_input,
            audio_config=audio_config,
            voice=voice,
        )

        response = await self.gtts_client.synthesize_speech( request=request )

        return response.audio_content

if __name__ == '__main__':
    import asyncio

    async def main():
        import argparse

        from pathlib import Path

        def _path_arg( arg: str ) -> Path:
            return Path( arg ).resolve().absolute()

        parser = argparse.ArgumentParser()
        text_group = parser.add_mutually_exclusive_group( required=True )
        text_group.add_argument( '--text' )
        text_group.add_argument( '--ssml' )
        parser.add_argument( '--lang', default='en-US' )
        parser.add_argument( '--voice', default='en-US-Wavenet-F' )
        parser.add_argument( '--pitch', type=float )
        parser.add_argument( '--speed', type=float )
        parser.add_argument( '--output', required=True, type=_path_arg )
        args = parser.parse_args()

        tts = TTS()

        audio_content = await tts.generate_tts( args.text, language_code=args.lang, voice_name=args.voice, pitch=args.pitch, speed=args.speed )

        args.output.write_bytes( audio_content )

    asyncio.run( main() )