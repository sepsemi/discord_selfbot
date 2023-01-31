import logging

from .user import (
    ClientUser, 
    User
)
from .guild import Guild
from .message import Message
from .channel import PrivateChannel

_log = logging.getLogger(__name__)

class ConnectionState:

    def __init__(self, loop, http, dispatch):
        self.loop = loop
        self.http = http
        self.dispatch = dispatch

        # Set the abs() max heartbeat timeout
        self.heartbeat_timeout = 60.0

        # register user defined methods
        self.parsers = parsers = {}
        for attr in dir(self):
            if attr.startswith('parse_'):
                func = getattr(self, attr)
                parsers[attr[6:].upper()] = func

        self.clear()

    def clear(self):
        self._users = {}
        self._guilds = {}
        self._channels = {}
        self._messages = {}
        self._ready = False

    def store_user(self, data):
        user_id = int(data['id'])
        try:
            return self._users[user_id]
        except KeyError:
            user = User(state=self, data=data)
            if user.discriminator != '0000':
                self._users[user_id] = user
            return user

    def store_message(self, channel, data):
        message_id = int(data['id'])
        try:
            return self._messages[message_id]
        except KeyError:
            message = Message(state=self, data=data, channel=channel)
            self._messages[message_id] = message
            return message

    def store_channel(self, data):
        channel_id = int(data['channel_id'])
        try:
            return self._channels[channel_id]
        except KeyError:
            channel,  _ = self._get_guild_channel(data)
            self._channels[channel_id] = channel
            return channel

    def store_guild(self, data):
        guild_id = int(data['id'])
        try:
            return self._guilds[guild_id]
        except KeyError:
            guild = Guild(state=self, data=data)
            self._guilds[guild_id] = guild
            return guild

    def _get_guild_channel(self, data, guild_id=None):
        # tries to get the channel or guild + channel
        channel_id = int(data['channel_id'])
        try:
            guild_id = guild_id or int(data['guild_id'])
            guild = self._guilds[guild_id]
            channel = guild.channels[channel_id]

        except KeyError:
            channel = self._channels[channel_id]
            guild = None

        return channel, guild
    
    def parse_ready(self, data):
        self.user = ClientUser(state=self, data=data['user'])
        # add all the users
        for user in data['users']:
            self.store_user(user)

        # store all the guilds
        for guild_data in data['guilds']:
            guild = self.store_guild(guild_data)

        for private_channel in data['private_channels']:
            channel_id = int(private_channel['id'])
            self._channels[channel_id] = PrivateChannel(me=self.user, state=self, data=private_channel)
        
        self._ready = True
        self.dispatch('ready')

    def parse_channel_create(self, data):
        channel_id = int(data['id'])
        channel_type = int(data['type'])

        print('new_channel: ', channel_type, channel_id)

        if channel_type == 1:
            # New DM or PrivateChannel
            print(data)
            self._channels[channel_id] = PrivateChannel(me=self.user, state=self, data=data)


    def parse_message_create(self, data):
        channel = self.store_channel(data)
        message = self.store_message(channel, data)
        
        user_id = message.author.id

        if user_id not in self._users.keys():
            user = self.store_user(data['author'])
            self.dispatch('new_user', user)
            _log.debug('[{self.id}][{self.__class__.__name__}]: new user: {user}'.format(self=self, user=user))

        self.dispatch('message', message)

    def parse_message_edit(self, data):
        return None 

    def parse_message_delete(self, data):
        message_id = int(data['id'])
        try:
            message = self._messages[message_id]
            self.dispatch('message_delete', message)
        except KeyError:
            return None

        
