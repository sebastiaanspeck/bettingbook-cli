import os

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

config = ConfigParser()

class ConfigHandler(object):
    def __init__(self):
        pass

    @staticmethod
    def get(self, section, value):
        return config.get(section, value)

    @staticmethod
    def get_data(section):
        self.load_config_file()
        data = {}
        for (key, val) in config.items(section):
            data[key] = val
        return data
    
    @staticmethod
    def create_config_file(apikey, name, timezone, filename):
        config.add_section('auth')
        config.set('auth', 'api_key', apikey)
        config.add_section('profile')
        config.set('profile', 'name', name)
        config.set('profile', 'balance', '100.00')
        config.set('profile', 'timezone', timezone)
        config.add_section('betting_files')
        config.set('betting_files', 'open_bets', 'betting_files/open_bets.csv')
        config.set('betting_files', 'closed_bets', 'betting_files/closed_bets.csv')
        with open(filename, 'w') as cfgfile:
            config.write(cfgfile)


    def get_missing_data_config(self):
        keys = []
        missing_options = []
        sections = [section for section in config.sections()]
        missing_sections = [x for x in ['auth', 'profile', 'betting_files'] if x not in sections]
        for section in config.sections():
            keys.extend([key for (key, val) in config.items(section)])
            missing_options.extend([(key, val) for (key, val) in config.items(section) if val == ""])
        missing_keys = [x for x in ['api_key', 'name', 'balance', 'timezone', 'open_bets', 'closed_bets'] if x not in keys]
        return missing_sections, missing_keys, missing_options


    def check_config_file(self, filename):
        missing_sections, missing_keys, missing_options = self.get_missing_data_config()
        for missing_key in missing_keys:
            if missing_key != "balance":
                value = str(input(f"Give the value for {missing_key}: "))
            else:
                value = "100"
            if missing_key in ["name", "balance", "timezone"]:
                if "profile" in missing_sections:
                    config.add_section('profile')
                update_config_file("profile", missing_key, value, filename)
            elif missing_key == "api_key":
                if "auth" in missing_sections:
                    config.add_section('auth')
                update_config_file("auth", missing_key, value, filename)
            elif missing_key in ["open_bets", "closed_bets"]:
                if "betting_files" in missing_sections:
                    config.add_section('betting_files')
            missing_sections, missing_keys, missing_options = self.get_missing_data_config()
        for missing_option in missing_options:
            if missing_option[0] != "balance":
                value = str(input(f"Give the value for {missing_option[0]}: "))
            else:
                value = "100"
            if missing_option[0] in ["name", "balance", "timezone"]:
                self.update_config_file("profile", missing_option[0], value, filename)
            if missing_option[0] == "api_key":
                self.update_config_file("auth", missing_option[0], value, filename)
            if missing_option[0] in ["open_bets", "closed_bets"]:
                self.update_config_file("betting_files", missing_option[0], value, filename)


    def update_config_file(section, key, value, filename):
        config.set(section, key, value)
        with open(filename, 'w') as cfgfile:
            config.write(cfgfile)


    def load_config_file(self):
        filename = os.path.join(os.getcwd(), 'config.ini')
        if not os.path.exists(filename):
            apikey = str(input("Give the API-key: "))
            name = str(input("Give your name: "))
            timezone = str(input("Give your timezone (e.a. Europe/Amsterdam): "))
            self.create_config_file(apikey, name, timezone, filename)
        config.read(filename)
        self.check_config_file(filename)
