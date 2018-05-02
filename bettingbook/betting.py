import click
import os

import convert

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

config = ConfigParser()


def check_for_files(files):
    for file in files:
        filename = os.path.join(os.getcwd(), file)
        if not os.path.exists(filename):
            with open(file, "w"):
                pass


def load_balance():
    balance = 0
    filename = os.path.join(os.getcwd(), 'config.ini')
    config.read(filename)
    for (key, val) in config.items('profile'):
        if key == 'balance':
            balance = val
    balance = convert.convert_float_to_curreny(balance)
    return balance


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


def get_input(balance):
    team = click.prompt("On which team do you want to bet? (1, X, 2)")
    stake = convert.convert_float_to_curreny(click.prompt(f"What is your stake? (max. {balance})"))
    while team.upper() not in ["1", "X", "2"]:
        print("Oops... You didn't entered 1, X or 2. Try again.")
        team = click.prompt("On which team do you want to bet? (1, X, 2)")
    while stake > balance:
        print("Oops... You entered a stake higher than your balance. Try again.")
        stake = convert.convert_float_to_curreny(click.prompt(f"What is your stake? (max. {balance})"))
    return team, stake


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


def update_balance(stake, balance):
    balance = balance - stake
    config.set('profile', 'balance', str(balance))
    with open('config.ini', 'w') as cfgfile:
        config.write(cfgfile)
    click.secho(f"Updated balance: {balance}")


def write_to_active_odds(match_id, prediction, odd, stake):
    f = open('active_odds.csv', 'w')
    f.write(f"{match_id},{prediction},{odd},{stake}\n")
    f.close()


def place_bet(match):
    balance = load_balance()
    odds = get_odds(match)
    click.echo(f"Betting on {match['localTeam']['data']['name']} vs {match['visitorTeam']['data']['name']} in "
               f"{match['league']['data']['name']} with odds: 1: {odds[0]}, X: {odds[1]}, 2: {odds[2]}")
    prediction, stake = get_input(balance)
    stake = convert.convert_float_to_curreny(stake)
    potential_wins, odd = calculate_potential_wins(prediction, stake, odds)
    if get_confirmation(prediction, stake, potential_wins):
        update_balance(stake, balance)
        write_to_active_odds(match['id'], prediction, odd, stake)


def main(matches):
    check_for_files(['active_odds.csv', 'finished_odds.csv'])
    click.clear()
    click.secho("Matches on which you want to bet:")
    for match in matches:
        place_bet(match)
