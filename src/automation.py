import toml
import asyncio
import random
import string
from datetime import datetime, timedelta, timezone

with open('etc/config.toml') as fp:
    config = toml.load(fp)


def should_delete(timestamp):
    interval = config['settings']['automation']['delete_interval']

    now = datetime.now(tz=timezone.utc)
    diff_interval = timestamp + timedelta(seconds=interval)
    diff_interval_ignore = timestamp + timedelta(seconds=interval + 1)

    if diff_interval < now and diff_interval_ignore > now:
        return True

async def background_delete(client):

    while not client.is_closed:
        for message in client.cached_messages:
            if not client.user.id == message.author.id:
                continue

            if should_delete(message.created_at):
                print('trying to delete')
                await client.delete_message(message.channel.id, message.id)

        await asyncio.sleep(1)

async def background_change_username(client):
 
    password = config['settings']['password']
    interval = config['settings']['automation']['change_username_interval']
    prefix = config['settings']['automation']['change_username_prefix']

    while not client.is_closed:
        rand = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(32 - len(prefix)))
        username = prefix + rand

        # change the username every x interval
        await client.change_username(password, username) 

        print('changed username to: ', username)
        await asyncio.sleep(interval)

