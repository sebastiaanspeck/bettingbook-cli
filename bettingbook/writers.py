import click
import datetime
import json
import os
import re

from abc import ABCMeta, abstractmethod
from itertools import groupby
from collections import namedtuple

import leagueids
import leagueproperties


def load_json(file):
    """Load JSON file at app start"""
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, file)) as jfile:
        data = json.load(jfile)
    return data


LEAGUE_IDS = leagueids.LEAGUE_IDS
LEAGUES_DATA = load_json("leagues.json")["leagues"]
LEAGUES_NAMES = {league["id"]: league["name"] for league in LEAGUES_DATA}
LEAGUE_PROPERTIES = leagueproperties.LEAGUE_PROPERTIES


def get_writer(output_format='stdout', output_file=None):
    return globals()[output_format.capitalize()](output_file)


class BaseWriter(object):
    __metaclass__ = ABCMeta

    def __init__(self, output_file):
        self.output_filename = output_file

    @abstractmethod
    def today_scores(self, today_scores):
        pass

    @abstractmethod
    def team_scores(self, team_scores, time):
        pass

    @abstractmethod
    def team_players(self, team):
        pass

    @abstractmethod
    def standings(self, league_table, league):
        pass

    @abstractmethod
    def league_scores(self, total_data):
        pass


