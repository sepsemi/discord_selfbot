from .user import User

class GuildChannel:
    def __init__(self, state, guild, data):
        self._state = state
        self.id = int(data['id'])
        self.type = int(data['id'])
        self.guild = guild

class TextChannel:
    
    def __init__(self, state, guild, data):
        self.id = int(data['id'])
        self.type = int(data['type'])
        self.nsfw = data.get('nsfw', None)
        self.flags = int(data['flags'])
        self.name = data['name']
        self.topic = data['topic']
        self.guild = guild
        self.position = int(data['position'])

    def __str__(self):
        return '{}, {}, {}, {}'.format(self.id, self.name, self.flags, self.topic)

class PrivateChannel:

    def __init__(self, me, state, data):
        self._state = state
        self.type = int(data['type'])
        self.id = int(data['id'])
        self.flags = int(data['flags'])
        self.guild = None
        self.recipients = self._get_recipients(data)

    def _get_recipients(self, data):
        try:
             return [self._state._users[int(uid)] for uid in data['recipient_ids']]
        except KeyError:
            # No recipients stored
            recipients = []
            for recipient in data['recipients']:
                recipients.append(self._state.store_user(recipient))
        
            return recipients
            
    def __str__(self):
         return 'Direct message with {}'.format(self.recipients[0])

    @property
    def name(self):
        return 'Direct message with {}'.format(self.recipients[0])
