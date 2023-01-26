import toml
import logging
import asyncio
import uvloop
from datetime import datetime

from dlib import Client, run_clients, logger

from src.automation import background_delete, background_change_username
from src.logger import Logger, MessageLogger

logger('info')

with open('etc/config.toml') as fp:
    config = toml.load(fp)

def yield_token(path):
    with open(path) as fp:
        for line in fp.readlines():
            yield line.rstrip()

class Client(Client):

    async def on_ready(self):
        ts = datetime.now()
        print('[{}][{}] ready: user.id={}, user={}'.format(
            ts, self.id, self.user.id, self.user))

        if config['settings']['automation']['delete']:
            if self.user.id in config['settings']['automation']['user_ids']:
                self.loop.create_task(background_delete(self))


        if config['settings']['automation']['change_username']:
            if self.user.id in config['settings']['automation']['user_ids']:
                self.loop.create_task(background_change_username(self))

    async def on_new_user(self, ctx):
        Logger(self).new_user(ctx)

    async def on_message(self, ctx):
        MessageLogger(self).send(ctx)

    async def on_message_delete(self, ctx):
        MessageLogger(self).delete(ctx)

    async def on_message_edit(self, before, after):
        MessageLogger(self).edit(before, after)

clients = []
for token in yield_token('etc/tokens.txt'):
    client = Client(token=token)
    clients.append(client)

print('subscribed {} clients'.format(len(clients)))
run_clients(*clients, reconnect=True)