class Stdout(BaseWriter):

    def __init__(self, output_file):
        super().__init__(output_file)
        self.Result = namedtuple("Result", "homeTeam, goalsHomeTeam, awayTeam, goalsAwayTeam")

        enums = dict(
            WIN="green",
            LOSE="red",
            TIE="yellow",
            MISC="green",
            TIME="yellow",
            CL_POSITION="green",
            EL_POSITION="yellow",
            RL_POSITION="red",
            POSITION="blue"
        )
        self.colors = type('Enum', (), enums)

    @staticmethod
    def show_profile(profiledata):
        click.secho("""Welcome back %s
Your balance: %s
Your timezone: %s""" % (profiledata['name'], profiledata['balance'], profiledata['timezone']), fg="green", nl=False)

    def team_players(self, team):
        pass

    def team_scores(self, team_scores, time):
        pass

    def today_scores(self, today_scores):
        """Prints the live scores in a pretty format"""
        scores = sorted(today_scores, key=lambda x: x["league_id"])
        for league, games in groupby(scores, key=lambda x: x['league_id']):
            league = Stdout.convert_leagueid_to_league(league)
            games = sorted(games, key=lambda x: x["time"]["starting_at"]["date_time"])
            try:
                games = sorted(games, key=lambda x: x["time"]["minute"], reverse=True)
            except TypeError:
                pass
            self.league_header(league)
            for game in games:
                self.scores(self.parse_result(game), add_new_line=False)
                if game["time"]["status"] in ["LIVE", "HT", "ET", "PEN_LIVE", "AET", "BREAK"]:
                    click.secho('   %s' % game["time"]["minute"]+"'",
                                fg=self.colors.TIME)
                elif game["time"]["status"] in ["FT", "FT_PEN", "TBA"]:
                    click.secho('   %s' % re.sub('[_]', '', game["time"]["status"][0:2]),
                                fg=self.colors.TIME)
                elif game["time"]["status"] in ["NS", "CANCL", "POSTP", "INT", "ABAN", "SUSP", "AWARDED", "DELAYED",
                                                "WO", "AU"]:
                    click.secho('   %s' % Stdout.convert_time(game["time"]["starting_at"]["date_time"]),
                                fg=self.colors.TIME)
                click.echo()

    def standings(self, league_table, league):
        """ Prints the league standings in a pretty way """
        click.secho("%-6s  %-30s    %-10s    %-10s    %-10s    %-10s    %-10s    %-10s" %
                    ("POS", "CLUB", "PLAYED", "WON", "DRAW", "LOST", "GOAL DIFF", "POINTS"))
        for team in league_table[0]['standings']['data']:
            team_str = (team['position'], team['team_name'], str(team['overall']['games_played']),
                        str(team['overall']['won']), str(team['overall']['draw']), str(team['overall']['lost']),
                        team['total']['goal_difference'], team['total']['points'])
            goal_difference = team_str[6]
            position = team_str[0]

            if int(goal_difference) > 0:
                goal_difference = goal_difference[1:]

            # Define the upper and lower bounds for Champions League,
            # Europa League and Relegation places.
            # This is so we can highlight them appropriately.
            cl_upper, cl_lower = LEAGUE_PROPERTIES[league]['cl']
            el_upper, el_lower = LEAGUE_PROPERTIES[league]['el']
            rl_upper, rl_lower = LEAGUE_PROPERTIES[league]['rl']

            team_str = (f"{position:<7} {team_str[1]:<33} {team_str[2]:<14}"
                        f"{team_str[3]:<13} {team_str[4]:<13} {team_str[5]:<13}"
                        f" {goal_difference:<13} {team_str[7]}")
            if cl_upper <= position <= cl_lower:
                click.secho(team_str, bold=True, fg=self.colors.CL_POSITION)
            elif el_upper <= position <= el_lower:
                click.secho(team_str, fg=self.colors.EL_POSITION)
            elif rl_upper <= position <= rl_lower:
                click.secho(team_str, fg=self.colors.RL_POSITION)
            else:
                click.secho(team_str, fg=self.colors.POSITION)
        click.secho("\nThis color is CL position", fg=self.colors.CL_POSITION)
        click.secho("This color is EL position", fg=self.colors.EL_POSITION)
        click.secho("This color is relegation position", fg=self.colors.RL_POSITION)

    def league_scores(self, total_data):
        """Prints the data in a pretty format"""
        scores = sorted(total_data, key=lambda x: x["league_id"])
        for league, games in groupby(scores, key=lambda x: x['league_id']):
            league = Stdout.convert_leagueid_to_league(league)
            if league is None:
                continue
            games = sorted(games, key=lambda x: x["time"]["starting_at"]["date_time"])
            try:
                games = sorted(games, key=lambda x: x["time"]["minute"], reverse=True)
            except TypeError:
                pass
            self.league_header(league)
            for game in games:
                self.scores(self.parse_result(game), add_new_line=False)
                if game["time"]["status"] in ["LIVE", "HT", "ET"]:
                    click.secho('   %s' % game["time"]["minute"] + "'",
                                fg=self.colors.TIME)
                elif game["time"]["status"] in ["FT", "ABAN", "SUSP", "WO", "AU", "POSTP"]:
                    click.secho('   %s %s' % (game["time"]["status"][0:2],
                                              Stdout.convert_time(game["time"]["starting_at"]["date"])),
                                fg=self.colors.TIME)
                elif game["time"]["status"] == "NS":
                    click.secho('   %s' % Stdout.convert_time(game["time"]["starting_at"]["date_time"]),
                                fg=self.colors.TIME)
                click.echo()

    def league_header(self, league):
        """Prints the league header"""
        league_name = " {0} ".format(league)
        click.secho(f"{league_name:=^61}", fg=self.colors.MISC)
        click.echo()

    def scores(self, result, add_new_line=True):
        """Prints out the scores in a pretty format"""
        if result.goalsHomeTeam > result.goalsAwayTeam:
            home_color, away_color = (self.colors.WIN, self.colors.LOSE)
        elif result.goalsHomeTeam < result.goalsAwayTeam:
            home_color, away_color = (self.colors.LOSE, self.colors.WIN)
        else:
            home_color = away_color = self.colors.TIE

        click.secho('%-25s %2s' % (result.homeTeam, result.goalsHomeTeam),
                    fg=home_color, nl=False)
        click.secho("  vs ", nl=False)
        click.secho('%2s %s' % (result.goalsAwayTeam,
                                result.awayTeam.rjust(25)), fg=away_color,
                    nl=add_new_line)

    def parse_result(self, data):
        """Parses the results and returns a Result namedtuple"""

        def match_status(status, score):
            return "-" if status == "NS" else score

        result = self.Result(
            data["localTeam"]["data"]["name"],
            match_status(data["time"]["status"], data["scores"]["localteam_score"]),
            data["visitorTeam"]["data"]["name"],
            match_status(data["time"]["status"], data["scores"]["visitorteam_score"]))

        return result

    @staticmethod
    def convert_time(time_str):
        """Converts the API UTC time string to the local user time."""
        try:
            return datetime.datetime.strftime(datetime.datetime.strptime(time_str,
                                                                         '%Y-%m-%d %H:%M:%S'), '%d-%m-%Y %H:%M')
        except ValueError:
            return datetime.datetime.strftime(datetime.datetime.strptime(time_str,
                                                                         '%Y-%m-%d'), '%d-%m-%Y')

    @staticmethod
    def convert_leagueid_to_league(league):
        return LEAGUES_NAMES.get(league)
