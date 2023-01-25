import toml
import logging
import asyncio
import uvloop
from datetime import datetime

import dlib

from src.automation import background_delete
from src.logger import Logger, MessageLogger


logger = logging.getLogger('dlib')

logger.setLevel(logging.INFO)
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


class Client(dlib.Client):

    async def on_ready(self):
        ts = datetime.now()
        print('[{}][{}] ready: user.id={}, user={}'.format(
            ts, self.id, self.user.id, self.user))

        if config['settings']['automation']['delete']:
            if self.user.id in config['settings']['automation']['user_ids']:
                self.loop.create_task(background_delete(self))

    async def on_new_user(self, ctx):
        Logger(self).new_user(ctx)

    async def on_message(self, ctx):

        self._closed = True
        MessageLogger(self).send(ctx)

    async def on_message_delete(self, ctx):
        MessageLogger(self).delete(ctx)

    async def on_message_edit(self, before, after):
        MessageLogger(self).edit(before, after)


async def main(loop):
    clients = []
    for token in yield_token('etc/tokens.txt'):
        client = Client(loop=loop, token=token)
        clients.append(loop.create_task(client.run()))

    print('subscribed {} clients'.format(len(clients)))

    await asyncio.wait(clients)

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(main(loop))
