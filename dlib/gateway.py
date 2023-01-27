import time
import zlib
import logging
import asyncio
import websockets

from .utils import minutes_elapsed_timestamp, to_json, from_json

_log = logging.getLogger(__name__)


WEBSOCKET_CAN_HANDLE_CODES = (
    1000, 
    1001,
    1006,
    4010, 
    4011, 
    4012, 
    4013, 
    4014
)

class ReconnectWebSocket(Exception):

    def __init__(self, resume=True):
        self.resume = resume
        self.op = 'RESUME' if resume else 'IDENTIFY'


class AsyncKeepaliveHandler:
    WINDOW = 2.0

    def __init__(self, websocket, interval, sock):
        self.open = False
        self.websocket = websocket
        self.interval = interval
        self.sock = sock
        self.id = websocket.id
        self.heartbeat_timeout = websocket._max_heartbeat_timeout

        # Predefined messages
        self.msg = '[%s] keepalive: heartbeat send, sequence=%s'
        self.behind_msg = '[%s] keealive: Gateway acknowledged late %.1fs behind'

        # Metric data
        timestamp = time.perf_counter()
        self._last_send = timestamp
        self._last_ack = timestamp
        self._last_recv = timestamp
        self.latency = float('inf')

    def ack(self):
        ack_time = time.perf_counter()
        self._last_ack = ack_time
        self.latency = ack_time - self._last_send

        if self.latency > 10:
            _log.warn(self.behind_msg % (self.websocket.id, self.latency))
        else:
            _log.debug(self.msg % (self.id, self.websocket.sequence))

    def tick(self):
        self._last_recv = time.perf_counter()

    def get_payload(self):
        return {
            'op': self.websocket.HEARTBEAT,
            'd': self.websocket.sequence
        }

    async def run(self):
        self.open = True

        while self.open:
            if self._last_recv + self.heartbeat_timeout < time.perf_counter():
                _log.warn(
                    '[{}] keepalive: has stopped responding to gateway, closing'.format(self.id))
                return None

            data = self.get_payload()
            try:
                # Send the payload to the websocket and quit if timeout
                
                _log.debug('[{}] keepalive: sending payload'.format(self.id))
                await asyncio.wait_for(self.sock.send(to_json(data)), timeout=self.WINDOW)
                self._last_send = time.perf_counter()

            except asyncio.exceptions.TimeoutError:
                _log.warn(
                    '[{}] keepalive: error, closing connection'.format(self.id))

                # We can't really close it in here since we need to raise an exception
                self.websocket.close_from_keep_alive()
                return None

            await asyncio.sleep(self.interval - self.WINDOW)


