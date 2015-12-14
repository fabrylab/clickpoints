import ConfigParser
import json

class ConfigAccessHelper:
    def __init__(self, parent, section):
        self.parent = parent
        self.section = section

    def __getattr__(self, key):
        try:
            data = self.parent.get(self.section, key)
        except ConfigParser.NoOptionError:
            return ""
        try:
            return json.loads(data)
        except ValueError:
            return data

class Config(ConfigParser.ConfigParser):
    def __init__(self, filename=None, *args, **kwargs):
        ConfigParser.ConfigParser.__init__(self, *args, **kwargs)
        if filename is not None:
            self.read(filename)

    def __getattr__(self, key):
        if key in self.sections():
            return ConfigAccessHelper(self, key)
        return ConfigParser.ConfigParser.__getattr__(self, key)