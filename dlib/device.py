import os
import sys
import random

BUILD_NUMBERS = (
    149345,
    72112,
)

USER_AGENTS = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.75 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/E7FBAF',
)

def get_browser_version(agent):
    # get the version string from user agent string
    slash_seperated = agent.split('/')
    
    # second last index contains version number
    return slash_seperated[-2].split()[0]

def create_device():
    user_agent = random.choice(USER_AGENTS)
    browser_version = get_browser_version(user_agent)
    build_number = random.choice(BUILD_NUMBERS)

    return {
    	'os': 'Windows',
		'browser': 'Chrome',
		'device': "",
		'system_locale': 'en-US',
		'browser_user_agent': user_agent,
		'browser_version': browser_version,
		'os_version': '',
		'referrer': '',
		'referring_domain': '',
		'referrer_current': '',
		'referring_domain_current': '',
		'release_channel': 'stable',
		'client_build_number': build_number,
		'client_event_source': None
	} 

def create_devices():
    # Create A number of possible combinations of devices to mimic more of discord
    
    devices = []
    num_of_combinations = len(USER_AGENTS) + len(BUILD_NUMBERS) * 2 

    while len(devices) < num_of_combinations:
        device_map = create_device()
        if device_map not in devices:
            devices.append(device_map)
    return devices
