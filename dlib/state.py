import logging

from .user import ClientUser, User
from .channel import DMChannel, PrivateChannel
from .guild import Guild
from .message import Message

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

    def store_user(self, data):
        user_id = int(data['id'])
        try:
            return self._users[user_id]
        except KeyError:
            user = User(state=self, data=data)
            if user.discriminator != '0000':
                self._users[user_id] = user
            return user

    def store_guild(self, data):
        guild_id = int(data['id'])
        try:
            return self._guilds[guild_id]
        except KeyError:
            guild = Guild(state=self, data=data)
            self._guilds[guild_id] = guild
            return guild

    def store_message(self, msg):
        # Not storage efficient
        self._messages[msg.id] = msg

    def _get_guild_channel(self, data, guild_id=None):
        channel_id = int(data['channel_id'])
        try:
            guild_id = guild_id or int(data['guild_id'])
            guild = self._guilds[guild_id]
            channel = guild.channels[channel_id]
            # guild = self._get_guild(guild_id)

        except KeyError:
            # Absolute cringe!
            try:
                channel = self._channels[channel_id]
            except KeyError:
                channel = None

            channel = channel
            guild = None

        return channel, guild

    def parse_ready(self, data):
        self.user = ClientUser(state=self, data=data['user'])
        # add all the users
        for user in data['users']:
            self.store_user(user)

        for guild_data in data['guilds']:
            self.store_guild(guild_data)

        for private_channel in data['private_channels']:
            channel_id = int(private_channel['id'])
            self._channels[channel_id] = PrivateChannel(
                me=self.user, state=self, data=private_channel)

        self.dispatch('ready')

    def parse_message_create(self, data):
        channel, _ = self._get_guild_channel(data)
        if channel is None:
            return None

        message = Message(state=self, data=data, channel=channel)

        user_id = message.author.id
        if user_id not in self._users.keys():
            _log.debug('[{}] new user: {}, {}'.format(
                self.id, message.author.id, message.author))

            # Append user to the user store because we can't fetch them (easily)
            user = self.store_user(data['author'])
            self.dispatch('new_user', user)

        self.store_message(message)
        self.dispatch('message', message)

    def parse_message_edit(self, data):
        return None

    def parse_message_delete(self, data):
        return None
