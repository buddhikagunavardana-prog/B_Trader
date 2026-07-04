import json


class ParameterManager:

    def __init__(self, path="src/config/strategy.json"):
        self.path = path

    def load(self):
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, data):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def update(self, section, key, value):
        data = self.load()

        data[section][key] = value

        self.save(data)

    def update_nested(self, keys, value):
        data = self.load()

        target = data

        for key in keys[:-1]:
            target = target[key]

        target[keys[-1]] = value

        self.save(data)

    def get(self, section):
        data = self.load()
        return data.get(section)

    def get_nested(self, keys):
        data = self.load()

        target = data

        for key in keys:
            target = target[key]

        return target