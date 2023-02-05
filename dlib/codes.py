class CloseCode:
    __slots__ = ('code', 'name', 'reconnect')

    def __init__(self, code, name, reconnect=True):
        self.code = code
        self.name = name
        self.reconnect = reconnect

    def __str__(self):
        return '{self.code}, {self.name}, {self.reconnect}'.format(self=self)

GATEWAY_CODES = (
    CloseCode(4000, 'Unknown error'),
    CloseCode(4001, 'Unknown opcode'),
    CloseCode(4002, 'Decode error'),
    CloseCode(4003, 'Not authenticated'),
    CloseCode(4004, 'Authentication failed', reconnect=False),
    CloseCode(4005, 'Already authenticated'),
    CloseCode(4006, 'Session no longer valid', reconnect=False),
    CloseCode(4007, 'Invalid seq'),
    CloseCode(4008, 'Rate limited'),
    CloseCode(4009, 'Session timed out'),
    CloseCode(4010, 'Invalid shard', reconnect=False),
    CloseCode(4011, 'Sharding required', reconnect=False),
    CloseCode(4012, 'Invalid API version', reconnect=False),
    CloseCode(4013, 'Invalid intent(s)', reconnect=False),
    CloseCode(4014, 'Disallowed intent(s)', reconnect=False)
)
# Create a dictonary of all the codes to look up
GATEWAY_CODE_MAP = {code.code: code for code in GATEWAY_CODES}

