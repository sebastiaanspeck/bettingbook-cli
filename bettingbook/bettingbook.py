import os
import click
import json
from collections import namedtuple

from request_handler import RequestHandler
from exceptions import IncorrectParametersException
from writers import get_writer
from betting import Betting

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

config = ConfigParser()


def load_json(file):
    """Load JSON file at app start"""
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, file)) as jfile:
        data = json.load(jfile)
    return data


LEAGUES_DATA = load_json("leagues.json")['leagues']
LEAGUES = [list(x.keys())[0] for x in LEAGUES_DATA]


def create_config_file(apikey, name, timezone, filename):
    config.add_section('auth')
    config.set('auth', 'api_key', apikey)
    config.add_section('profile')
    config.set('profile', 'name', name)
    config.set('profile', 'balance', '100.00')
    config.set('profile', 'timezone', timezone)
    config.add_section('files')
    config.set('betting_files', 'open_bets', 'betting_files/open_bets')
    config.set('betting_files', 'closed_bets', 'betting_files/closed_bets')
    with open(filename, 'w') as cfgfile:
        config.write(cfgfile)


def get_missing_data_config():
    keys = []
    missing_options = []
    sections = [section for section in config.sections()]
    missing_sections = [x for x in ['auth', 'profile', 'betting_files'] if x not in sections]
    for section in config.sections():
        keys.extend([key for (key, val) in config.items(section)])
        missing_options.extend([(key, val) for (key, val) in config.items(section) if val == ""])
    missing_keys = [x for x in ['api_key', 'name', 'balance', 'timezone', 'open_bets', 'closed_bets'] if x not in keys]
    return missing_sections, missing_keys, missing_options


def check_config_file(filename):
    missing_sections, missing_keys, missing_options = get_missing_data_config()
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
        missing_sections, missing_keys, missing_options = get_missing_data_config()
    for missing_option in missing_options:
        if missing_option[0] != "balance":
            value = str(input(f"Give the value for {missing_option[0]}: "))
        else:
            value = "100"
        if missing_option[0] in ["name", "balance", "timezone"]:
            update_config_file("profile", missing_option[0], value, filename)
        if missing_option[0] == "api_key":
            update_config_file("auth", missing_option[0], value, filename)
        if missing_option[0] in ["open_bets", "closed_bets"]:
            update_config_file("betting_files", missing_option[0], value, filename)


def update_config_file(section, key, value, filename):
    config.set(section, key, value)
    with open(filename, 'w') as cfgfile:
        config.write(cfgfile)


def load_config_file():
    filename = os.path.join(os.getcwd(), 'config.ini')
    if not os.path.exists(filename):
        apikey = str(input("Give the API-key: "))
        name = str(input("Give your name: "))
        timezone = str(input("Give your timezone (e.a. Europe/Amsterdam): "))
        create_config_file(apikey, name, timezone, filename)
    config.read(filename)
    check_config_file(filename)


def get_params(apikey, timezone):
    params = {}
    if apikey:
        params['api_token'] = apikey
    else:
        params['api_token'] = config.get('auth', 'api_key')
    if timezone:
        params['tz'] = timezone
    else:
        params['tz'] = config.get('profile', 'timezone')
    return params


def get_data(section):
    data = {}
    for (key, val) in config.items(section):
        data[key] = val
    return data


def check_options(history, bet, live, today, refresh, matches):
    if history and live or history and today:
        raise IncorrectParametersException('--history and --days is not supported for --live/--today. '
                                           'Use --matches to use these parameters')
    if bet and live:
        raise IncorrectParametersException('--bet is not supported for --live. '
                                           'Use --matches or --today to use this parameters')
    if matches and refresh:
        raise IncorrectParametersException('--refresh is not supported for --matches. '
                                           'Use --live or --today to use this parameters')


