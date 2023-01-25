import os
import sys
import msgspec
import datetime

DISCORD_EPOCH = 1420070400000

# Define json_function alias
to_json = msgspec.json.encode
from_json = msgspec.json.decode

def minutes_elapsed_timestamp(value):
    now = datetime.datetime.now(datetime.timezone.utc)
    elasped = now - datetime.timedelta(minutes=value)
    return round(elasped.timestamp() * 1000)

def snowflake_time(id):
    timestamp = ((id >> 22) + DISCORD_EPOCH) / 1000
    return datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)


