import toml
import logging
import asyncio
import uvloop
from datetime import datetime, timedelta, timezone

import dlib


logger = logging.getLogger('dlib')

logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter(
    '[%(asctime)s][%(levelname)s] %(name)s - %(message)s'))
logger.addHandler(sh)

with open('etc/config.toml') as fp:
    config = toml.load(fp)

def yield_token(path):
    with open(path) as fp:
        for line in fp.readlines():
            yield line.rstrip()

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


class Client(dlib.Client):

    async def on_ready(self):
        ts = datetime.now()
        print('[{}][{}] ready: user.id={}, user={}'.format(
            ts, self.id, self.user.id, self.user))

        if config['settings']['automation']['delete']:
            if self.user.id in config['settings']['automation']['user_ids']:
                self.loop.create_task(background_delete(self))

    async def on_new_user(self, ctx):
        ts = datetime.now()
        print('[{}][{}] new user: id={}, user={}'.format(
            ts, self.id, ctx.id, ctx))

    async def on_message(self, ctx):
        if self.user.id == ctx.author.id:
            await self.delete_message(ctx.channel.id, ctx.id)

        ts = datetime.now()
        print('[{}][{}] send: id={}, channel.id={}, content={}'.format(
            ts, self.id, ctx.id, ctx.channel.id, ctx.content))

    async def on_message_delete(self, ctx):
        ts = datetime.now()
        print('[{}][{}] delete: id={}, channel.id={}, content={}'.format(
            ts, self.id, ctx.id, ctx.channel.id, ctx.content))

    async def on_message_edit(self, before, after):
        ts = datetime.now()
        print('[{}][{} edit: id={}, channel.id={}, before={}, after={}'.format(
            ts, self.id. before.id, before.channel.id, before.content, after.content))


async def main(loop):
    clients = []
    for token in yield_token('etc/tokens.txt'):
        client = Client(loop=loop, token=token)
        clients.append(loop.create_task(client.run()))

    print('subscribed {} clients'.format(len(clients)))

    await asyncio.wait(clients)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(main(loop))
