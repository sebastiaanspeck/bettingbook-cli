import click
import os
import csv
import datetime

import convert

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

config = ConfigParser()


class Betting(object):
    def __init__(self, params, league_data, writer, request_handler, config_handler):
        self.params = params
        self.league_data = league_data
        self.writer = writer
        self.request_handler = request_handler
        self.config_handler = config_handler

    @staticmethod
    def check_for_files(files):
        for file in files:
            filename = os.path.join(os.getcwd(), file)
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            if not os.path.exists(filename):
                with open(filename, "w+"):

    @staticmethod
    def get_bets(filename):
        with open(filename, "r") as f:
            reader = list(csv.reader(f))
        return reader

    def write_to_bets_file(self, data, bet_type):
        with open(
            self.config_handler.get_data("betting_files")[bet_type], "a", newline=""
        ) as f:
            writer = csv.writer(f)
            writer.writerow(data)
        self.remove_empty_lines_csv_file(
            self.config_handler.get_data("betting_files")[bet_type]
        )

    def update_open_bets_file(self, data):
        with open(
            self.config_handler.get_data("betting_files")["open_bets"], "w", newline=""
        ) as f:
            writer = csv.writer(f)
            for line in data:
                writer.writerow(line)
        self.remove_empty_lines_csv_file(
            self.config_handler.get_data("betting_files")["open_bets"]
        )

    @staticmethod
    def remove_empty_lines_csv_file(file):
        try:
            file_object = open(file, "r")
            lines = csv.reader(file_object, delimiter=",", quotechar='"')
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
                file_object = open(file, "w")
                for line in data:
                    str1 = ",".join(line)
                    file_object.write(str1 + "\n")
                file_object.close()
        except Exception as e:
            click.secho(e)

    def check_open_bets(self):
        reader = self.get_bets(
            self.config_handler.get_data("betting_files")["open_bets"]
        )
        for i, row in enumerate(reader):
            match_data = self.request_handler.get_match_bet(row[0])[0]
            if match_data["time"]["status"] in ["FT", "AET", "FT_PEN"]:
                self.calculate_winning_odd(match_data, i, row, reader)

    def calculate_winning_odd(self, match_data, i, row, reader):
        winning_team = self.writer.calculate_winning_team(
            match_data["scores"]["localteam_score"],
            match_data["scores"]["visitorteam_score"],
            match_data["time"]["status"],
        )
        predicted_team = row[1]
        potential_wins = row[3]
        if winning_team == predicted_team:
            click.echo(
                f"Woohoo! You predicted {match_data['localTeam']['data']['name']} - "
                f"{match_data['visitorTeam']['data']['name']} correct and won {potential_wins}"
            )
            self.update_balance(
                convert.float_to_currency(potential_wins), operation="win"
            )
            row.extend((winning_team, "yes"))
        else:
            click.echo(
                f"Ah no! You predicted {match_data['localTeam']['data']['name']} - "
                f"{match_data['visitorTeam']['data']['name']} incorrect"
            )
            row.extend((winning_team, "no"))
        self.write_to_bets_file(row, "closed_bets")
        del reader[i][0:]
        self.update_open_bets_file(reader)

    def get_odds(self, match):
        def average_odd(odd_in):
            try:
                return sum(odd_in) / len(odd_in)
            except (ValueError, ZeroDivisionError):
                return 0.00

        odds_dict = {"1": [], "X": [], "2": []}
        for odds in match["flatOdds"]["data"]:
            for odd in odds["odds"]:
                odds_dict = self.fill_odds(odd, odds_dict)

        home_odd, draw_odd, away_odd = "", "", ""
        for label, values in odds_dict.items():
            odd = average_odd(values)
            odd = "{0:.2f}".format(odd)
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
        odds[odd["label"]].append(float(odd["value"]))
        return odds

    @staticmethod
    def get_league_name(match):
        league_name = convert.league_id_to_league_name(match["league_id"])
        league_prefix = match["league"]["data"]["name"]
        if league_prefix == league_name:
            league_name = league_name
        else:
            league_name = league_name + " - " + league_prefix
        return league_name

    def get_input(self):
        prediction = self.get_prediction()
        stake = self.get_stake()
        return prediction, stake

    @staticmethod
    def get_prediction():
        prediction = click.prompt("On which team do you want to bet? (1, X, 2)")
        while prediction.upper() not in ["1", "X", "2"]:
            click.secho(
                "Oops... You didn't entered 1, X or 2. Try again.", fg="red", bold=True
            )
            prediction = click.prompt("On which team do you want to bet? (1, X, 2)")
        return prediction

    def get_stake(self):
        balance = convert.float_to_currency(
            self.config_handler.get_data("profile")["balance"]
        )
        stake = convert.float_to_currency(
            click.prompt(f"What is your stake? (max. " f"{balance})", type=float)
        )
        while stake > balance or stake <= 0:
            click.secho(
                "Oops... You entered a stake higher than your balance or an invalid stake. Try again.",
                fg="red",
                bold=True,
            )
            stake = convert.float_to_currency(
                click.prompt(f"What is your stake? (max. " f"{balance})"), type=float
            )
        return stake

    @staticmethod
    def get_confirmation(prediction, stake, potential_wins):
        msg = convert.prediction_to_msg(prediction)
        return click.confirm(
            f"Are you sure that the match will result in a {msg} with a stake of {stake}? "
            f"This can result in a potential win of {potential_wins}"
        )

    @staticmethod
    def calculate_potential_wins(team, stake, odds):
        if team == "1":
            odd = odds[0]
        elif team == "X":
            odd = odds[1]
        else:
            odd = odds[2]
        odd = convert.float_to_currency(odd)
        potential_wins = convert.float_to_currency(stake * odd)
        return potential_wins, odd

    def update_balance(self, stake, operation):
        balance = convert.float_to_currency(
            self.config_handler.get_data("profile")["balance"]
        )
        if operation == "loss":
            balance = balance - stake
        elif operation == "win":
            balance = balance + stake
        self.config_handler.update_config_file("profile", "balance", str(balance))
        click.secho(f"Updated balance: {balance}\n")

    def place_bet(self, matches):
        self.main()
        click.secho("\nMatches on which you want to bet:\n")
        for match in matches:
            self.place_bet_match(match)

    def place_bet_match(self, match):
        odds = self.get_odds(match)
        league_name = self.get_league_name(match)
        date = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
        click.echo(
            f"Betting on {match['localTeam']['data']['name']} - {match['visitorTeam']['data']['name']} in "
            f"{league_name} with odds:\n1: {odds[0]}, X: {odds[1]}, 2: {odds[2]}"
        )
        prediction, stake = self.get_input()
        stake = convert.float_to_currency(stake)
        potential_wins, odd = self.calculate_potential_wins(prediction, stake, odds)
        data = [prediction, stake, potential_wins, odd, match, date]
        self.place_bet_confirmation(data)

    def place_bet_confirmation(self, data_in):
        if self.get_confirmation(data_in[0], data_in[1], data_in[2]):
            self.update_balance(data_in[1], "loss")
            data_out = [
                data_in[4]["id"],
                data_in[0],
                data_in[1],
                data_in[2],
                data_in[3],
                data_in[4]["localTeam"]["data"]["name"],
                data_in[4]["visitorTeam"]["data"]["name"],
                convert.datetime(
                    data_in[4]["time"]["starting_at"]["date_time"],
                    convert.format_date(
                        self.config_handler.get("profile", "date_format")
                    ),
                ),
                data_in[5],
            ]
            self.write_to_bets_file(data_out, "open_bets")
        else:
            click.secho("Your bet is canceled\n")

    def view_bets(self, type_sort):
        self.main()
        sort_reverse = True
        if type_sort == "open":
            sort_reverse = False
        bets = sorted(
            self.get_bets(
                self.config_handler.get_data("betting_files")[f"{type_sort}_bets"]
            ),
            key=lambda x: (x[7]),
            reverse=sort_reverse,
        )
        if len(bets) == 0:
            click.secho(f"\nNo {type_sort} bets found.", fg="red", bold=True)
        else:
            click.secho(f"\n{type_sort.title()} bets:", bold=True)
            if type_sort == "open":
                click.secho(
                    f"{'MATCH':50} {'PREDICTION':15} {'ODD':10} {'STAKE':10} {'POTENTIAL WINS':20} "
                    f"{'DATE AND TIME':20}",
                    bold=True,
                )
            else:
                click.secho(
                    f"{'MATCH':50} {'PREDICTION':15} {'ODD':10} {'STAKE':10} {'POTENTIAL WINS':20} "
                    f"{'DATE AND TIME':20} {'RESULT':10} {'CORRECT':10}",
                    bold=True,
                )
            for bet in bets:
                if type_sort == "open":
                    bet_str = (
                        f"{bet[5] + ' - ' + bet[6]:<50} {bet[1]:<15} {bet[4]:<10} "
                        f"{bet[2]:<10} {bet[3]:<20} {bet[7]:<20}"
                    )
                else:
                    bet_str = (
                        f"{bet[5] + ' - ' + bet[6]:<50} {bet[1]:<15} {bet[4]:<10} "
                        f"{bet[2]:<10} {bet[3]:<20} {bet[7]:<20} {bet[9]:<10} {bet[10]:<10}"
                    )
                click.secho(bet_str)

    def main(self):
        self.check_for_files(self.config_handler.get_data("betting_files").values())
        self.check_open_bets()
