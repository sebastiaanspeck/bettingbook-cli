import os
import click
import json

from get_data import GetData
from exceptions import IncorrectParametersException
from writers import get_writer

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
    config.set('profile', 'balance', 100)
    config.set('profile', 'timezone', timezone)
    with open(filename, 'w') as cfgfile:
        config.write(cfgfile)


def get_missing_data_config():
    keys = []
    missing_options = []
    sections = [section for section in config.sections()]
    missing_sections = [x for x in ['auth', 'profile'] if x not in sections]
    for section in config.sections():
        keys.extend([key for (key, val) in config.items(section)])
        missing_options.extend([(key, val) for (key, val) in config.items(section) if val == ""])
    missing_keys = [x for x in ['api_key', 'name', 'balance', 'timezone'] if x not in keys]
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
        elif missing_key:
            if "auth" in missing_sections:
                config.add_section('auth')
            update_config_file("auth", missing_key, value, filename)
        missing_sections, missing_keys, missing_options = get_missing_data_config()
    for missing_option in missing_options:
        if missing_option[0] != "balance":
            value = str(input(f"Give the value for {missing_option[0]}: "))
        else:
            value = "100"
        if missing_option[0] in ["name", "balance", "timezone"]:
            update_config_file("profile", missing_option[0], value, filename)
        elif missing_option[0]:
            update_config_file("auth", missing_option[0], value, filename)


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
@click.option('--profile', '-P', is_flag=True,
              help="Show your profile (name, balance, timezone)")
def main(apikey, timezone, live, today, matches, standings, league, days, history, details, odds, profile):
    """
    A CLI to "bet" on football games.

    League codes:

    \b
    - GB1: English Premier League
    - FR1: French Ligue 1
    - DE1: German Bundesliga
    - IT1: Serie A
    - NL1: Eredivisie
    - ES1: Primera Division
    """
    params = {}
    if apikey:
        params['api_token'] = apikey
    else:
        params['api_token'] = config.get('auth', 'api_key')
    if timezone:
        params['tz'] = timezone
    else:
        params['tz'] = config.get('profile', 'timezone')

    profile_data = {}
    for (key, val) in config.items('profile'):
        profile_data[key] = val

    try:
        writer = get_writer()
        gd = GetData(params, LEAGUES_DATA, writer)

        if live:
            if history:
                raise IncorrectParametersException('--history and --days is not supported for --live. '
                                                   'Use --matches to use these parameters')
            gd.get_matches('livescores/now',
                           ["No live action currently", "There was problem getting live scores, check your parameters"],
                           league, days, history, details, odds, type_sort="live")
            return

        if today:
            if history:
                raise IncorrectParametersException('--history and --days is not supported for --today. '
                                                   'Use --matches to use these parameters')
            gd.get_matches('livescores',
                           ["No matches today", "There was problem getting todays scores, check your parameters"],
                           league, days, history, details, odds, type_sort="today")
            return

        if matches:
            gd.get_matches('fixtures/between/',
                           [[f"No matches in the past {str(days)} days."],
                            [f"No matches in the coming {str(days)} days."]],
                           league, days, history, details, odds, type_sort="matches")
            return

        if standings:
            if not league:
                raise IncorrectParametersException('Please specify a league. '
                                                   'Example --standings --league=EN1')
            if history:
                raise IncorrectParametersException('--history and --days is not supported for --standings. '
                                                   'Use --matches to use these parameters')
            if details:
                raise IncorrectParametersException('--details is not supported for --standings. '
                                                   'Use --matches, --live or --today to use these parameters')
            if league.endswith('C'):
                raise IncorrectParametersException(f'Standings for {league} not supported')
            gd.get_standings(league)
            return

        if profile:
            gd.show_profile(profile_data)
            return

    except IncorrectParametersException as e:
        click.secho(str(e), fg="red", bold=True)


if __name__ == '__main__':
    main()
