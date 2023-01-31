import os
import sys
import random
from .utils import to_json
from base64 import urlsafe_b64encode

BUILD_NUMBERS = (
    149345,
    72112,
    170459,
    126021,
    1275,
    56252,
    9010,
    9008,
    9007,
    9006,
    9005,
    9004,
    9003,
)

USER_AGENTS = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.75 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/E7FBAF',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:101.0) Gecko/20100101 Firefox/101.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:99.0) Gecko/20100101 Firefox/99.0',
    'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.10; rv:75.0) Gecko/20100101 Firefox/75.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:61.0) Gecko/20100101 Firefox/73.0',
    'Mozilla/5.0 (Windows; U; Windows NT 9.1; en-US; rv:12.9.1.11) Gecko/20100821 Firefox/70'
)

class Device:

    __slots__ = ('build_number', 'user_agent','browser_version')

    def __init__(self, user_agent, browser_version, build_number):
        self.build_number = build_number
        self.user_agent = user_agent
        self.browser_version = browser_version

    @property
    def headers(self):
        return {
            'os': 'Windows',
            'browser': 'Chrome',
            'device': "",
            'system_locale': 'en-US',
            'browser_user_agent': self.user_agent,
            'browser_version': self.browser_version,
            'os_version': '',
            'referrer': '',
            'referring_domain': '',
            'referrer_current': '',
            'referring_domain_current': '',
            'release_channel': 'stable',
            'client_build_number': self.build_number,
            'client_event_source': None
        } 
    
    @property
    def x_super_properties(self):
        headers = self.headers
        return urlsafe_b64encode(to_json(headers))
    
def get_browser_version(agent):
    # get the version string from user agent string
    slash_seperated = agent.split('/')
    
    # second last index contains version number
    return slash_seperated[-2].split()[0]

def create_device():
    user_agent = random.choice(USER_AGENTS)
    browser_version = get_browser_version(user_agent)
    build_number = random.choice(BUILD_NUMBERS)

    return Device(user_agent, browser_version, build_number)

def create_devices():
    # Create A number of possible combinations of devices to mimic more of discord
    
    devices = []
    num_of_combinations = len(USER_AGENTS) + len(BUILD_NUMBERS) * 2 

    while len(devices) < num_of_combinations:
        device_map = create_device()
        if device_map not in devices:
            devices.append(device_map)

    return devices

create_device()
