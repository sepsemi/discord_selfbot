import uvloop
import asyncio
import logging
import msgspec
import datetime

# Set the loop policy to be uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# Define json_function alias
to_json = msgspec.json.encode
from_json = msgspec.json.decode

DISCORD_EPOCH = 1420070400000

def get_new_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop

def yield_token(path):
    with open(path) as fp:
        for line in fp.readlines():
            yield line.rstrip()

def minutes_elapsed_timestamp(value):
    now = datetime.datetime.now(datetime.timezone.utc)
    elasped = now - datetime.timedelta(minutes=value)
    return round(elasped.timestamp() * 1000)

def snowflake_time(id):
    timestamp = ((id >> 22) + DISCORD_EPOCH) / 1000
    return datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
