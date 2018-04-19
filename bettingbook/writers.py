import click
import datetime
import json
import os
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
LEAGUES_NAMES = {league["id"]: league["name"] for league in LEAGUES_DATA}


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
            POSITION="blue"
        )
        self.colors = type('Enum', (), enums)

    @staticmethod
    def show_profile(profiledata):
        click.secho("""Welcome back %s
Your balance: %s
Your timezone: %s""" % (profiledata['name'], profiledata['balance'], profiledata['timezone']), fg="green", nl=False)

    def standings(self, league_table, league):
        pass

    def team_players(self, team):
        pass

    def team_scores(self, team_scores, time):
        pass

    def today_scores(self, today_scores):
        """Prints the live scores in a pretty format"""
        scores = sorted(today_scores, key=lambda x: x["league_id"])
        for league, games in groupby(scores, key=lambda x: x['league_id']):
            league = Stdout.convert_leagueid_to_league(league)
            status = copy.deepcopy(games)
            status = {game["time"]["status"] for game in status}
            if status == {"NS"}:
                games = sorted(games, key=lambda x: x["time"]["starting_at"]["date_time"])
            else:
                games = sorted(games, key=lambda x: x["time"]["minute"], reverse=True)
            self.league_header(league)
            for game in games:
                self.scores(self.parse_result(game), add_new_line=False)
                if game["time"]["status"] in ["LIVE", "HT", "ET"]:
                    click.secho('   %s' % game["time"]["minute"]+"'",
                                fg=self.colors.TIME)
                elif game["time"]["status"] == "FT":
                    click.secho('   %s' % game["time"]["status"],
                                fg=self.colors.TIME)
                elif game["time"]["status"] in ["NS", "ABAN", "SUSP", "WO", "AU"]:
                    click.secho('   %s' % Stdout.convert_time(game["time"]["starting_at"]["date_time"]),
                                fg=self.colors.TIME)
                click.echo()

    # def team_scores(self, team_scores, time):
    #     """Prints the teams scores in a pretty format"""
    #     for score in team_scores["fixtures"]:
    #         if score["status"] == "FINISHED":
    #             # click.echo()
    #             click.secho("%s\t" % score["date"].split('T')[0],
    #                         fg=self.colors.TIME, nl=False)
    #             self.scores(self.parse_result(score))
    #         else:
    #             # click.echo()
    #             self.scores(self.parse_result(score), add_new_line=False)
    #             click.secho('   %s' % Stdout.convert_time(score["date"]),
    #                         fg=self.colors.TIME)
    #
    # def team_players(self, team):
    #     """Prints the team players in a pretty format"""
    #     players = sorted(team['players'], key=lambda d: (d['jerseyNumber']))
    #     click.secho("%-4s %-25s    %-20s    %-20s    %-15s    %-10s" %
    #                 ("N.", "NAME", "POSITION", "NATIONALITY", "BIRTHDAY",
    #                  "MARKET VALUE"), bold=True, fg=self.colors.MISC)
    #     fmt = (u"{jerseyNumber:<4} {name:<28} {position:<23} {nationality:<23}"
    #            u" {dateOfBirth:<18} {marketValue}")
    #     for player in players:
    #         # click.echo()
    #         click.secho(fmt.format(**player), bold=True)
    #
    # def standings(self, league_table, league):
    #     """ Prints the league standings in a pretty way """
    #     click.secho("%-6s  %-30s    %-10s    %-10s    %-10s" %
    #                 ("POS", "CLUB", "PLAYED", "GOAL DIFF", "POINTS"))
    #     for team in league_table["standing"]:
    #         if team["goalDifference"] >= 0:
    #             team["goalDifference"] = ' ' + str(team["goalDifference"])
    #
    #         team_str = (u"{position:<7} {teamName:<33} {playedGames:<12}"
    #                     u" {goalDifference:<14} {points}").format(**team)
    #         click.secho(team_str, fg=self.colors.POSITION)

    def league_scores(self, total_data):
        """Prints the data in a pretty format"""
        scores = sorted(total_data, key=lambda x: x["league_id"])
        for league, games in groupby(scores, key=lambda x: x['league_id']):
            league = Stdout.convert_leagueid_to_league(league)
            if league is None:
                continue
            status = copy.deepcopy(games)
            status = {game["time"]["status"] for game in status}
            if status in [{"NS"}, {"FT"}, {'FT', 'NS'}, {'POSTP', 'FT'}]:
                games = sorted(games, key=lambda x: x["time"]["starting_at"]["date_time"])
            else:
                games = sorted(games, key=lambda x: x["time"]["minute"], reverse=True)
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
        click.secho(f"{league_name:=^62}", fg=self.colors.MISC)
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
