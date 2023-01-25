class BaseUser:
    __slots__  = (
        'id',
        'username',
        'discriminator',
        'avatar',
        '_banner',
        'bot',
        'system',
        '_flags',
        'public_flags',
        '_premium_type',
        '_state'
    )

    def __init__(self, state, data):
        self._state = state
        self.id = int(data['id'])
        self.username = data['username']
        self.discriminator = data['discriminator']
        self.avatar = data['avatar']
        self.bot = data.get('bot', False)
        self.system = data.get('system', False)
        self._banner = data.get('banner')
        self._flags = int(data.get('flags', 0))
        self._premium_type = int(data.get('premium_type', 0))
        self.public_flags = int(data.get('public_flags', 0))
    
    def __repr__(self) -> str:
        return (
            f"<BaseUser id={self.id} name={self.username!r} discriminator={self.discriminator!r}"
            f" bot={self.bot} system={self.system}>"
        )

    @property
    def json(self):
        return {
            'id': self.id,
            'username': self.username,
            'discriminator': self.discriminator,
            'avatar': self._avatar,
            'bot': self.bot,
            'system': self.system,
            'banner': self._banner,
            'flags': self._flags,
            'premium_type': self._premium_type,
            'public_flags': self._public_flags
        }

    def __str__(self) -> str:
        return f'{self.username}#{self.discriminator}'

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _UserTag) and other.id == self.id

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return self.id >> 22

class ClientUser(BaseUser):
    __slots__ = ('locale', '_flags', 'verified', 'mfa_enabled', '__weakref__')

    def __init__(self, state, data):
        super().__init__(state=state, data=data)
        self.verified = data.get('verified', False)
        self.locale = data.get('locale')
        self._flags = data.get('flags', 0)
        self.mfa_enabled = data.get('mfa_enabled', False)

class User(BaseUser):

    __slots__ = ('__weakref__',)
