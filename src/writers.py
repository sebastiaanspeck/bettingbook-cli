import click
import json
import os
import copy

import convert

from abc import ABCMeta
from itertools import groupby
from collections import namedtuple
from datetime import datetime


def load_json(file):
    """Load JSON file at app start"""
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, file)) as jfile:
        data = json.load(jfile)
    return data


LEAGUES_DATA = load_json("leagues.json")["leagues"]


def get_writer(output_format='stdout', output_file=None):
    return globals()[output_format.capitalize()](output_file)


class BaseWriter(object):
    __metaclass__ = ABCMeta

    def __init__(self, output_file):
        self.output_filename = output_file


class Stdout(BaseWriter):

    def __init__(self, output_file):
        super().__init__(output_file)
        self.Result = namedtuple("Result", "homeTeam, goalsHomeTeam, awayTeam, goalsAwayTeam")

        self.Odds = namedtuple("Odds", "oddHometeam, oddDraw, oddAwayteam, winningOdd")

        enums = dict(
            WIN="green",
            LOSE="red",
            TIE="yellow",
            MISC="green",
            TIME="yellow",
            CL_POSITION="green",
            EL_POSITION="yellow",
            RL_POSITION="red",
            POSITION="white",
            ODDS="yellow"
        )
        self.colors = type('Enum', (), enums)

        self.score_id = 1

        self.bet_matches = []

    @staticmethod
    def show_profile(profiledata):
        click.secho("""Welcome back %s
Your balance: %s
Your timezone: %s
""" % (profiledata['name'], profiledata['balance'], profiledata['timezone']), fg="green", nl=False)

    def standings(self, league_table, leagueid, show_details):
        """ Prints the league standings in a pretty way """
        for leagues in league_table:
            self.standings_header(convert.convert_leagueid_to_leaguename(leagueid), show_details, leagues['name'])
            number_of_teams = len(leagues['standings']['data'])
            positions = set()
            if show_details:
                click.secho(f"{'POS':6}  {'CLUB':30}    {'PLAYED':10}    {'WON':10}    {'DRAW':10}    {'LOST':10}    "
                            f"{'GOALS':10}    {'GOAL DIFF':10}    {'POINTS':10}    {'RECENT FORM':10}")
            else:
                click.secho(f"{'POS':6}  {'CLUB':30}    {'PLAYED':10}    {'GOAL DIFF':10}    {'POINTS':10}")
            for team in leagues['standings']['data']:
                goal_difference = team['total']['goal_difference']
                position = team['position']
                result = team['result']
                recent_form = " ".join(team['recent_form'])
                goals = str(team['overall']['goals_scored']) + ":" + str(team['overall']['goals_against'])

                while len(goals) < 4:
                    goals = goals + " "

                if show_details:
                    team_str = (f"{position:<7} {team['team_name']:<33} {str(team['overall']['games_played']):<14}"
                                f"{str(team['overall']['won']):<13} {str(team['overall']['draw']):<13} "
                                f"{str(team['overall']['lost']):<13} {goals:<13} "
                                f"{goal_difference:<13} {team['total']['points']:<13} {recent_form}")
                else:
                    team_str = (f"{position:<7} {team['team_name']:<33} {str(team['overall']['games_played']):<14}"
                                f"{goal_difference:<13} {team['total']['points']}")
                positions = self.color_results(result, team_str, positions)
                if team['position'] == number_of_teams:
                    click.echo()
            self.print_colors(positions)

    def color_results(self, result, team_str, positions):
        if result is None:
            click.secho(team_str, fg=self.colors.POSITION)
        elif 'Champions League' in result or result == "Promotion":
            if result == "Promotion":
                positions.add(('promotion', self.colors.CL_POSITION))
            elif "Champions League" in result:
                positions.add(('CL (play-offs)', self.colors.CL_POSITION))
            click.secho(team_str, bold=True, fg=self.colors.CL_POSITION)
        elif 'Europa League' in result or result == "Promotion Play-off":
            if result == "Promotion Play-off":
                positions.add(('promotion (play-offs)', self.colors.EL_POSITION))
            elif "Europa League" in result:
                positions.add(('EL (play-offs)', self.colors.EL_POSITION))
            click.secho(team_str, fg=self.colors.EL_POSITION)
        elif 'Relegation' in result:
            positions.add(('relegation (play-offs)', self.colors.RL_POSITION))
            click.secho(team_str, fg=self.colors.RL_POSITION)
        else:
            click.secho(team_str, fg=self.colors.POSITION)
        return positions

    @staticmethod
    def print_colors(positions):
        for position in positions:
            try:
                click.secho(f"This color is {position[0]} position", fg=position[1])
            except IndexError:
                pass

    def league_scores(self, total_data, parameters):
        """Prints the data in a pretty format"""
        if parameters.refresh:
            os.system('cls' if os.name == 'nt' else 'clear')
        self.score_id = 1
        self.bet_matches = []
        scores = sorted(total_data, key=lambda x: (x["league"]["data"]["country_id"], x['league_id']))
        self.updatetime()
        for league, games in groupby(scores, key=lambda x: x['league_id']):
            league = convert.convert_leagueid_to_leaguename(league)
            games = sorted(games, key=lambda x: x["time"]["starting_at"]["date_time"])
            if league is None:
                continue
            games_copy = copy.deepcopy(games)
            league_prefix = list(set([x['league']['data']['name'] for x in games_copy]))
            match_status = set([x['time']['status'] for x in games_copy])
            if parameters.type_sort == "live" and match_status == {"NS"} or \
                    parameters.type_sort == "live" and match_status == {"FT"}:
                continue
            if parameters.type_sort == "today" and match_status == {"LIVE"}:
                continue
            if league_prefix[0] == league:
                self.league_header(league)
            else:
                self.league_header(league + ' - ' + league_prefix[0])
            games = self.group_games(games, games_copy)
            self.print_matches(games, parameters)
        return self.bet_matches

    def group_games(self, games, games_copy):
        keys = [list(key.keys()) for key in games_copy]
        uniq_keys = set()
        for key in keys:
            uniq_keys.update(key)
        if "round" in uniq_keys:
            if self.groupby_round(games_copy):
                games = groupby(games, key=lambda x: x["round"]["data"]["name"])
            else:
                games = groupby(games, key=lambda x: x["stage"]["data"]["name"])
        else:
            games = groupby(games, key=lambda x: x["stage"]["data"]["name"])
        return games

    def print_matches(self, games, parameters):
        for matchday, matches in games:
            print_matchday = ''
            if len(str(matchday)) < 3:
                self.league_subheader(matchday, 'matchday')
            else:
                self.league_subheader(matchday, 'stage')
            for match in matches:
                self.print_match(match, parameters, print_matchday, matchday)

    def print_match(self, match, parameters, print_matchday, matchday):
        if parameters.type_sort == "today" and match["time"]["status"] in ["LIVE", "HT", "ET", "PEN_LIVE", "AET",
                                                                           "BREAK", "AU"]:
            return
        if parameters.type_sort == "live" and match["time"]["status"] in ["NS", "FT", "FT_PEN", "CANCL", "POSTP",
                                                                          "INT", "ABAN", "SUSP", "AWARDED", "DELAYED",
                                                                          "TBA", "WO", "AU"]:
            return
        if matchday == "Regular Season" and print_matchday != match["round"]["data"]["name"]:
            print_matchday = match["round"]["data"]["name"]
            self.league_subheader(print_matchday, 'matchday')
        if parameters.show_odds:
            self.print_odds(match)
        if parameters.place_bet:
            self.bet_matches.extend([match["id"]])
        self.scores(self.parse_result(match), parameters.place_bet)
        if parameters.type_sort != "matches":
            self.print_datetime_status_matches(match)
        else:
            self.print_datetime_status(match)
        if parameters.show_details:
            self.print_details(match)
        click.echo()

    def updatetime(self):
        """Prints the time at which the data was updated"""
        click.secho(f"Last update: {datetime.now():%d-%m-%Y %H:%M:%S}", fg=self.colors.MISC)

    def league_header(self, league):
        """Prints the league header"""
        league_name = f" {league} "
        click.secho(f"{league_name:=^62}", fg=self.colors.MISC)

    def standings_header(self, league, details, prefix=None):
        """Prints the league header"""
        league_name = f" {league} - {prefix} "
        if details:
            click.secho(f"{league_name:#^151}", fg=self.colors.MISC)
        else:
            click.secho(f"{league_name:#^76}", fg=self.colors.MISC)
        click.echo()

    def league_subheader(self, subheader, type_header):
        """Prints the league matchday"""
        if type_header == 'matchday':
            league_subheader = " Matchday {0} ".format(subheader)
        else:
            league_subheader = " {0} ".format(subheader)
        click.secho(f"{league_subheader:-^62}", fg=self.colors.MISC)
        click.echo()

    def scores(self, result, place_bet):
        """Prints out the scores in a pretty format"""
        winning_team = self.calculate_winning_team(result.goalsHomeTeam, result.goalsAwayTeam, '')
        if winning_team == "1":
            home_color, away_color = (self.colors.WIN, self.colors.LOSE)
        elif winning_team == "2":
            home_color, away_color = (self.colors.LOSE, self.colors.WIN)
        else:
            home_color = away_color = self.colors.TIE

        if place_bet:
            if self.score_id < 10:
                click.secho(f"{self.score_id}.  ", nl=False)
            else:
                click.secho(f"{self.score_id}. ", nl=False)
            x = 21
            self.score_id += 1
        else:
            x = 25

        click.secho(f"{result.homeTeam:{x}} {result.goalsHomeTeam:>2}",
                    fg=home_color, nl=False)
        click.secho("  vs ", nl=False)
        click.secho(f"{result.goalsAwayTeam:>2} {result.awayTeam.rjust(26)}",
                    fg=away_color, nl=False)

    def print_odds(self, match):
        odds_dict = {"1": [], "X": [], "2": []}
        for bookmaker in match["odds"]["data"]:
            for odds in bookmaker["bookmaker"]["data"]:
                for odd in odds["odds"]["data"]:
                    odds_dict = self.fill_odds(odd, odds_dict)
        self.odds(self.parse_odd(odds_dict, match["scores"]["localteam_score"],
                                 match["scores"]["visitorteam_score"], match["time"]["status"]))

    @staticmethod
    def fill_odds(odd, odds):
        odds[odd["label"]].append(float(odd["value"]))
        return odds

    def print_datetime_status_matches(self, match):
        if match["time"]["status"] in ["LIVE", "HT", "ET", "PEN_LIVE", "AET", "BREAK"]:
            if match["time"]["status"] == "HT":
                click.secho(f'   HT',
                            fg=self.colors.TIME)
            # print 0' instead of None'
            elif match["time"]["minute"] is None and match["time"]["added_time"] == 0:
                click.secho(f'   0\'',
                            fg=self.colors.TIME)
            # print minute
            elif match["time"]["added_time"] in [0, None]:
                click.secho(f'   {match["time"]["minute"]}\'',
                            fg=self.colors.TIME)
            elif match["time"]["added_time"] not in [0, None]:
                click.secho(f'   {match["time"]["minute"]}\'+{match["time"]["added_time"]}',
                            fg=self.colors.TIME)
        elif match["time"]["status"] in ["FT", "FT_PEN", "TBA", "NS", "CANCL", "POSTP", "INT", "ABAN",
                                         "SUSP", "AWARDED", "DELAYED", "WO", "AU"]:
            click.secho(f'   {convert.convert_time(match["time"]["starting_at"]["date_time"])} '
                        f'{match["time"]["status"]}',
                        fg=self.colors.TIME)

    def print_datetime_status(self, match):
        if match["time"]["status"] in ["FT", "FT_PEN", "AET", "TBA"]:
            click.secho(f'   {convert.convert_time(match["time"]["starting_at"]["date"])} '
                        f'{match["time"]["status"]}',
                        fg=self.colors.TIME)
        elif match["time"]["status"] in ["NS", "CANCL", "POSTP", "INT", "ABAN", "SUSP", "AWARDED",
                                         "DELAYED", "WO", "AU"]:
            click.secho(f'   {convert.convert_time(match["time"]["starting_at"]["date_time"])} '
                        f'{match["time"]["status"]}',
                        fg=self.colors.TIME)

    def print_details(self, match):
        goals = []
        events = sorted(match["events"]["data"], key=lambda x: x["id"])
        for event in events:
            if event["type"] in ["goal", "penalty", "own-goal"] and event["minute"] is not None:
                player_name = convert.format_playername(event["player_name"])
                home_team = convert.convert_teamid_to_teamname(event["team_id"], match["localTeam"]["data"]["id"])
                goal_type = convert.convert_type_to_prefix(event["type"])
                goals.extend([[home_team, player_name, event["minute"], goal_type]])
        goals = sorted(goals, key=lambda x: x[0])
        events = {"home": [], "away": []}
        for goal in goals:
            if goal[0]:
                events["home"].extend([{goal[1]: [{"minute": [goal[2]], "type": [goal[3]]}]}])
            else:
                events["away"].extend([{goal[1]: [{"minute": [goal[2]], "type": [goal[3]]}]}])
        events["home"] = self.merge_duplicate_keys(events["home"])
        events["away"] = self.merge_duplicate_keys(events["away"])
        goals = convert.convert_events_to_pretty_goals(events, match["scores"]["localteam_score"],
                                                       match["scores"]["visitorteam_score"])
        self.goals(goals)

    def odds(self, odds):
        """Prints out the odds in a pretty format"""
        if odds.winningOdd == 0:
            home_color, draw_color, away_color = (self.colors.WIN, self.colors.LOSE, self.colors.LOSE)
        elif odds.winningOdd == 1:
            home_color, draw_color, away_color = (self.colors.LOSE, self.colors.WIN, self.colors.LOSE)
        elif odds.winningOdd == 2:
            home_color, draw_color, away_color = (self.colors.LOSE, self.colors.LOSE, self.colors.WIN)
        else:
            home_color, draw_color, away_color = (self.colors.ODDS, self.colors.ODDS, self.colors.ODDS)
        click.secho("{}".format(odds.oddHometeam.rjust(28)), fg=home_color, nl=False)
        click.secho(" {} ".format(odds.oddDraw), fg=draw_color, nl=False)
        click.secho("{}".format(odds.oddAwayteam), fg=away_color, nl=True)

    @staticmethod
    def merge_duplicate_keys(dicts):
        d = {}
        for dicty in dicts:
            for key in dicty:
                try:
                    d[key][0]["minute"] += dicty[key][0]["minute"]
                    d[key][0]["type"] += dicty[key][0]["type"]
                except KeyError:
                    d[key] = dicty[key]
        return d

    @staticmethod
    def calculate_winning_team(home_goals, away_goals, game_status):
        # hometeam won
        if home_goals > away_goals and game_status != "TBA":
            return "1"
        # awayteam won
        elif home_goals < away_goals and game_status != "TBA":
            return "2"
        # draw
        elif home_goals == away_goals and game_status not in ['NS', 'TBA']:
            return "X"
        # no winner yet
        else:
            return 'no_winner_yet'

    @staticmethod
    def get_pretty_goals_clean_sheet(team, events):
        goals = []
        for goal in events[team]:
            number_of_goals = len(events[team][goal][0]["minute"])
            if number_of_goals == 1:
                try:
                    str_scorer = ''.join([goal, ' (', str(events[team][goal][0]['minute'][0]),
                                          str(events[team][goal][0]['type'][0]), ')'])
                except TypeError:
                    continue
            else:
                minutes = []
                for key, val in enumerate(events[team][goal][0]["minute"]):
                    minutes.extend([''.join([str(val), str(events[team][goal][0]["type"][key])])])
                str_scorer = ''.join([goal, ' (', ','.join(minutes), ')'])
            if team == "home":
                goals.extend(["{}".format(str_scorer)])
            else:
                goals.extend(["{}".format(str_scorer.rjust(62))])
        return goals

    @staticmethod
    def get_pretty_goals(events):
        goals = []
        for goal in events["home"]:
            number_of_goals = len(events["home"][goal][0]["minute"])
            if number_of_goals == 1:
                str_scorer = ''.join([goal, ' (', str(events['home'][goal][0]['minute'][0]),
                                      str(events['home'][goal][0]['type'][0]), ')'])
            else:
                minutes = []
                for key, val in enumerate(events["home"][goal][0]["minute"]):
                    minutes.extend([''.join([str(val), str(events["home"][goal][0]["type"][key])])])
                str_scorer = ''.join([goal, ' (', ','.join(minutes), ')'])
            goals.extend(["{}".format(str_scorer)])
        for i, goal in enumerate(events["away"]):
            number_of_goals = len(events["away"][goal][0]["minute"])
            if number_of_goals == 1:
                str_scorer = ''.join([goal, ' (', str(events['away'][goal][0]['minute'][0]),
                                      str(events['away'][goal][0]['type'][0]), ')'])
            else:
                minutes = []
                for key, val in enumerate(events["away"][goal][0]["minute"]):
                    minutes.extend([''.join([str(val), str(events["away"][goal][0]["type"][key])])])
                str_scorer = ''.join([goal, ' (', ','.join(minutes), ')'])
            try:
                goals[i] += "{}".format(str_scorer.rjust(62 - len(goals[i])))
            except IndexError:
                goals.extend(["{}".format(str_scorer.rjust(62))])
        return goals

    @staticmethod
    def goals(goals):
        """"Prints the goals in a pretty format"""
        try:
            for goal in goals:
                click.secho(goal)
        except TypeError:
            pass

    def parse_result(self, data):
        """Parses the results and returns a Result namedtuple"""
        def match_status(status, score):
            return "-" if status in ["NS", "TBA"] else score
        result = self.Result(
            data["localTeam"]["data"]["name"],
            match_status(data["time"]["status"], data["scores"]["localteam_score"]),
            data["visitorTeam"]["data"]["name"],
            match_status(data["time"]["status"], data["scores"]["visitorteam_score"]))

        return result

    def parse_odd(self, odds, home_goals, away_goals, status):
        """Parses the odds and returns a Odds namedtuple"""
        def winning_odd():
            winning_team = self.calculate_winning_team(home_goals, away_goals, status)
            return winning_team

        def highest_odd(odd_in):
            try:
                return sum(odd_in)/len(odd_in)
            except ValueError:
                return '0.00'
        for label, values in odds.items():
            odd = highest_odd(values)
            odd = "{0:.2f}".format(odd)
            if label == "1":
                home_odd = odd
            elif label == "2":
                away_odd = odd
            else:
                draw_odd = odd
            try:
                odds = self.Odds(
                    str(home_odd), str(draw_odd),  str(away_odd),
                    winning_odd())
            except UnboundLocalError:
                odds = self.Odds(
                    '0.00', '0.00', '0.00',
                    'no_winner_yet')
        return odds

    @staticmethod
    def groupby_round(matches):
        for match in matches:
            try:
                match['round']['data']['name']
            except KeyError:
                return False
        return True
