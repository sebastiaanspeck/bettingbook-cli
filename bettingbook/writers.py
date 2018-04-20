import click
import datetime
import json
import os
import re
import copy

from abc import ABCMeta, abstractmethod
from itertools import groupby
from collections import namedtuple

import leagueids


def load_json(file):
    """Load JSON file at app start"""
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, file)) as jfile:
        data = json.load(jfile)
    return data


LEAGUE_IDS = leagueids.LEAGUE_IDS
LEAGUES_DATA = load_json("leagues.json")["leagues"]


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
    def convert_leagueid_to_leaguename(self, league):
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
            POSITION="white"
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
            league = Stdout.convert_leagueid_to_leaguename(league)
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
        for leagues in league_table:
            self.standings_header(self.convert_leagueid_to_leaguename(league), leagues['name'])
            number_of_teams = len(leagues['standings']['data'])
            click.secho("{:6}  {:30}    {:10}    {:10}    {:10}    {:10}    {:10}    {:10}".format
                        ("POS", "CLUB", "PLAYED", "WON", "DRAW", "LOST", "GOAL DIFF", "POINTS"))
            for team in leagues['standings']['data']:
                goal_difference = team['total']['goal_difference']
                position = team['position']
                result = team['result']

                if int(goal_difference) > 0:
                    goal_difference = goal_difference[1:]

                # Define the upper and lower bounds for Champions League,
                # Europa League and Relegation places.
                # This is so we can highlight them appropriately.

                team_str = (f"{position:<7} {team['team_name']:<33} {str(team['overall']['games_played']):<14}"
                            f"{str(team['overall']['won']):<13} {str(team['overall']['draw']):<13} "
                            f"{str(team['overall']['lost']):<13} {goal_difference:<13} {team['total']['points']}")
                if 'Champions League' in result:
                    click.secho(team_str, bold=True, fg=self.colors.CL_POSITION)
                elif 'Europa League' in result:
                    click.secho(team_str, fg=self.colors.EL_POSITION)
                elif 'Relegation' in result:
                    click.secho(team_str, fg=self.colors.RL_POSITION)
                else:
                    click.secho(team_str, fg=self.colors.POSITION)
                if team['position'] == number_of_teams:
                    click.echo()
        click.secho("This color is CL (play-offs) position", fg=self.colors.CL_POSITION)
        click.secho("This color is EL (play-offs) position", fg=self.colors.EL_POSITION)
        click.secho("This color is relegation (play-offs) position", fg=self.colors.RL_POSITION)

    def league_scores(self, total_data):
        """Prints the data in a pretty format"""
        scores = sorted(total_data, key=lambda x: x["league_id"])
        for league, games in groupby(scores, key=lambda x: x['league_id']):
            league = Stdout.convert_leagueid_to_leaguename(league)
            games = sorted(games, key=lambda x: x["time"]["starting_at"]["date_time"])
            if league is None:
                continue
            league_names = copy.deepcopy(games)
            league_prefix = list(set([x['league']['data']['name'] for x in league_names]))
            if league_prefix[0] == league:
                self.league_header(league)
            else:
                self.league_header(league + ' - ' + league_prefix[0])
            for matchday, matches in groupby(games, key=lambda x: x["round"]["data"]["name"]):
                self.league_matchday(matchday)
                for match in matches:
                    self.scores(self.parse_result(match), add_new_line=False)
                    if match["time"]["status"] in ["LIVE", "HT", "ET"]:
                        click.secho(f'   {match["time"]["minute"]} {chr(44)}', fg=self.colors.TIME)
                    elif match["time"]["status"] in ["FT", "ABAN", "SUSP", "WO", "AU", "POSTP"]:
                        click.secho(f'   {match["time"]["status"][0:2]} '
                                    f'{Stdout.convert_time(match["time"]["starting_at"]["date"])}', fg=self.colors.TIME)
                    elif match["time"]["status"] == "NS":
                        click.secho(f'   {Stdout.convert_time(match["time"]["starting_at"]["date_time"])}',
                                    fg=self.colors.TIME)
                    click.echo()

    def league_header(self, league):
        """Prints the league header"""
        league_name = f" {league} "
        click.secho(f"{league_name:=^62}", fg=self.colors.MISC)
        click.echo()

    def standings_header(self, league, prefix=None):
        """Prints the league header"""
        league_name = f" {league} - {prefix} "
        click.secho(f"{league_name:#^118}", fg=self.colors.MISC)
        click.echo()

    def league_matchday(self, matchday):
        """Prints the league matchday"""
        league_round = " Matchday {0} ".format(matchday)
        click.secho(f"{league_round:-^62}", fg=self.colors.MISC)
        click.echo()

    def scores(self, result, add_new_line=True):
        """Prints out the scores in a pretty format"""
        if result.goalsHomeTeam > result.goalsAwayTeam:
            home_color, away_color = (self.colors.WIN, self.colors.LOSE)
        elif result.goalsHomeTeam < result.goalsAwayTeam:
            home_color, away_color = (self.colors.LOSE, self.colors.WIN)
        else:
            home_color = away_color = self.colors.TIE

        click.secho("{:25} {:>2}".format(result.homeTeam, result.goalsHomeTeam),
                    fg=home_color, nl=False)
        click.secho("  vs ", nl=False)
        click.secho('{:>2} {}'.format(result.goalsAwayTeam, result.awayTeam.rjust(26)), fg=away_color,
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
    def convert_leagueid_to_leaguename(league):
        for leagues in LEAGUES_DATA:
            if str(league) in leagues['id']:
                return leagues['name']
            if str(league) in leagues['abbrevation']:
                return leagues['name']
        return None

    @staticmethod
    def convert_time(time_str):
        """Converts the API UTC time string to the local user time."""
        try:
            return datetime.datetime.strftime(datetime.datetime.strptime(time_str,
                                                                         '%Y-%m-%d %H:%M:%S'), '%d-%m-%Y %H:%M')
        except ValueError:
            return datetime.datetime.strftime(datetime.datetime.strptime(time_str,
                                                                         '%Y-%m-%d'), '%d-%m-%Y')
