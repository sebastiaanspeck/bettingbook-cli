import os
import click

from get_data import GetData
from exceptions import IncorrectParametersException
from writers import get_writer
import leagueids

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

config = ConfigParser()

LEAGUE_IDS = leagueids.LEAGUE_IDS


def create_config_file(apikey, name, filename):
    config.add_section('auth')
    config.set('auth', 'api_key', apikey)
    config.add_section('profile')
    config.set('profile', 'name', name)
    config.set('profile', 'balance', 100)
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
    missing_keys = [x for x in ['api_key', 'name', 'balance'] if x not in keys]
    return missing_sections, missing_keys, missing_options


def check_config_file(filename):
    missing_sections, missing_keys, missing_options = get_missing_data_config()
    for missing_key in missing_keys:
        if missing_key != "balance":
            value = str(input(f"Give the value for {missing_key}: "))
        else:
            value = "100"
        if missing_key in ["name", "balance"]:
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
        if missing_option[0] in ["name", "balance"]:
            update_config_file("profile", missing_option[0], value, filename)
        elif missing_option[0]:
            update_config_file("auth", missing_option[0], value, filename)


def update_config_file(section, key, value, filename):
    config.set(section, key, value)
    with open(filename, 'w') as cfgfile:
        config.write(cfgfile)


def load_config_file():
    global api_key
    filename = os.path.join(os.getcwd(), 'config.ini')
    if not os.path.exists(filename):
        apikey = str(input("Give the API-key: "))
        name = str(input("Give your name: "))
        create_config_file(apikey, name, filename)
    config.read(filename)
    check_config_file(filename)
    api_key = config.get('auth', 'api_key')


@click.command()
@click.option('--apikey', default=load_config_file,
              help="API key to use.")
@click.option('--today', is_flag=True,
              help="Shows matches from various leagues for today.")
@click.option('--live', is_flag=True,
              help="Shows live scores from various leagues.")
@click.option('--stdout', 'output_format', flag_value='stdout', default=True,
              help="Print to stdout.")
@click.option('-o', '--output-file', default=None,
              help="Save output to a file (only if csv or json option is provided).")
def main(apikey, today, live, output_format, output_file):
    """
    A CLI to "bet" on football games.

    League codes:

    - GB1: English Premier League
    - FR1: French Ligue 1
    - DE1: German Bundesliga
    - IT1: Serie A
    - NL1: Eredivisie
    - ES1: Primera Division
    """
    params = {'api_token': api_key,
              'tz': 'Europe/Amsterdam'}

    try:
        if output_format == 'stdout' and output_file:
            raise IncorrectParametersException('Printing output to stdout and saving to a file are mutually exclusive')
        writer = get_writer(output_format)
        gd = GetData(params, LEAGUE_IDS, writer)

        if today:
            gd.get_today_scores()
            return
        if live:
            gd.get_live_scores()

    except IncorrectParametersException as e:
        click.secho(str(e), fg="red", bold=True)


if __name__ == '__main__':
    main()
