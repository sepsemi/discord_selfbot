from .utils import snowflake_time
from .user import User


class Message:
    
    def __init__(self, state, channel, data):
        self._state = state
        self.channel = channel
        self.id = int(data['id'])
        self.type = int(data['type'])
        self.everyone = data['mention_everyone']
        self.created_at = snowflake_time(self.id)
        self.content = data['content']
        self.author = User(state=state, data=data['author'])

    def __str__(self):
        return 'channel_id={self.channel.id}, id={self.id}, author={self.author}, content={self.content}'.format(self=self)


