import zlib
import time
import logging
import asyncio
import threading
import websockets

from concurrent.futures import TimeoutError as TreadingTImeoutError

from .utils import (
    from_json, 
    to_json,
    minutes_elapsed_timestamp
)

from .codes import GATEWAY_CODE_MAP

_log = logging.getLogger(__name__)

def find_role_by_id(roles, role_id):
    for role in roles:
        if role['id'] == role_id:
            return role
    return None

def find_permission_object_with_permissions(overwrites, permission):
    for overwrite in overwrites:
        deny, allow = int(overwrite['deny']), int(overwrite['allow'])

        #if (allow & permission) == permission:
            #return True
        if not (deny & permission) == permission:
            return True

    return False    

class ReconnectWebSocket(Exception):

    def __init__(self, resume=True):
        self.resume = resume
        self.op = 'RESUME' if resume else 'IDENTIFY'

class KeepaliveClient:

    def __init__(self, ws, sock, interval):
        self.ws = ws
        self.loop = ws.loop
        self.sock = sock
        self.interval = interval
        self._max_heartbeat_timeout = ws._max_heartbeat_timeout
        
        self.last_ack = time.perf_counter() 
        self.last_send = time.perf_counter()
        self.last_recv = time.perf_counter()

    def __str__(self):
        return 'id={}, interval={}, sequence={}'.format(self.ws.id, self.interval, self.ws.sequence)

class KeepaliveHandler(threading.Thread):
    # Wait 2 seconds before we give timeout
    WINDOW = 2.0

    def __init__(self):
        threading.Thread.__init__(self, daemon=True)
        self.tick_time = 0.5
        self.clients = {}
        self._open = True

        # Predefined messages
        self.msg = '[%s][%s]: Gateway acknowledged heartbeat, sequence=%s'
        self.behind_msg = '[%s][%s]: Gateway acknowledged late %.1fs behind'
    
    def execute_thread_safe(self, client, func):
        future = asyncio.run_coroutine_threadsafe(func, client.loop)
        try:
            return future.result(self.WINDOW)
        except TreadingTImeoutError:
            _log.warn('[{}][{}]: Timed out waiting for future'.format(self.__class__.__name__, client.ws.id))
        except (
            websockets.exceptions.ConnectionClosedOK, 
            websockets.exceptions.ConnectionClosedError
        ):
            _log.warn('[{}][{}]: Connection is closed'.format(self.__class__.__name__, client.ws.id))
        
        # We have an exception so we should remove the client
        self.remove(client)

    def stop(self):
        # Signal the loop to stop
        self._open = False
         
    def add(self, client_id, ws, sock, interval):
        # add the client for hearbeats
        self.clients[client_id] = KeepaliveClient(ws, sock, interval)
        # we added a new client lets set new possible tick time
        self.tick_time = self.get_tick_time()

    def remove(self, client_id):
        # remove the client from the registerd clients
        if client_id in self.clients.keys():
            # shared state is bad
            del self.clients[client_id]

        # we should refresh our tick time
        self.tick_time = self.get_tick_time()

    def tick(self, client_id): 
        self.clients[client_id].last_recv = time.perf_counter()

    def ack(self, client_id):
        ack_time = time.perf_counter()
        client = self.clients[client_id]

        client.last_ack = ack_time
        client.latency = ack_time - client.last_send

        if client.latency > 10:
            _log.warn(self.behind_msg % (self.__class__.__name__, client_id, client.latency))
        else:
            _log.debug(self.msg % (self.__class__.__name__, client_id, client.ws.sequence))
    
    def get_payload(self, client_id):
        client = self.clients[client_id]
        return {
            'op': client.ws.HEARTBEAT,
            'd': client.ws.sequence
        }
    
    def get_tick_time(self):
        # search for the shortest interval and subtract with WINDOW 
        times = [client.interval for client in self.clients.values()]
        return min(times) - self.WINDOW if times else self.tick_time

    def run(self):
        while self._open:
            for client_id, client in self.clients.copy().items():
                if client.last_recv + client._max_heartbeat_timeout < time.perf_counter():
                    _log.warn('[{}][{}]: has stopped responding to gateway, closing'.format(self.__class__.__name__, client.ws.id))
                    result = self.execute_thread_safe(client, client.ws.close(client.sock))
                    self.remove(client)
                    continue

                # fire heartbeat block if we get error die on client and gateway
                _log.debug('[{}][{}]: Sending heartbeat to gateway'.format(self.__class__.__name__, client.ws.id))
                payload = to_json(self.get_payload(client_id))
                result = self.execute_thread_safe(client, client.sock.send(payload))
                client.last_send = time.perf_counter()

            # dynamically update this value when adding and removing clients
            time.sleep(self.tick_time)

