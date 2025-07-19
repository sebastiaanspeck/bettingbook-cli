from datetime import datetime
from re import sub
from decimal import Decimal

from json_handler import JsonHandler
import writers

jh = JsonHandler()
LEAGUES_DATA = jh.load_leagues()

dt = datetime


def league_id_to_league_name(league_id):
    for leagues in LEAGUES_DATA:
        league_name = list(leagues.values())[1]
        league_ids = list(leagues.values())[0]
        if int(league_id) in league_ids:
            return league_name
    return ""


def league_id_to_league_abbreviation(league_id):
    for leagues in LEAGUES_DATA:
        league_abbr = list(leagues.keys())[0]
        league_ids = list(leagues.values())[0]
        if int(league_id) in league_ids:
            return league_abbr
    return ""


def format_date(date_format):
    if "-" in date_format:
        splitter = "-"
    elif "/" in date_format:
        splitter = "/"
    elif "." in date_format:
        splitter = "."
    else:
        splitter = " "
    return splitter.join(["%" + char for char in date_format.split(splitter)])


def datetime(datetime_str, date_format):
    """Converts the API datetime string to the local user datetime."""
    datetime = dt.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    if datetime.year == dt.now().year:
        date_format = date_format.replace("%Y", "").replace("%y", "").rstrip("-")
    return dt.strftime(datetime, date_format + " %H:%M")


def date(date_str, date_format):
    """Converts the API date string to the local user date."""
    date = dt.strptime(date_str, "%Y-%m-%d")
    if date.year == dt.now().year:
        date_format = date_format.replace("%Y", "").replace("%y", "").rstrip("-")
    return dt.strftime(date, date_format)


def time(time_str):
    """Converts the API time string to the local user time."""
    return dt.strftime(dt.strptime(time_str, "%H:%M:%S"), "%H:%M")


def prediction_to_msg(prediction):
    if prediction == "1":
        return "win for the home-team"
    elif prediction.upper() == "X":
        return "draw"
    else:
        return "win for the away-team"


def player_name(name):
    if name is None:
        return ""
    try:
        name = name.split(" ", 1)
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
        return ""
    elif goal_type == "penalty":
        return " P"
    elif goal_type == "own-goal":
        return " OG"


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


def float_to_currency(float_value):
    currency_value = "{:,.2f}".format(float(float_value))
    currency_value = Decimal(sub(r"[^\d.]", "", currency_value))
    return currency_value
