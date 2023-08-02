from dataclasses import dataclass
from typing import Dict

import aiohttp

from jsonschema import validate

@dataclass
class DiabloBossEvent:
    name: str
    expectedName: str
    nextExpectedName: str
    timestamp: int
    expected: int
    nextExpected: int
    territory: str
    zone: str

@dataclass
class DiabloLegionEvent:
    timestamp: int
    expected: int
    nextExpected: int
    territory: str
    zone: str

@dataclass
class DiabloHelltideEvent:
    timestamp: int
    zone: str
    refresh: int

@dataclass
class DiabloEvents:
    boss: DiabloBossEvent
    legion: DiabloLegionEvent
    helltide: DiabloHelltideEvent

HELLTIDE_ZONE_NAMES: Dict[ str, str ] = {
  'kehj': 'Kehjistan',
  'hawe': 'Hawezar',
  'scos': 'Scosglen',
  'frac': 'Fractured Peaks',
  'step': 'Dry Steppes',
}

EVENTS_SCHEMA = {
    'type': 'object',
    'properties': {
        'boss': {
            'type': 'object',
            'properties': {
                'name': { 'type': 'string' },
                'expectedName': { 'type': 'string' },
                'nextExpectedName': { 'type': 'string' },
                'timestamp': { 'type': 'integer' },
                'expected': { 'type': 'integer' },
                'nextExpected': { 'type': 'integer' },
                'territory': { 'type': 'string' },
                'zone': { 'type': 'string' },
            },
            'required': [ 'name', 'expectedName', 'nextExpectedName', 'timestamp', 'expected', 'nextExpected', 'territory', 'zone' ]
        },
        'legion': {
            'type': 'object',
            'properties': {
                'timestamp': { 'type': 'integer' },
                'expected': { 'type': 'integer' },
                'nextExpected': { 'type': 'integer' },
                'territory': { 'type': 'string' },
                'zone': { 'type': 'string' },
            },
            'required': [ 'timestamp', 'expected', 'nextExpected', 'territory', 'zone' ]
        },
        'helltide': {
            'type': 'object',
            'properties': {
                'timstamp': { 'type': 'integer' },
                'zone': { 'type': 'string' },
                'refresh': { 'type': 'integer' },
            },
            'required': [ 'timestamp', 'zone', 'refresh' ],
        },
    },
    'required': [ 'boss', 'legion', 'helltide' ]
}

async def get_diablo_events() -> DiabloEvents:
    async with aiohttp.ClientSession() as session:
        async with session.get( 'https://d4armory.io/api/events/recent' ) as response:
            response.raise_for_status()

            data = await response.json()

    validate( data, EVENTS_SCHEMA )

    return DiabloEvents(
        boss=DiabloBossEvent(
            **data[ 'boss' ],
        ),
        legion=DiabloLegionEvent(
            **data[ 'legion' ],
        ),
        helltide=DiabloHelltideEvent(
            **data[ 'helltide' ],
        )
    )

if __name__ == '__main__':
    import asyncio

    from datetime import datetime

    async def main():
        events = await get_diablo_events()
        print( events )
        now = datetime.utcnow()
        print( 'Next Boss:', datetime.utcfromtimestamp( events.boss.timestamp ) - now, '/', datetime.utcfromtimestamp( events.boss.expected ) - now )
        print( 'Next Legion:', datetime.utcfromtimestamp( events.legion.timestamp ) - now, '/', datetime.utcfromtimestamp( events.legion.expected ) - now )
        print( 'Next Helltide:', datetime.utcfromtimestamp( events.helltide.timestamp ) - now, '/', datetime.utcfromtimestamp( events.helltide.timestamp + ( 2 * 60 + 15 ) * 60 ) - now )

    asyncio.run( main() )
