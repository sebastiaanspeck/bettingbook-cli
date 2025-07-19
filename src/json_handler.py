import os
import json


class JsonHandler(object):
    LEAGUES_FILENAME = os.path.join(os.getcwd(), "league_files/leagues.json")

    def __init__(self):
        pass

    def load_leagues(self):
        """Load JSON file at app start"""
        here = os.path.dirname(os.getcwd())
        with open(os.path.join(here, self.LEAGUES_FILENAME)) as json_file:
            data = json.load(json_file)
        return data["leagues"]

    # TODO MAKE A FUNCTION TO CREATE A leagues_from_plan.json BASED ON THE LEAGUES IN
    #  THE SPORTMONKS API PLAN (SEE POSSIBLE LEAGUES)
