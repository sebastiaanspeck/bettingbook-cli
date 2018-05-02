import click
import os
import csv

import convert
import request_handler


try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

config = ConfigParser()


class Betting(object):
    def __init__(self, params, league_data, writer):
        self.params = params
        self.league_data = league_data
        self.writer = writer
        self.balance = ''

    @staticmethod
    def check_for_files(files):
        for file in files:
            filename = os.path.join(os.getcwd(), file)
            if not os.path.exists(filename):
                with open(file, "w"):
                    pass

    def load_balance(self):
        filename = os.path.join(os.getcwd(), 'config.ini')
        config.read(filename)
        for (key, val) in config.items('profile'):
            if key == 'balance':
                self.balance = val
        self.balance = convert.convert_float_to_curreny(self.balance)

    def check_active_odds(self):
        rh = request_handler.RequestHandler(self.params, self.league_data, self.writer)
        with open('active_odds.csv', 'r') as f:
            reader = list(csv.reader(f))
            for i, row in enumerate(reader):
                match_data = rh.get_match_bet(row[0])[0]
                if match_data['time']['status'] in ["FT"]:
                    self.calculate_winning_odd(match_data, i, row, reader)

    def calculate_winning_odd(self, match_data, i, row, reader):
        winning_team = self.writer.calculate_winning_team(match_data["scores"]["localteam_score"],
                                                          match_data["scores"]["visitorteam_score"],
                                                          match_data['time']['status'])
        predicted_team = row[1]
        potential_wins = row[2]
        if winning_team == 0 and predicted_team == '1' or winning_team == 1 and predicted_team == 'X' or \
           winning_team == 2 and predicted_team == '2':
            click.echo(f"Woohoo! You predicited {match_data['visitorTeam']['data']['name']} - "
                       f"{match_data['visitorTeam']['data']['name']} correct")
            self.update_balance(convert.convert_float_to_curreny(potential_wins), operation='win')
        else:
            click.echo(f"Ah noo! You predicited {match_data['visitorTeam']['data']['name']} - "
                       f"{match_data['visitorTeam']['data']['name']} incorrect")
        self.write_to_finished_odds(row)
        del reader[i][0:]
        self.update_active_odds(reader)

    @staticmethod
    def get_odds(match):
        odds = []
        for i, odd in enumerate(match["flatOdds"]["data"]):
            if match["flatOdds"]["data"][i]["market_id"] == 1:
                odds = odd["odds"]
        for i, _ in enumerate(odds):
            if len(str(odds[i]["value"])) <= 3:
                odds[i]["value"] = "{0:.2f}".format(odds[i]["value"])
            if len(str(odds[i]["value"])) > 4:
                odds[i]["value"] = "{0:.1f}".format(float(odds[i]["value"]))
            if odds[i]["label"] == "1":
                home_odd = odds[i]["value"]
            elif odds[i]["label"] == "2":
                away_odd = odds[i]["value"]
            elif odds[i]["label"] == "X":
                draw_odd = odds[i]["value"]
        odds = [home_odd, draw_odd, away_odd]
        return odds

    @staticmethod
    def get_league_name(match):
        league_name = convert.convert_leagueid_to_leaguename(match['league_id'])
        league_prefix = match['league']['data']['name']
        if league_prefix == league_name:
            league_name = league_name
        else:
            league_name = league_name + ' - ' + league_prefix
        return league_name

    def get_input(self):
        prediction = self.get_prediction()
        stake = self.get_stake()
        return prediction, stake

    @staticmethod
    def get_prediction():
        prediction = click.prompt("On which team do you want to bet? (1, X, 2)")
        while prediction.upper() not in ["1", "X", "2"]:
            print("Oops... You didn't entered 1, X or 2. Try again.")
            prediction = click.prompt("On which team do you want to bet? (1, X, 2)")
        return prediction

    def get_stake(self):
        stake = convert.convert_float_to_curreny(click.prompt(f"What is your stake? (max. {self.balance})"))
        while stake > self.balance or stake <= 0:
            print("Oops... You entered a stake higher than your balance or an invalid stake. Try again.")
            stake = convert.convert_float_to_curreny(click.prompt(f"What is your stake? (max. {self.balance})"))
        return stake

    @staticmethod
    def calculate_potential_wins(team, stake, odds):
        if team == "1":
            odd = odds[0]
        elif team == "X":
            odd = odds[1]
        else:
            odd = odds[2]
        odd = convert.convert_float_to_curreny(odd)
        potential_wins = convert.convert_float_to_curreny(stake*odd)
        return potential_wins, odd

    @staticmethod
    def get_confirmation(prediction, stake, potential_wins):
        confirmation = click.prompt(f"Are you sure to bet that team {prediction} will win with a stake of {stake}? "
                                    f"This can result in a potential win of {potential_wins}. (Y/N)")
        while confirmation.upper() not in ["Y", "N"]:
            print("Oops... You didn't entered Y or N. Try again.")
            confirmation = click.prompt(f"Are you sure to bet team {prediction} will win with a stake of {stake}? "
                                        f"This can result in a potential win of {potential_wins}. (Y/N)")
        if confirmation.upper() == "Y":
            return True
        else:
            return False

    def update_balance(self, stake, operation):
        if operation == 'loss':
            self.balance = self.balance - stake
        elif operation == 'win':
            self.balance = self.balance + stake
        config.set('profile', 'balance', str(self.balance))
        with open('config.ini', 'w') as cfgfile:
            config.write(cfgfile)
        click.secho(f"Updated balance: {self.balance}")

    @staticmethod
    def write_to_active_odds(match_id, prediction, potential_wins):
        with open('active_odds.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([match_id, prediction, potential_wins])

    @staticmethod
    def update_active_odds(data):
        with open('active_odds.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            for line in data:
                writer.writerow(line)

    @staticmethod
    def write_to_finished_odds(row):
        with open('finished_odds.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(row)

    def place_bet(self, match):
        odds = self.get_odds(match)
        league_name = self.get_league_name(match)
        click.echo(f"Betting on {match['localTeam']['data']['name']} - {match['visitorTeam']['data']['name']} in "
                   f"{league_name} with odds:\n1: {odds[0]}, X: {odds[1]}, 2: {odds[2]}")
        prediction, stake = self.get_input()
        stake = convert.convert_float_to_curreny(stake)
        potential_wins, odd = self.calculate_potential_wins(prediction, stake, odds)
        if self.get_confirmation(prediction, stake, potential_wins):
            self.update_balance(stake, 'loss')
            self.write_to_active_odds(match['id'], prediction, potential_wins)
        else:
            print("Your bet is canceled")

    def main(self, matches):
        self.check_for_files(['active_odds.csv', 'finished_odds.csv'])
        self.load_balance()
        self.check_active_odds()
        click.secho("\nMatches on which you want to bet:\n")
        for match in matches:
            self.place_bet(match)