class Websocket:
    DISPATCH = 0
    HEARTBEAT = 1
    IDENTIFY = 2
    PRESENCE = 3
    VOICE_STATE = 4
    VOICE_PING = 5
    RESUME = 6
    RECONNECT = 7
    REQUEST_MEMBERS = 8
    INVALIDATE_SESSION = 9
    HELLO = 10
    HEARTBEAT_ACK = 11
    GUILD_SYNC = 12

    def __init__(self, loop, client, **params):
        self.loop = loop
        self.id = client.id
        self.token = client.token
        self.uri = 'wss://gateway.discord.gg/?encoding=json&v=9&compress=zlib-stream'

        self._connection = client._connection
        self._discord_parsers = client._connection.parsers
        self._dispatch = client.dispatch

        # register unique device to spoof the socket connection
        self._device = client._device

        self._keep_alive = None

        # Updatables
        self.session_id = params.get('session_id', None)
        self.sequence = params.get('session_id', None)
        self.resume_set = params.get('resume', False)

        self._max_heartbeat_timeout = client._connection.heartbeat_timeout
        self._zlib = zlib.decompressobj()
        self._buffer = bytearray()
        self._close_code = None

    def clean(self):
        # Clean up after ourselfs
        self._keep_alive = None
        self.session_id = None
        self.sequence = None
        self._zlib = zlib.decompressobj()
        self._buffer = bytearray()
        self._close_code = None

    async def received_message(self, sock, msg):
        if type(msg) is bytes:
            self._buffer.extend(msg)
            if len(msg) < 4 or msg[-4:] != b'\x00\x00\xff\xff':
                return None

            msg = self._zlib.decompress(self._buffer)
            self._buffer = bytearray()

        msg = from_json(msg)

        event = msg['t'] if 't' in msg.keys() else None
        op = msg['op'] if 'op' in msg.keys() else None
        data = msg['d'] if 'd' in msg.keys() else None
        seq = msg['s'] if 's' in msg.keys() else None

        if seq is not None:
            self.sequence = seq

        if self._keep_alive:
            self._keep_alive.tick()

        if op != self.DISPATCH:
            if op == self.RECONNECT:
                _log.debug('[{}] gateway: Asked for reconnect'.format(self.id))
                self._keep_alive.open = False
                raise ReconnectWebSocket()

            if op == self.HEARTBEAT_ACK:
                if self._keep_alive:
                    self._keep_alive.ack()
                return None

            if op == self.HEARTBEAT:
                await self._keep_alive.send_heartbeat(self.id)
                _log.debug(
                    '[{}] gateway: Request forcefull hearbeat send'.format(self.id))
                return None

            if op == self.HELLO:
                interval = data['heartbeat_interval'] / 1000.0

                if not self.resume_set:
                    # Send identify
                    await self.identify(sock)
                else:
                    await self.resume(sock)

                self._keep_alive = AsyncKeepaliveHandler(
                    websocket=self, interval=interval, sock=sock)
                self.loop.create_task(self._keep_alive.run())

            if op == self.INVALIDATE_SESSION:
                if data is True:
                    raise ReconnectWebSocket()

                # Set to null
                self.sequence = None
                self.session_id = None

                # Close keepalive
                self._keep_alive.open = False

                _log.info('[{}] gateway: Invalidated session'.format(self.id))
                raise ReconnectWebSocket(resume=False)

            return None

        if event == 'READY':
            # Update our prescence as we connect
            await self.change_presence(sock)

        elif event == 'RESUMED':
            _log.debug('[{}] gateway: has resumed'.format(self.id))

        try:
            func = self._discord_parsers[event]
        except KeyError:
            if event is not None:
                _log.debug('[{}] gateway: unsubscribed event seq={}, event={}'.format(
                    self.id, seq, event))
        else:
            func(data)

    def close_from_keep_alive(self):
        # Yeah i can't care more anymore.
        try:
            raise ReconnectWebSocket()
        # Funny we are raising anod now we need to close
        except ReconnectWebSocket:
            return None

    async def change_presence(self, sock):
        # Create an elapsed timestamp for exmaple "20-60 minutes"
        elapsed = minutes_elapsed_timestamp(0)
        payload = {
            'op': self.PRESENCE,
            'd': {
                'status': 'idle',
                'since': None,
                'activities': [
                    {
                        'name': 'Hearts of Iron IV',
                        'type': 0,
                        'application_id': 358421669603311616,
                        'timestamps': {
                            'start': elapsed
                        }
                    }
                ],
                'afk': False
            }
        }
        await sock.send(to_json(payload))

    async def resume(self, sock):
        payload = {
            'op': self.RESUME,
            'd': {
                'seq': self.sequence,
                'session_id': self.session_id,
                'token': self.token
            }
        }
        await sock.send(to_json(payload))

    async def identify(self, sock):
        # This is highly unreliable
        payload = {
            'op': self.IDENTIFY,
            'd': {
                'token': self.token,
                'capabilities': 1021,
                'properties': {**self._device},
                'compress': False,
                # Need to research
                'client_state': {
                    'guild_hashes': {},
                    'highest_last_message_id': '0',
                    'read_state_version': 0,
                    'user_guild_settings_version': -1,
                    'user_settings_version': -1,
                    'private_channels_version': '0'
                }
            }
        }

        # Set presence
        payload['d']['presence'] = {
            'status': 'idle',
            'since': 0,
            'activities': [],
            'afk': False
        }

        await sock.send(to_json(payload))

    async def poll_event(self, sock):
        try:
            msg = await asyncio.wait_for(sock.recv(), timeout=self._max_heartbeat_timeout)
            await self.received_message(sock, msg)

        except asyncio.exceptions.TimeoutError as e:
            _log.error('[{}] gateway: receive timeout'.format(self.id))
            raise ReconnectWebSocket
