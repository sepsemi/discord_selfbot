import asyncio
from asyncpg import create_pool
from asyncpg.exceptions import (
    UniqueViolationError
)

class Database:
    
    def __init__(self, loop, **kwags):
        self.loop = loop
        self.pool = None
        
        self.host = kwags.get('host', '127.0.0.1')
        self.port = kwags.get('port', 5432)
        self.username = kwags.get('username', 'root')
        self.password = kwags.get('password', 'toor')
        self.database = kwags.get('database', None)

    def __str__(self):
        return 'destination=({self.host}:{self.port}), credentials=({self.username}, {self.password}), database={self.database}'.format(self=self)
        
    async def connect(self):
        pool = await create_pool(
            host=self.host,
            port=self.port,
            user=self.username,
            password=self.password,
            database=self.database
        )
        self.pool = pool

    async def insert(self, sql, *values):
        async with self.pool.acquire() as connection:
            try:
                return await connection.execute(sql, *values)
            except UniqueViolationError:
                return None

    async def select(self, sql, *values):
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                cursor = await connection.cursor(sql, *values)
                return await cursor.fetchrow()

    async def update(self, sql, *values):
        async with self.pool.acquire() as connection:
            return await connection.execute(sql, *values)


class DiscordDatabase(Database):

    def __init__(self, loop, **config):
        Database.__init__(self, loop, **config)

    def new_user(self, ctx):
        sql = """
            INSERT INTO users(id, username, discriminator, avatar, bot, public_flags)
            VALUES ($1, $2, $3, $4, $5, $6)
        """
        return self.insert(sql, ctx.id, ctx.username, ctx.discriminator, ctx.avatar, ctx.bot, ctx.public_flags)

    def message_create(self, ctx):    
        sql = """
            INSERT INTO messages(id, type, status, author_id, channel_id, content)
            VALUES ($1, $2, $3, $4, $5, $6)
        """ 
        return self.insert(sql, ctx.id, ctx.type, 0, ctx.author.id, ctx.channel.id, ctx.content)

    def message_delete(self, ctx):
        sql = """
            UPDATE messages SET status = 2
            WHERE id = $1 and channel_id = $2 and author_id = $3
        """
        return self.update(sql, ctx.id, ctx.channel.id, ctx.author.id)


