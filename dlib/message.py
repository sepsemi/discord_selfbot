from .utils import snowflake_time
from .user import User

class MessageReference:

    def __init__(self, state, channel, data):
        self._state = state
        self.id = int(data['message_id'])

class Message:

    __slots__ = ('_state', 'channel', 'id', 'type', 'everyone', 'author', 'created_at', 'content')

    def __init__(self, state, channel, data):
        self._state = state
        self.channel = channel
        self.id = int(data['id'])
        self.type = int(data['type'])
        self.everyone = data['mention_everyone']
        self.author = User(state=state, data=data['author'])
        self.created_at = snowflake_time(self.id)
        self.content = data['content']

