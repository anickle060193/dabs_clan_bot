from pathlib import Path

ROOT_DIR = Path( __file__ ).parent

LOGS_DIR = ROOT_DIR / 'logs'

SOUNDS_DIR = ROOT_DIR / 'sounds'

INTRO_SOUNDS_DIR = SOUNDS_DIR / 'intros'
WELCOME_SOUNDS_DIR = SOUNDS_DIR / 'welcomes'

ELIXIR_ALERT_SOUNDS_DIR = SOUNDS_DIR / 'elixir_alerts'

DIABLO_VOICE_CHANNEL_IDS = [
    1088975077179150479, # DABS Clan - diablo4-party-channel
    1128140152418611221, # anickle060193's Test Server - Other Channel
]