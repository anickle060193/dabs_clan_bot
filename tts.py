from google.cloud import texttospeech_v1 as gtts

class TTS:
    def __init__( self ) -> None:
        self.gtts_client = gtts.TextToSpeechAsyncClient()

    async def generate_tts( self, text: str, *, language_code='en-US', voice_name='en-US-Wavenet-F', pitch=None ) -> bytes:
        tts_input = gtts.SynthesisInput()
        tts_input.text = text

        audio_config = gtts.AudioConfig()
        audio_config.audio_encoding = 'MP3'
        audio_config.effects_profile_id = [ 'headphone-class-device' ]
        audio_config.pitch = pitch

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
        parser.add_argument( '--text', '-t', required=True )
        parser.add_argument( '--lang', '-l', default='en-US' )
        parser.add_argument( '--voice', '-v', default='en-US-Wavenet-F' )
        parser.add_argument( '--pitch', '-p', type=float )
        parser.add_argument( '--output', '-o', required=True, type=_path_arg )
        args = parser.parse_args()

        tts = TTS()

        audio_content = await tts.generate_tts( args.text, language_code=args.lang, voice_name=args.voice, pitch=args.pitch )

        args.output.write_bytes( audio_content )

    asyncio.run( main() )