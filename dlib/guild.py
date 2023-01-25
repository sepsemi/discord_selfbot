from .channel import TextChannel

def factory_channel(channel_type, channel):
    if channel_type == 0:
        # Guild channel
        return None

class Guild:
    
    def __init__(self, state, data):
        self.channels = {}
        self.members = {}
        self._state = state
        
        # Data
        self.id = int(data['id'])
        self.name = data['name']
        self.verification_level = int(data['verification_level'])
        self._icon = data['icon']
        self._banner = data['banner']
        self.emojis = data['emojis']
        self.description = data['description']
        self.vanity_url_code = data['vanity_url_code']
        self._discovery_splash = data['discovery_splash']
        self.owner_id = int(data['owner_id'])
    
        # The only channel types we care about are (0, 2, 4, 5, 11, 13, 14, 15)
        for channel_data in data['channels']:
            if channel_data['type'] == 0:
                channel = TextChannel(state, self, channel_data)
                # Fast lookups
                self.channels[channel.id] = channel

    def __str__(self):
        return self.name
