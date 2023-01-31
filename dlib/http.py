import time
import logging
import random
import asyncio
import aiohttp

from .utils import from_json, to_json
from urllib.parse import quote as _uriquote

_log = logging.getLogger(__name__)


class RateLimit:
    INCREASE_WINDOW = 0.1

    def __init__(self):
        self._rand = random.Random()
        self._current = float('inf')
        self._timestamp = None
    
    @property
    def limited(self):
        # check if we are limited or not
        if self._timestamp is not None and time.time() - self._timestamp >= self._current:
            return False

        return True

    def set(self, seconds):
        if self._timestamp is None:
            self._timestamp = time.time()
            self._current = seconds
        
        self.increase(seconds)

    def increase(self, seconds):
        self._current += seconds
     
    @property
    def limited_for(self):
        return self._current

class Route:
    BASE = 'https://discord.com/api/v10'

    def __init__(self, method, path, **parameters):
        self.method = method
        self.path = path

        url = self.BASE + self.path

        if parameters:
            url = url.format_map({k: _uriquote(v) if isinstance(
                v, str) else v for k, v in parameters.items()})
        self.url = url


class HTTPClient:
    DNS_CACHE_TTL = 300
    MAX_SIZE_POOL = 10
    ESTABLISHED_CONNECTION_TIMEOUT = 1800.0

    def __init__(self, loop, token, device):
        self.loop = loop
        self.token = token
        self.id = token[-18:]
        self.device = device
        self.ratelimter = RateLimit()
        self.__session = self.get_aiohttp_session()

    def get_aiohttp_client_timeout(self):
        return aiohttp.ClientTimeout(
            total=None,
            connect=None,
            sock_read=None,
            sock_connect=self.ESTABLISHED_CONNECTION_TIMEOUT
        )

    def get_aiohttp_connector(self):
        return aiohttp.TCPConnector(
            loop=self.loop,
            ttl_dns_cache=self.DNS_CACHE_TTL,
            force_close=True,
            limit=self.MAX_SIZE_POOL
        )

    def get_aiohttp_session(self):
        return aiohttp.ClientSession(
            loop=self.loop, 
            connector=self.get_aiohttp_connector(),
            timeout=self.get_aiohttp_client_timeout()
        )

    async def close(self):
        await self.__session.close()
        

    async def make_request(self, method, url, kwargs):

        method = method.lower()
        func = getattr(self.__session, method)

        # run the loop until its no longer limited
        while True:

            response = await func(url, **kwargs)
            if not response.status in (200, 204, 429, 404):
                raise RuntimeError('Response not handled')

            # check if we are limited
            if response.status == 429:
                data = from_json(await response.text())  
                # we are limted so we set the time given 
                self.ratelimter.set(data['retry_after'])

            if not self.ratelimter.limited:
                return await response.text()
            
            # there is no reason to do anything, because we are limited

            _log.info('[{}] ratelimited: ratlimited for {} seconds'.format(self.id, self.ratelimter.limited_for))
            await asyncio.sleep(self.ratelimter.limited_for)


    async def request(self, route, **kwargs):
        method = route.method
        url = route.url

        # header creation
        headers = {
            'useragent': self.device.user_agent,
            'x-super-properties': self.device.x_super_properties,
            'authorization': self.token
        }

        if 'json' in kwargs:
            headers['Content-Type'] = 'application/json'
            kwargs['data'] = to_json(kwargs.pop('json'))

        kwargs['headers'] = headers

        # Do more later
        await self.make_request(method, url, kwargs)

    def delete_message(self, channel_id, message_id):
        route = Route('DELETE', '/channels/{channel_id}/messages/{message_id}',
                      channel_id=channel_id, message_id=message_id)
        return self.request(route)

    def change_username(self, password, username):
        payload = {
            'password': password,
            'username': username,
        }

        return self.request(Route('PATCH', '/users/@me'), json=payload)
