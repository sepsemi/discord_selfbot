class PrivateChannel:

    def __init__(self, me, state, data):
        self.type = int(data['type'])
        self.id = int(data['id'])
        self.flags = int(data['flags'])
        self.guild = None
        self.recipients = [state._users[int(uid)] for uid in data['recipient_ids']]

    def __str__(self):
         return 'Direct message with {}'.format(self.recipients[0])

    @property
    def name(self):
        return 'Direct message with {}'.format(self.recipients[0])

class DMChannel:

    def __init__(self, me, state, data):
        self._state = state
        self.recipient = data['recipients'][0]
        self.me = me
        self.id = int(data['id'])

    def __str__(self) -> str:
        if self.recipient:
            return f'Direct Message with {self.recipient}'
        return 'Direct Message with Unknown User'

    @classmethod
    def _from_message(cls, state, channel_id):
        self = cls.__new__(cls)
        self._state = state
        self.id = channel_id
        self.recipient = None
        self.me = state.user
        return self

class TextChannel:
    
    def __init__(self, state, guild, data):
        self.id = int(data['id'])
        self.type = int(data['type'])
        self.nsfs = int(data['nsfw']) if 'nsfw' in data.keys() else None
        self.flags = int(data['flags'])
        self.name = data['name']
        self.topic = data['topic']
        self.guild = guild
        self.position = int(data['position'])

        # Add the guild

    def __str__(self):
        return '{}, {}, {}, {}'.format(self.id, self.name, self.flags, self.topic)

