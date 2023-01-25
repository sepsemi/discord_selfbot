import aiohttp
from .utils import from_json, to_json
from urllib.parse import quote as _uriquote


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

    def __init__(self, loop, token, device):
        self.loop = loop
        self.token = token
        self.device = device
        connector = aiohttp.TCPConnector(force_close=True)
        self.__session = aiohttp.ClientSession(loop=loop, connector=connector)

    async def make_request(self, method, url, kwargs):
        method = method.lower()
        func = getattr(self.__session, method)

        result = await func(url, **kwargs)
        return result

    async def request(self, route, **kwargs):
        method = route.method
        url = route.url

        # header creation
        headers = {
            'useragent': self.device['browser_user_agent'],
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
