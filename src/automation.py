import toml
import asyncio
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
