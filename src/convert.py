import json
import os
import datetime as dt
from re import sub
from decimal import Decimal

import writers


def load_json(file):
    """Load JSON file at app start"""
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, file)) as json_file:
        data = json.load(json_file)
    return data


LEAGUES_DATA = load_json("leagues.json")["leagues"]


def league_id_to_league_name(league):
    for leagues in LEAGUES_DATA:
        league_name = list(leagues.values())[1]
        league_ids = list(leagues.values())[0]
        if str(league) in league_ids:
            return league_name
    return None


def datetime(datetime_str):
    """Converts the API UTC datetime string to the local user datetime."""
    return dt.datetime.strftime(dt.datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S'), '%d-%m-%Y %H:%M')


def date(date_str):
    """Converts the API UTC date string to the local user date."""
    return dt.datetime.strftime(dt.datetime.strptime(date_str, '%Y-%m-%d'), '%d-%m-%Y')


def time(time_str):
    """Converts the API UTC time string to the local user time."""
    return dt.datetime.strftime(dt.datetime.strptime(time_str, '%H:%M:%S'), '%H:%M')


def prediction_to_msg(prediction):
    if prediction == '1':
        return 'win for the home-team'
    elif prediction.upper() == 'X':
        return 'draw'
    else:
        return 'win for the away-team'


def player_name(name):
    try:
        name = name.split(' ', 1)
    except AttributeError:
        return name
    if len(name) == 1:
        name = name[0]
    else:
        name = name[1]
    return name


def team_id_to_team_name(team_id, home_team):
    return team_id == str(home_team)


def goal_type_to_prefix(goal_type):
    if goal_type == "goal":
        return ''
    elif goal_type == "penalty":
        return ' P'
    elif goal_type == "own-goal":
        return ' OG'


def events_to_pretty_goals(events, home_goals, away_goals):
    # no home or away-goals scored (0-0)
    if home_goals == 0 and away_goals == 0:
        return []
    # home scored and away didn't (x-0)
    if home_goals > 0 and away_goals == 0:
        return writers.Stdout.get_pretty_goals_clean_sheet("home", events)
    # home didn't score and away did (0-x)
    if home_goals == 0 and away_goals > 0:
        return writers.Stdout.get_pretty_goals_clean_sheet("away", events)
    # both teams scored at least once
    if home_goals > 0 and away_goals > 0:
        return writers.Stdout.get_pretty_goals(events)


def float_to_currency(f):
    f = '{:,.2f}'.format(float(f))
    f = Decimal(sub(r'[^\d.]', '', f))
    return f
