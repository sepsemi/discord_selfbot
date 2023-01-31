import toml
import asyncio
from datetime import datetime

from dlib import (
    Client, 
    logger,
    run_clients, 
    yield_token
)

from src.automation import (
    background_delete,
    background_change_username
)

from src.logger import (
    Logger,
    MessageLogger
)

from src.processor import CommandProcessor

from src.database import DiscordDatabase

logger('info')

with open('etc/config.toml') as fp:
    config = toml.load(fp)

database = None

class Client(Client):

    database = database
    
    async def on_ready(self):
        ts = datetime.now()
        print('[{}][{}] ready: user.id={}, user={}'.format(ts, self.id, self.user.id, self.user))
       
        tasks = []
        for user in self.users:
            tasks.append(self.loop.create_task(database.new_user(user)))

        await asyncio.wait(tasks)

        # regiser command processor
        #self.processor = CommandProcessor(loop=self.loop, state=self._connection)
        self.processor = CommandProcessor()

    async def on_new_user(self, ctx):
        Logger(self).new_user(ctx)
        await database.new_user(ctx)

    async def on_message(self, ctx):
        MessageLogger(self).send(ctx)
        await database.message_create(ctx) 
           
        if self.is_ready:
        # process the command acordingly
            self.processor.process(ctx)

    async def on_message_delete(self, ctx):
        MessageLogger(self).delete(ctx)
        await database.message_delete(ctx) 

    async def on_message_edit(self, before, after):
        MessageLogger(self).edit(before, after)

async def main(loop):
    global database
        
    database = DiscordDatabase(loop=loop, **config['database'])
    await database.connect()

    clients = []
    for token in yield_token('etc/tokens.txt'):
        client = Client(loop=loop, token=token)
        clients.append(loop.create_task(client.run()))
    
    await asyncio.wait(clients)


loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(main(loop))


