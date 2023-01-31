import inspect
import src.command as commands

def get_command_by_insepction(name):
    func = getattr(commands, name)
    result = inspect.getfullargspec(func)

    return (func, result.args, result.defaults)

class CommandProcessor:
    
    def __init__(self):
        self.prefix = '--'
        self.string = None
        self.split_string = None
        self.command_filling_functions = {
            1: self._fill_both_values,
            2: self._fill_one_value
        }
    
    def _build_command_from_kw(self):
        command = {}
        for step in self.split_string[1:]:
            if '=' in step:
                key, value = step.split('=')
                command[key] = value

        return command

    def _fill_both_values(self, command, keywords, values):
        for key, value in zip(keywords, values):
            command[key] = value

    def _fill_one_value(self, command, keywords, values):
        if self.split_string[1].isdigit():
            command[keywords[0]] = self.split_string[1]
            command[keywords[1]] = values[1]
        else:
            self._fill_missing_values(command, keywords, values)

    def _fill_missing_values(self, command, keywords, values):
        for key, value in zip(keywords, values):
            if key not in command.keys():
                command[key] = value

    def build_final_command(self, command, keywords, values):
        split_string_length = len(self.split_string)
        command_filling_function = self.command_filling_functions.get(split_string_length, self._fill_missing_values)
        command_filling_function(command, keywords, values)

    def process(self, ctx):
        if not ctx.content.startswith(self.prefix):
            return None

        self.string = ctx.content[len(self.prefix):]
        # split on space
        self.split_string = self.string.split()

        command_name = self.split_string[0]
        if command_name not in registered_commands:
            return None

        # build the command from keywords
        command = self._build_command_from_kw()
        
        func, keywords, values = get_command_by_insepction(command_name)        
        #keywords = registered_commands[command_name]['keywords']
        #values = registered_commands[command_name]['values']
        
        # build the final command
        self.build_final_command(command, keywords, values)
 
        func(ctx, **command)

