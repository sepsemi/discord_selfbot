import uvloop
import logging
import asyncio
import websockets
import contextlib

from .device import create_devices

from .http import HTTPClient
from .state import ConnectionState
from .backoff import ExponentialBackoff
from .gateway import Websocket, ReconnectWebSocket, WEBSOCKET_CAN_HANDLE_CODES

# Cannot run many clients, need to fix
DEVICES = create_devices()

_log = logging.getLogger(__name__)

def get_new_loop():
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop

def set_loop_on_client(client, loop):
    client.loop = loop

def run_clients(*clients, loop = None, reconnect=True):
    if loop is None:
        loop = get_new_loop()

    tasks = []
    for client in clients:

        set_loop_on_client(client, loop)
        tasks.append(loop.create_task(client.run(reconnect)))
    
    try:
        loop.run_until_complete(asyncio.wait(tasks))
    except KeyboardInterrupt:
        # Gracefull shutdown
        all_tasks = asyncio.gather(*asyncio.all_tasks(loop), return_exceptions=False)
        all_tasks.cancel()
    finally:
        loop.close()

class Client:

    def __init__(self, loop = None, token=None):
        self.loop = loop
        self.token = token
        self.id = token[:18]
        self._closed = True
        self._device = DEVICES.pop()
        #self._connection = self._get_connection()
        #self._ws = self._get_websocket()

    @property
    def _ws_client_params(self):
        size = 1024 * 1024 * 2.5

        return {
            'max_size': size,
            'read_limit': size,
            'write_limit': size
        }

    def _get_connection(self):
        state = ConnectionState(
            loop=self.loop,
            http=HTTPClient(self.loop, self.token, self._device),
            dispatch=self.dispatch,
        )
        state.id = self.id
        return state

    def _get_websocket(self, params):
        return Websocket(client=self, loop=self.loop, params=params)

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

    def clean(self):
        self._closed = False
        self._ws._keep_alive.open = False

    def close(self):
        self._closed = True
        self._ws._keep_alive.open = False
        self.loop.create_task(self._connection.http.close())


    async def connect(self, reconnect):
        backoff = ExponentialBackoff()
        self._closed = False 
        ws_params = {'initial': True}

        self._connection = self._get_connection()
 
        # i wonder if there is a better way to handle this
        while not self._closed or reconnect is True:
            self._ws = self._get_websocket(ws_params)

            async with websockets.connect(self._ws.uri, **self._ws_client_params) as sock:
                while not self.is_closed:
                    try:
                        await self._ws.poll_event(sock)
                    except ReconnectWebSocket as e:
                        _log.debug('[{}] gateway: got a request to {}'.format(
                            self.id, e.op.lower()))
                        ws_params.update(
                            sequence=self._ws.sequence, resume=e.resume, session=self._ws.session_id)
                        self.close()
                        continue

                    except (
                            websockets.exceptions.ConnectionClosedError, 
                            websockets.exceptions.ConnectionClosedOK,
                    ) as e:
                        _log.error(
                            '[{}] gateway: receive connection closed, code={}'.format(self.id, e.code))
 
                        # If we cannot handle it close the connection entirely
                        if e.code not in WEBSOCKET_CAN_HANDLE_CODES:
                            # raises error if keepalive is not set
                            return self.close()
                        
                        break
               
            # clean up the session for a reconnect
            self.clean()
            
            # always resume
            ws_params.update(sequence=self._ws.sequence, resume=True, session=self._ws.session_id)
            retry = backoff.delay()
            _log.debug("Attempting a reconnect in %.2fs", retry)
            await asyncio.sleep(retry)

    async def run(self, reconnect=True):
        _log.debug('running client_id={}'.format(self.id))
        await self.connect(reconnect)

    @property
    def is_closed(self):
        return self._closed

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
