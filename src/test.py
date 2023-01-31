from processor import CommandProcessor

test_commands = [
    '--delete',
    '--delete 60',
    '--delete channel_id=743646434232',
    '--delete amount=8453875 channel_id=743646434232',
    '--delete channel_id=743646434232 amount=90000',
    '--delete amount=80'
]

processor = CommandProcessor()

for command in test_commands:
    processor.process(command)
