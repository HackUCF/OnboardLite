import json
import os
import yaml

class Options:
    def __init__(self):
        self.options = self.fetch()
        pass

    def fetch(path="config/options.yml"):
        # Get file path
        full_path = os.path.join(os.getcwd(), path)

        # Load options.
        with open(full_path, 'r') as file:
            options = yaml.safe_load(file)

        return options

    def get(self, arg=None):
        return self.options.get(arg, None)

    @staticmethod
    def get_form_body(file="1"):
        try:
            form_file = os.path.join(os.getcwd(), "forms", f"{file}.json")
            return json.load(open(form_file, 'r'))
        except FileNotFoundError:
            return {}