def check_options_standings(league, history):
    if not league:
        raise IncorrectParametersException('Please specify a league. '
                                           'Example --standings --league=EN1')
    if history:
        raise IncorrectParametersException('--history and --days is not supported for --standings. '
                                           'Use --matches to use these parameters')
    if league.endswith('C') and league not in ["WC", "EC"]:
        raise IncorrectParametersException(f'Standings for {league} not supported')


@click.command()
@click.option('--apikey', default=load_config_file,
              help="API key to use.")
@click.option('--timezone', default=load_config_file,
              help="Timezone to use. See https://bit.ly/2glGdNY "
                   "for a list of accepted timezones")
@click.option('--live', '-L', is_flag=True,
              help="Shows live scores from various leagues.")
@click.option('--today', '-T', is_flag=True,
              help="Shows matches from various leagues for today.")
@click.option('--matches', '-M', is_flag=True,
              help="Shows matches from various leagues for a longer period.")
@click.option('--standings', '-S', is_flag=True,
              help="Standings for a particular league.")
@click.option('--league', '-l', type=click.Choice(LEAGUES),
              help="Show fixtures from a particular league.")
@click.option('--days', '-d', default=7, show_default=True,
              help=("The number of days in the future for which you "
                    "want to see the scores, or the number of days "
                    "in the past when used with --history"))
@click.option('--history', '-H', is_flag=True, default=False, show_default=True,
              help="Displays past games when used with --time command.")
@click.option('--details', '-D', is_flag=True, default=False, show_default=True,
              help="Displays goal-scorers under the score.")
@click.option('--odds', '-O', is_flag=True, default=False, show_default=True,
              help="Displays the odds above the score.")
@click.option('--refresh', '-R', is_flag=True, default=False, show_default=True,
              help="Refresh the data every minute.")
@click.option('--bet', '-B', is_flag=True, default=False, show_default=True,
              help="Place a bet.")
@click.option('--profile', '-P', is_flag=True,
              help="Show your profile (name, balance, timezone)")
@click.option('--all-bets', '-AB', is_flag=True,
              help="Show all your bets")
@click.option('--open-bets', '-OB', is_flag=True,
              help="Show your open bets")
@click.option('--closed-bets', '-CB', is_flag=True,
              help="Show your closed bets")
def main(apikey, timezone, live, today, matches, standings, league, days, history, details, odds, refresh, bet, profile,
         all_bets, open_bets, closed_bets):
    params = get_params(apikey, timezone)
    profile_data = get_data('profile')
    betting_files = get_data('betting_files')

    try:
        writer = get_writer()
        rh = RequestHandler(params, LEAGUES_DATA, writer, profile_data, betting_files)
        betting = Betting(params, LEAGUES_DATA, writer, profile_data, betting_files)

        Parameters = namedtuple("parameters", "url, msg, league_name, days, "
                                "show_history, show_details, show_odds, refresh, place_bet, type_sort")

        if live or today or matches:
            check_options(history, bet, live, today, refresh, matches)
            if bet:
                odds = True
            if live:
                parameters = Parameters('livescores/now',
                                        ["No live action currently",
                                         "There was problem getting live scores, check your parameters"],
                                        league, days, history, details, odds, refresh, bet, "live")
            elif today:
                parameters = Parameters('livescores',
                                        ["No matches today",
                                         "There was problem getting todays scores, check your parameters"],
                                        league, days, history, details, odds, refresh, bet, "today")
            else:
                parameters = Parameters('fixtures/between/',
                                        [[f"No matches in the past {str(days)} days."],
                                         [f"No matches in the coming {str(days)} days."]],
                                        league, days, history, details, odds, refresh, bet, "matches")
            rh.get_matches(parameters)
            return

        if standings:
            check_options_standings(league, history)
            rh.get_standings(league, details)
            return

        if profile:
            rh.show_profile(profile_data)
            return

        if all_bets:
            betting.view_bets('open')
            betting.view_bets('closed')

        if open_bets:
            betting.view_bets('open')

        if closed_bets:
            betting.view_bets('closed')

    except IncorrectParametersException as e:
        click.secho(str(e), fg="red", bold=True)


if __name__ == '__main__':
    main()
