import json
import os
import datetime
from re import sub
from decimal import Decimal

import writers


def load_json(file):
    """Load JSON file at app start"""
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, file)) as jfile:
        data = json.load(jfile)
    return data


LEAGUES_DATA = load_json("leagues.json")["leagues"]


def convert_leagueid_to_leaguename(league):
    for leagues in LEAGUES_DATA:
        leaguename = list(leagues.values())[1]
        leagueids = list(leagues.values())[0]
        if str(league) in leagueids:
            return leaguename
    return None


def convert_datetime(datetime_str):
    """Converts the API UTC time string to the local user time."""
    try:
        return datetime.datetime.strftime(datetime.datetime.strptime(datetime_str,
                                                                     '%Y-%m-%d %H:%M:%S'), '%d-%m-%Y %H:%M')
    except ValueError:
        return datetime.datetime.strftime(datetime.datetime.strptime(datetime_str, '%Y-%m-%d'), '%d-%m-%Y')


def convert_time(time_str):
    return datetime.datetime.strftime(datetime.datetime.strptime(time_str, '%H:%M:%S'), '%H:%M')


def convert_prediction_to_msg(prediction):
    if prediction == '1':
        return 'win for the home-team'
    elif prediction.upper() == 'X':
        return 'draw'
    else:
        return 'win for the away-team'


def format_playername(name):
    try:
        player_name = name.split(' ', 1)
    except AttributeError:
        return name
    if len(player_name) == 1:
        player_name = player_name[0]
    else:
        player_name = player_name[1]
    return player_name


def convert_teamid_to_teamname(teamid, hometeam):
    return teamid == str(hometeam)


def convert_type_to_prefix(goal_type):
    if goal_type == "goal":
        return ''
    elif goal_type == "penalty":
        return ' P'
    elif goal_type == "own-goal":
        return ' OG'


def convert_events_to_pretty_goals(events, home_goals, away_goals):
    # no home or away-goals scored (0-0)
    if home_goals == 0 and away_goals == 0:
        return []
    # home scored and away didn't (x-0)
    if home_goals > 0 and away_goals == 0:
        return writers.Stdout.get_pretty_goals_clean_sheet("home", events)
    # away didn't score and away did (0-x)
    if home_goals == 0 and away_goals > 0:
        return writers.Stdout.get_pretty_goals_clean_sheet("away", events)
    if home_goals > 0 and away_goals > 0:
        return writers.Stdout.get_pretty_goals(events)


def convert_float_to_curreny(f):
    f = '{:,.2f}'.format(float(f))
    f = Decimal(sub(r'[^\d.]', '', f))
    return f
