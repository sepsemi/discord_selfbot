import logging
import asyncio

from .http import HTTPClient
from .state import ConnectionState

from .utils import get_new_loop
from .device import create_devices
from .backoff import ExponentialBackoff

from .gateway import (
    _keep_alive_ref,
    DiscordWebSocket,
    ReconnectWebSocket
)

_log = logging.getLogger(__name__)

# Cannot run many clients need to fix
DEVICES = create_devices()

_keep_alive_ref.start()

def run_clients(client, *tokens, loop=None, reconnect=True):
    loop = loop if loop is not None else get_new_loop()

    tasks = set()
    for token in tokens:
        _client = client(token=token, loop=loop)
        tasks.add(loop.create_task(_client.run(reconnect)))

    try:
        _keep_alive_ref.start()
        # if the loop is none

        loop.run_until_complete(asyncio.wait(tasks))
    except KeyboardInterrupt:
        # Gracefull shutdown
        all_tasks = asyncio.gather(*asyncio.all_tasks(loop), return_exceptions=False)
        all_tasks.cancel()

        # Stop the keep_alive thread
        _keep_alive_ref.stop()
    finally:
        loop.close()

class Client:

    def __init__(self, loop=None, token=None, *hooks):
        self.loop = loop
        self.token = token
        self.id = token[:18]
        self._device = self._get_device()
        self._closed = False
        self.ws = None
        self._connection = self._get_connection()

    def _get_device(self):
        # check if we reused a device
        return DEVICES.pop(0)

    def _get_connection(self):
        state = ConnectionState(
            loop=self.loop,
            http=HTTPClient(self.loop, self.token, self._device),
            dispatch=self.dispatch,
        )
        state.id = self.id
        return state

    def _schedule_event(self, coro, event_name, *args, **kwargs):

        # Schedules the task
        return asyncio.create_task(coro(*args, **kwargs), name=event_name)

    def dispatch(self, event, *args, **kwargs):
        method = 'on_{}'.format(event)
        try:
            coro = getattr(self, method)
        except AttributeError:
            return None
        
        self._schedule_event(coro, method, *args, **kwargs)

    @property
    def is_closed(self):
        return self._closed

    def _set_reconnect_params(self, params, resume):
        params.update(
            sequence=self.ws.sequence,
            resume=resume,
            session=self.ws.session_id,
            gateway=self.ws.gateway,
        )
        _log.debug('[{}][{}]: set params to: {}'.format(self.__class__.__name__, self.id, params))

    async def connect(self, reconnect):
        backoff = ExponentialBackoff()
        # set this for every client started

        ws_params = {'initial': True} 
        while not self._closed or reconnect is True:
            try:
                self.ws = DiscordWebSocket(loop=self.loop, client=self, params=ws_params)
                ws_params['initial'] = False
                await self.ws.connect_and_poll()
            except ReconnectWebSocket as e:

                _log.debug('[{}][{}]: Got a request to {} the websocket.'.format(self.__class__.__name__, self.id, e.op))
                self._set_reconnect_params(ws_params, e.resume)
                if e.resume:
                    ws_params['gateway'] = self.ws.gateway
                continue

            retry = backoff.delay()
            _log.exception('[{}][{}]: Attempting a reconnect in {:.2f}'.format(self.__class__.__name__, self.id, retry))
            await asyncio.sleep(retry)

            # we should always try to resume discord will invalidate session if not
            self._set_reconnect_params(ws_params, resume=True)
                    
    async def run(self, reconnect=True):

        _log.debug('[{}][{}]: Running client'.format(self.__class__.__name__, self.id))
        await self.connect(reconnect)

    @property
    def is_ready(self):
        return self._connection._ready

    @property
    def user(self):
        return self._connection.user

    @property
    def users(self):
        return list(self._connection._users.values())

    @property
    def cached_messages(self):
        return list(self._connection._messages.values())

    async def delete_message(self, channel_id, msg_id):
        self.loop.create_task(
            self._connection.http.delete_message(channel_id, msg_id))

    async def change_username(self, password, username):
        self.loop.create_task(self._connection.http.change_username(password, username))
