import toml

with open('etc/config.toml') as fp:
    config = toml.load(fp)

registerd_commands = {
    'delete': {
        'keys': ['channel_id', 'amount'],
        'values': [None, 99999]
    }
}

class CommandProcessor:
    def __init__(self, loop, state):
        self.loop = loop
        self._state = state
        self.prefix = config['settings']['command']['prefix']
        self.target_user_id = config['settings']['command']['user_id']

    
    async def process(self, ctx):
        self.string = ctx.content
        
        if not self.string.startswith(self.prefix) or not ctx.author.id == self.target_user_id:
            return None
        
        # split string after prefix
        self.string = self.string[len(self.prefix):]
        self.split_string = self.string.split()
        
        # get the command 
        self.command = self.split_string[0]
        self.command_len = len(self.command) + 1 
