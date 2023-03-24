import json
import sublime
import sublime_plugin
import threading
import os
import urllib.request as request

class ChatGptCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.set_settings()
        view = self.view

        # Get the region of the entire buffer
        regions = view.sel()

        # Check that there is exactly one selection region
        if len(regions) == 1:
            # Get the selected region
            region = regions[0]

            # Get the text of the selected region
            self.selected_text = view.substr(region)
        self.show_input()


    def set_settings(self):
        settings = sublime.load_settings('ChatGPT.sublime-settings')

        self.settings = {
            'api_key': str(settings.get('api_key')),
            'timeout': int(settings.get('timeout', 10)),
            'model': str(settings.get('model', 'text-davinci-003')),
            'temperature': float(settings.get('temperature', 0.5)),
            'max_tokens': int(settings.get('max_tokens', 1024)),
            'debug': bool(settings.get('debug', False))
        }

        self.debug('settings', self.settings)

    def show_input(self):
        self.window = sublime.active_window()
        self.view = self.window.active_view()
        self.window.show_input_panel(
            self.show_input_title(),
            self.show_input_value(),
            self.show_input_done,
            None,
            None
        )

    def show_input_title(self):
        return 'ChatGPT Question (model: %s | timeout: %s)' % (self.settings['model'], self.settings['timeout'])

    def show_input_value(self):
        if len(self.settings['api_key']) == 0:
            return 'You must set the API Key (Preferences > Package Settings > ChatGPT > Settings)'
        return ''

    def show_input_done(self, input_string):
        if len(self.settings['api_key']) == 0:
            return

        self.debug('show_input_done[input_string]', input_string)

        if len(input_string) == 0:
            return

        self.view.settings().set('show_input_last', input_string)
        # put something to check input here
        input_string = input_string.replace(' ','')
        input_string = input_string.replace('_',' ')
        input_string = input_string.split(':')
        command_line_options = []
        try:
            command_line_options = input_string[1].split(',')
        except:
            pass
        command_line_options.append(self.selected_text)
        # Unix-based systems
        if os.name == "posix":
            home_dir = os.path.expanduser("~")
            file_path = os.path.join(home_dir, ".config", "sublime-text", "Packages", "MyChatGPT", "ChatGPT-Prompt", input_string[0])
            
        # Windows
        elif os.name == "nt":
            home_dir = os.environ["userprofile"]
            file_path = os.path.join(home_dir, "path", "to", "file.txt")

        # Open the file and start the search from the home directory
        with open(file_path, "r") as file:
            contents = file.read()
            contents = contents.format(*command_line_options)
            print(command_line_options)
            print(contents)
        Request(self.view, self.settings, contents).start()

    def debug(self, key, value):
        if (self.settings['debug']):
            print(key, value)

class Request(threading.Thread):
    def __init__(self, view, settings, prompt):
        self.view = view
        self.settings = settings
        self.prompt = prompt
        super(Request, self).__init__()

    def run(self):
        contents = self.request().replace('\\', '\\\\').replace('$', '\\$')

        self.view.run_command('insert_snippet', {'contents': contents})

    def request(self):
        response = self.request_response()
        data = self.request_data()
        timeout = self.settings['timeout']

        self.debug('request[data]', data)

        try:
            text = request.urlopen(response, data=data, timeout=timeout).read().decode('utf-8')

            self.debug('request[response]', text)

            text = str(json.loads(text)['choices'][0]['text'])

            if len(text) == 0:
                text = '# No Response #'
        except Exception as e:
            text = '# Error: %s #' % str(e)

        self.debug('request[text]', text)

        return text

    def request_response(self):
        return request.Request(
            url='https://api.openai.com/v1/completions',
            method='POST',
            headers=self.request_headers()
        )

    def request_headers(self):
        return {
            'Authorization': 'Bearer %s' % self.settings['api_key'],
            'Content-Type': 'application/json'
        }

    def request_data(self):
        return json.dumps({
            'prompt': self.prompt,
            'model': self.settings['model'],
            'temperature': self.settings['temperature'],
            'max_tokens': self.settings['max_tokens']
        }).encode()

    def debug(self, key, value):
        if (self.settings['debug']):
            print(key, value)
