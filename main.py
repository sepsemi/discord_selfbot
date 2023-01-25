import logging
import asyncio
import uvloop

import datetime

import dlib


logger = logging.getLogger('dlib')

logger.setLevel(logging.INFO)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter(
    '[%(asctime)s][%(levelname)s] %(name)s - %(message)s'))
logger.addHandler(sh)


def yield_token(path):
    with open(path) as fp:
        for line in fp.readlines():
            yield line.rstrip()


class Client(dlib.Client):

    async def on_ready(self):
        ts = datetime.datetime.now()
        print('[{}] ready: user.id={}, user={}'.format(
            ts, self.user.id, self.user))

    async def on_new_user(self, ctx):
        ts = datetime.datetime.now()
        print('[{}] new user: id={}, user={}'.format(ts, ctx.id, ctx))

    async def on_message(self, ctx):
        if self.user.id == ctx.author.id:
            print("me")
            await self.delete_message(ctx.channel.id, ctx.id)

        ts = datetime.datetime.now()
        print('[{}] send: id={}, channel.id={}, content={}'.format(
            ts, ctx.id, ctx.channel.id, ctx.content))

    async def on_message_delete(self, ctx):
        ts = datetime.datetime.now()
        print('[{}] delete: id={}, channel.id={}, content={}'.format(
            ts, ctx.id, ctx.channel.id, ctx.content))

    async def on_message_edit(self, before, after):
        ts = datetime.datetime.now()
        print('[{}] edit: id={}, channel.id={}, before={}, after={}'.format(
            ts, before.id, before.channel.id, before.content, after.content))


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