_keep_alive_ref = KeepaliveHandler()

class DiscordWebSocket:
    API_VERSION = 9
    DEFAULT_GATEWAY =               'wss://gateway.discord.gg'

    # 0-12 is documented in discord docs the rest is reverse engineerd
    DISPATCH =                      0 
    HEARTBEAT =                     1
    IDENTIFY =                      2
    PRESENCE =                      3
    VOICE_STATE =                   4
    VOICE_PING =                    5
    RESUME =                        6
    RECONNECT =                     7
    REQUEST_MEMBERS =               8
    INVALIDATE_SESSION =            9
    HELLO =                         10
    HEARTBEAT_ACK =                 11
    GUILD_SYNC =                    12
    DM_UPDATE =                     13
    LAZY_REQUEST =                  14
    LOBBY_DISCONNECT =              16
    LOBBY_VOICE_STATES_UPDATE =     17
    STREAM_CREATE =                 18 
    STREAM_DELETE =                 19 
    STREAM_WATCH =                  20 
    STREAM_PING =                   21 
    STREAM_SET_PAUSED =             22 
    REQUEST_APPLICATION_COMMANDS =  24 

    def __init__(self, loop, client, params):
        self.loop = loop
        self.id = client.id
        self.token = client.token
        self.device = client._device
        self._dispatch = client.dispatch
        self._keep_alive = None

        # set the timeout to wait for polling events, but also keepalive timeout
        self._dispatch = client.dispatch
        self._connection = client._connection
        self._discord_parsers = client._connection.parsers
        self._max_heartbeat_timeout = client._connection.heartbeat_timeout
        
        self._initial = params['initial']
        self.resume_set = params.get('resume', False)

        self.sequence = params.get('sequence', None)
        self.session_id = params.get('session', None)

        # get the default or reconnect gateway
        uri =  params.get('gateway', self.DEFAULT_GATEWAY)
        self.gateway = uri + '/?encoding=json&v={}&compress=zlib-stream'.format(self.API_VERSION)

        self._reset_buffer()
        
        self._open = True

    def _reset_buffer(self):
        self._zlib = zlib.decompressobj()
        self._buffer = bytearray()

    def _extract_session_from_replace(self, data):
        # get the first session that is not our current and is as long as our current session_id

        for session in reversed(data):
            session_id = session['session_id']
            if len(session_id) >= len(self.session_id) and session_id != self.session_id:
                return session_id

        return self.session_id
 
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
            self._keep_alive.tick(self.id)
        
        if op != self.DISPATCH:
            if op == self.RECONNECT:
                _log.debug('[{}][{}]: Received RECONNECT opcode'.format(self.__class__.__name__, self.id))

                await self.close(sock)

                _log.debug('[{}][{}]: In reconnect transition sock closed={}'.format(self.__class__.__name__, self.id, sock.open))
                raise ReconnectWebSocket

            if op == self.HEARTBEAT_ACK:
                if self._keep_alive:
                    self._keep_alive.ack(self.id)
                return None

            if op == self.HEARTBEAT:
                if self._keep_alive:
                    _log.debug('[{}][{}]: Request forcefull hearbeat'.format(self.__class__.__name__, self.id))
                    payload = self._keep_alive.get_payload(self.id)
                    await sock.send(to_json(payload))
                return None

            if op == self.HELLO:
                interval = data['heartbeat_interval'] / 1000.0
                self._keep_alive = _keep_alive_ref

                # add the client to the keepalive handler, sends imediatly
                
                if not self.resume_set:
                    # send identify
                    await self.identify(sock)
                else:
                    await self.resume(sock)

                self._keep_alive.add(self.id, self, sock, interval)

            if op == self.INVALIDATE_SESSION:
                if data is True:
                    await self.close(sock)
                    raise ReconnectWebSocket()

                self.sequence = None
                self.session_id = None
                self.gateway = self.DEFAULT_GATEWAY

                _log.info('[{}][{}]: Session has been invalidated'.format(self.__class__.__name__, self.id))
                # Close keepalive
                await self.close(sock, code=1000)
                raise ReconnectWebSocket(resume=False)
            
            # done processing opcodes
            return None

        if event == 'READY':
            self.sequence = msg['s']
            self.session_id = data['session_id']
            self.gateway = data['resume_gateway_url']

            _log.info('[{}][{}]: Connected to gateway session_id={}'.format(self.__class__.__name__, self.id, self.session_id))
            
            await self.change_presence(sock)  
            
            if self._initial:
                # This is only called on the first ever connect
                self._dispatch('setup_hook')

            # Subscribe to all the guilds
            #await self.subscribe_to_guilds(sock, data['guilds'])

        elif event == 'RESUMED':
            _log.info('[{}][{}]: Successfully RESUMED session_id={}'.format(self.__class__.__name__, self.id, self.session_id))

        elif event == 'SESSIONS_REPLACE':
            # update the running session

            return None

            new_session_id = self._extract_session_from_replace(data)

            _log.debug('[{}][{}]: Replacing session_id={}, with={}'.format(self.__class__.__name__, self.id, self.session_id, new_session_id))
            self.session_id = new_session_id

            return None

        try:
            func = self._discord_parsers[event]
        except KeyError:
            if event is not None:
                _log.debug('[{}][{}]: Unknown event, seq={}, event={}'.format(self.__class__.__name__, self.id, self.sequence, event))
        else:
            func(data)

    async def resume(self, sock):
        payload = {
            'op': self.RESUME,
            'd': {
                'seq': self.sequence,
                'session_id': self.session_id,
                'token': self.token
            }
        }

        _log.debug('[{}][{}]: Sending resume packet: {}'.format(self.__class__.__name__, self.id, payload))
        await sock.send(to_json(payload))

    async def identify(self, sock):
        # This is highly unreliable
        payload = {
            'op': self.IDENTIFY,
            'd': {
                'token': self.token,
                'capabilities': 1021,
                'properties': {**self.device.headers},
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
        _log.debug('[{}][{}]: Sending identify packet: {}'.format(self.__class__.__name__, self.id, payload))
        await sock.send(to_json(payload))

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

    async def subscribe_to_guilds(self, sock, guilds):


        for guild in guilds:
            await self.subscribe_to_guild_channels(sock, guild)
    
            break

    async def subscribe_to_guild_channels(self, sock, guild):
        guild_id = guild['id']
        roles = guild['roles']
        default_role = find_role_by_id(roles, guild_id)
        
        channels = guild['channels']
        payload_channels = {}
        for index, channel in enumerate(channels):
            if 'id' in channel.keys():
                if channel['type'] == 0:

                    permission = (1 << 10) | (1 << 11) | (1 << 16)

                    if find_permission_object_with_permissions(channel['permission_overwrites'], permission):
                        print(channel['name'])
                        payload_channels[channel['id']] = [[0,99]]

        print('done')
        payload = {
            "op":14,
            "d":{
                "guild_id":"267624335836053506",
                "typing": True,
                "activities": True,
                "threads": True,
                "channels":{**payload_channels}
            }
        }
        print('sending lazy request')
        await sock.send(to_json(payload))


    @property
    def _ws_settings(self):
        size = 1024 * 1024 * 2.5
        return {
            'max_size': size,
            'read_limit': size,
            'write_limit': size,
            'ping_interval': self._max_heartbeat_timeout,
            'ping_timeout': self._max_heartbeat_timeout,
        }

    async def connect_and_poll(self):
        async with websockets.connect(self.gateway, **self._ws_settings, loop=self.loop) as self.sock:
            while self.sock.open:
                try:
                    msg = await asyncio.wait_for(self.sock.recv(), timeout=self._max_heartbeat_timeout)
                    await self.received_message(self.sock, msg)

                except asyncio.exceptions.TimeoutError as e:
                    _log.error('[{}][{}]: Websocket received timeout'.format(self.__class__.__name__, self.id))
                    raise ReconnectWebSocket
                
                except (
                        websockets.exceptions.ConnectionClosedError,  
                        websockets.exceptions.ConnectionClosedOK
                ) as e:
                    
                    if e.code in GATEWAY_CODE_MAP:
                        code = GATEWAY_CODE_MAP[e.code] 
                        _log.error('[{}][{}]: Processing websocket close with: code={}'.format(self.__class__.__name__, self.id, code)) 
                        # check if we should reconnect or not
                        await self.close(self.sock, e.code)
                        raise ReconnectWebSocket(code.reconnect)
                        
                    # The close code is unknown to us
                    _log.error('[{}][{}]: Websocket closed unknown code: {}'.format(self.__class__.__name__, self.id, e.code)) 
                    await self.close(self.sock, e.code)
                    return None

    async def close(self, sock, code=4000):
        if self._keep_alive:
            # remove the client from the keep_alive handler
            self._keep_alive.remove(self.id)
            self._keep_alive = None

        await sock.close(code=code)
            
