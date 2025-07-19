import os

from configparser import ConfigParser

config = ConfigParser()


class ConfigHandler(object):
    FILENAME = os.path.join(os.getcwd(), "config.ini")

    def __init__(self):
        pass

    def load_config_file(self):
        if not os.path.exists(ConfigHandler.FILENAME):
            api_token = str(input("Give the API-token: "))
            name = str(input("Give your name: "))
            timezone = str(input("Give your timezone (e.a. Europe/Amsterdam): "))
            self.create_config_file(api_token, name, timezone)
        config.read(ConfigHandler.FILENAME)
        self.check_config_file()

    def get(self, section, value):
        self.load_config_file()
        return config.get(section, value)

    def get_data(self, section):
        self.load_config_file()
        data = {}
        for key, val in config.items(section):
            data[key] = val
        return data

    @staticmethod
    def update_config_file(section, key, value):
        config.set(section, key, value)
        with open(ConfigHandler.FILENAME, "w") as cfgfile:
            config.write(cfgfile)

    @staticmethod
    def create_config_file(api_token, name, timezone):
        config.add_section("auth")
        config.set("auth", "api_token", api_token)
        config.add_section("profile")
        config.set("profile", "name", name)
        config.set("profile", "balance", "100.00")
        config.set("profile", "timezone", timezone)
        config.set("profile", "date_format", "d-m-Y")
        config.add_section("betting_files")
        config.set("betting_files", "open_bets", "betting_files/open_bets.csv")
        config.set("betting_files", "closed_bets", "betting_files/closed_bets.csv")
        config.set(
            "betting_files", "balance_history", "betting_files/balance_history.csv"
        )
        with open(ConfigHandler.FILENAME, "w") as cfgfile:
            config.write(cfgfile)

    @staticmethod
    def get_missing_data_config():
        keys = []
        missing_options = []
        sections = [section for section in config.sections()]
        missing_sections = [
            x for x in ["auth", "profile", "betting_files"] if x not in sections
        ]
        for section in config.sections():
            keys.extend([key for (key, val) in config.items(section)])
            missing_options.extend(
                [(key, val) for (key, val) in config.items(section) if val == ""]
            )
        missing_keys = [
            x
            for x in [
                "api_token",
                "name",
                "balance",
                "timezone",
                "date_format",
                "open_bets",
                "closed_bets",
            ]
            if x not in keys
        ]
        return missing_sections, missing_keys, missing_options

    def check_config_file(self):
        missing_sections, missing_keys, missing_options = self.get_missing_data_config()
        for missing_key in missing_keys:
            if missing_key not in [
                "balance",
                "date_format",
                "open_bets",
                "closed_bets",
            ]:
                value = str(input(f"Give the value for {missing_key}: "))
            elif missing_key == "balance":
                value = "100"
            elif missing_key == "date_format":
                value = "d-m-Y"
            elif missing_key == "open_bets":
                value = "betting_files/open_bets.csv"
            else:
                value = "betting_files/closed_bets.csv"
            if missing_key in ["name", "balance", "timezone", "date_format"]:
                if "profile" in missing_sections:
                    config.add_section("profile")
                self.update_config_file("profile", missing_key, value)
            elif missing_key == "api_key":
                if "auth" in missing_sections:
                    config.add_section("auth")
                self.update_config_file("auth", missing_key, value)
            elif missing_key in ["open_bets", "closed_bets", "balance_history"]:
                if "betting_files" in missing_sections:
                    config.add_section("betting_files")
                self.update_config_file("betting_files", missing_key, value)
            missing_sections, missing_keys, missing_options = (
                self.get_missing_data_config()
            )
        for missing_option in missing_options:
            if missing_option[0] not in [
                "balance",
                "date_format",
                "open_bets",
                "closed_bets",
            ]:
                value = str(input(f"Give the value for {missing_option[0]}: "))
            elif missing_option[0] == "balance":
                value = "100"
            elif missing_option[0] == "date_format":
                value = "d-m-Y"
            elif missing_option[0] == "open_bets":
                value = "betting_files/open_bets.csv"
            else:
                value = "betting_files/closed_bets.csv"
            if missing_option[0] in ["name", "balance", "timezone", "date_format"]:
                self.update_config_file("profile", missing_option[0], value)
            elif missing_option[0] == "api_key":
                self.update_config_file("auth", missing_option[0], value)
            elif missing_option[0] in ["open_bets", "closed_bets"]:
                self.update_config_file("betting_files", missing_option[0], value)
