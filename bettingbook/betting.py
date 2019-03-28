import click
import os
import csv
import datetime

import convert
import request_handler


try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

config = ConfigParser()


class Betting(object):
    def __init__(self, params, league_data, writer, profile_data, betting_files):
        self.params = params
        self.league_data = league_data
        self.writer = writer
        self.profile_data = profile_data
        self.betting_files = betting_files

    @staticmethod
    def check_for_files(files):
        for file in files:
            filename = os.path.join(os.getcwd(), file)
            if not os.path.exists(filename):
                with open(file, "w"):
                    pass

    @staticmethod
    def load_config_file():
        filename = os.path.join(os.getcwd(), 'config.ini')
        config.read(filename)

    @staticmethod
    def get_bets(filename):
        with open(filename, 'r') as f:
            reader = list(csv.reader(f))
        return reader

    def write_to_open_bets(self, data):
        with open(self.betting_files['open_bets'], 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(data)
        self.remove_empty_lines_csv_file(self.betting_files['open_bets'])

    def update_open_bets(self, data):
        with open(self.betting_files['open_bets'], 'w', newline='') as f:
            writer = csv.writer(f)
            for line in data:
                writer.writerow(line)
        self.remove_empty_lines_csv_file(self.betting_files['open_bets'])

    def write_to_closed_bets(self, row):
        with open(self.betting_files['closed_bets'], 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(row)
        self.remove_empty_lines_csv_file(self.betting_files['closed_bets'])

    @staticmethod
    def remove_empty_lines_csv_file(file):
        try:
            file_object = open(file, 'r')
            lines = csv.reader(file_object, delimiter=',', quotechar='"')
            flag = 0
            data = []
            for line in lines:
                if not line:
                    flag = 1
                    continue
                else:
                    data.append(line)
            file_object.close()
            if flag == 1:  # if blank line is present in file
                file_object = open(file, 'w')
                for line in data:
                    str1 = ','.join(line)
                    file_object.write(str1 + "\n")
                file_object.close()
        except Exception as e:
            click.secho(e)

    def check_open_bets(self):
        rh = request_handler.RequestHandler(self.params, self.league_data, self.writer,
                                            self.profile_data, self.betting_files)
        reader = self.get_bets(self.betting_files['open_bets'])
        for i, row in enumerate(reader):
            match_data = rh.get_match_bet(row[0])[0]
            if match_data['time']['status'] in ['FT']:
                self.calculate_winning_odd(match_data, i, row, reader)

    def calculate_winning_odd(self, match_data, i, row, reader):
        winning_team = self.writer.calculate_winning_team(match_data['scores']['localteam_score'],
                                                          match_data['scores']['visitorteam_score'],
                                                          match_data['time']['status'])
        predicted_team = row[1]
        potential_wins = row[2]
        if winning_team == 0 and predicted_team == '1' or winning_team == 1 and predicted_team == 'X' or \
           winning_team == 2 and predicted_team == '2':
            click.echo(f"Woohoo! You predicted {match_data['localTeam']['data']['name']} - "
                       f"{match_data['visitorTeam']['data']['name']} correct and won {potential_wins}")
            self.update_balance(convert.convert_float_to_curreny(potential_wins), operation='win')
            row.extend((winning_team, "yes"))
        else:
            click.echo(f"Ah noo! You predicted {match_data['localTeam']['data']['name']} - "
                       f"{match_data['visitorTeam']['data']['name']} incorrect")
            row.extend((winning_team, "no"))
        self.write_to_closed_bets(row)
        del reader[i][0:]
        self.update_open_bets(reader)

    def get_odds(self, match):
        def highest_odd(odd_in):
            try:
                return max(odd_in)
            except ValueError:
                return '0.00'

        odds_dict = {"1": [], "X": [], "2": []}
        for bookmaker in match["odds"]["data"]:
            if bookmaker['name'] == "3Way Result":
                for odds in bookmaker["bookmaker"]["data"]:
                    for odd in odds["odds"]["data"]:
                        odds_dict = self.fill_odds(odd, odds_dict)

        for label, values in odds_dict.items():
            odd = highest_odd(values)
            if len(str(odd)) <= 3:
                odd = "{0:.2f}".format(float(odd))
            if len(str(odd)) > 4:
                odd = "{0:.1f}".format(float(odd))
            if label == "1":
                home_odd = odd
            elif label == "X":
                draw_odd = odd
            else:
                away_odd = odd

        odds = [home_odd, draw_odd, away_odd]
        return odds

    @staticmethod
    def fill_odds(odd, odds):
        odds[odd["label"]].append(str(odd["value"]))
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
        while prediction.upper() not in ['1', 'X', '2']:
            click.secho("Oops... You didn't entered 1, X or 2. Try again.", fg="red", bold=True)
            prediction = click.prompt("On which team do you want to bet? (1, X, 2)")
        return prediction

    def get_stake(self):
        stake = convert.convert_float_to_curreny(click.prompt(f"What is your stake? (max. "
                                                              f"{self.profile_data['balance']})", type=float))
        balance = convert.convert_float_to_curreny(self.profile_data['balance'])
        while stake > balance or stake <= 0:
            click.secho("Oops... You entered a stake higher than your balance or an invalid stake. Try again.",
                        fg="red", bold=True)
            stake = convert.convert_float_to_curreny(click.prompt(f"What is your stake? (max. "
                                                                  f"{self.profile_data['balance']})"))
        return stake

    @staticmethod
    def get_confirmation(prediction, stake, potential_wins):
        msg = convert.convert_prediction_to_msg(prediction)
        confirmation = click.prompt(f"Are you sure that the match will result in a {msg} with a stake of {stake}? "
                                    f"This can result in a potential win of {potential_wins}. (Y/N)")
        while confirmation.upper() not in ['Y', 'N']:
            click.secho("Oops... You didn't entered Y or N. Try again.", fg="red", bold=True)
            confirmation = click.prompt(f"{msg} with a stake of {stake}? "
                                        f"This can result in a potential win of {potential_wins}. (Y/N)")
        if confirmation.upper() == "Y":
            return True
        else:
            return False

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

    def update_balance(self, stake, operation):
        balance = convert.convert_float_to_curreny(self.profile_data['balance'])
        if operation == 'loss':
            balance = balance - stake
        elif operation == 'win':
            balance = balance + stake
        config.set('profile', 'balance', str(balance))
        with open('config.ini', 'w') as cfgfile:
            config.write(cfgfile)
        click.secho(f"Updated balance: {balance}")

    def place_bet(self, matches):
        self.main()
        click.secho("\nMatches on which you want to bet:\n")
        for match in matches:
            self.place_bet_match(match)

    def place_bet_match(self, match):
        odds = self.get_odds(match)
        league_name = self.get_league_name(match)
        date = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')
        click.echo(f"Betting on {match['localTeam']['data']['name']} - {match['visitorTeam']['data']['name']} in "
                   f"{league_name} with odds:\n1: {odds[0]}, X: {odds[1]}, 2: {odds[2]}")
        prediction, stake = self.get_input()
        stake = convert.convert_float_to_curreny(stake)
        potential_wins, odd = self.calculate_potential_wins(prediction, stake, odds)
        data = [prediction, stake, potential_wins, odd, match, date]
        self.place_bet_confirmation(data)

    def place_bet_confirmation(self, daty):
        if self.get_confirmation(daty[0], daty[1], daty[2]):
            self.update_balance(daty[1], 'loss')
            data = [daty[4]['id'], daty[0], daty[1], daty[2], daty[3],
                    daty[4]['localTeam']['data']['name'], daty[4]['visitorTeam']['data']['name'],
                    convert.convert_time(daty[4]["time"]["starting_at"]["date_time"]), daty[5]]
            self.write_to_open_bets(data)
        else:
            click.secho("Your bet is canceled\n")

    def view_bets(self, type_sort):
        self.main()
        bets = sorted(self.get_bets(f'betting_files/{type_sort}_bets.csv'), key=lambda x: (x[7]))
        if len(bets) == 0:
            click.secho(f"\nNo {type_sort} bets found.", fg="red", bold=True)
        else:
            click.secho(f"\n{type_sort.title()} bets:", bold=True)
            if type_sort == 'open':
                click.secho(f"{'MATCH':50} {'PREDICTION':15} {'ODD':10} {'STAKE':10} {'POTENTIAL WINS':20} "
                            f"{'DATE AND TIME':20}", bold=True)
            else:
                click.secho(f"{'MATCH':50} {'PREDICTION':15} {'ODD':10} {'STAKE':10} {'POTENTIAL WINS':20} "
                            f"{'DATE AND TIME':20} {'RESULT':10} {'CORRECT':10}", bold=True)
            for bet in bets:
                if type_sort == 'open':
                    bet_str = f"{bet[5]+' - '+bet[6]:<50} {bet[1]:<15} {bet[4]:<10} " \
                              f"{bet[2]:<10} {bet[3]:<20} {bet[7]:<20}"
                else:
                    bet_str = f"{bet[5]+' - '+bet[6]:<50} {bet[1]:<15} {bet[4]:<10} " \
                              f"{bet[2]:<10} {bet[3]:<20} {bet[7]:<20} {bet[9]:<10} {bet[10]:<10}"
                click.secho(bet_str)

    def main(self):
        self.check_for_files(self.betting_files.values())
        self.load_config_file()
        self.check_open_bets()
