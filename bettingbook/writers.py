import click
import datetime
import json
import os
import copy

from abc import ABCMeta, abstractmethod
from itertools import groupby
from collections import namedtuple


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

    @abstractmethod
    def standings(self, league_table, league):
        pass

    @abstractmethod
    def league_scores(self, total_data, parameters):
        pass


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

    @staticmethod
    def show_profile(profiledata):
        click.secho("""Welcome back %s
Your balance: %s
Your timezone: %s""" % (profiledata['name'], profiledata['balance'], profiledata['timezone']), fg="green", nl=False)

    def standings(self, league_table, leagueid):
        """ Prints the league standings in a pretty way """
        for leagues in league_table:
            self.standings_header(self.convert_leagueid_to_leaguename(leagueid), leagues['name'])
            number_of_teams = len(leagues['standings']['data'])
            positions = []
            click.secho("{:6}  {:30}    {:10}    {:10}    {:10}    {:10}    {:10}    {:10}".format
                        ("POS", "CLUB", "PLAYED", "WON", "DRAW", "LOST", "GOAL DIFF", "POINTS"))
            for team in leagues['standings']['data']:
                goal_difference = team['total']['goal_difference']
                position = team['position']
                result = team['result']

                if int(goal_difference) > 0:
                    goal_difference = goal_difference[1:]

                team_str = (f"{position:<7} {team['team_name']:<33} {str(team['overall']['games_played']):<14}"
                            f"{str(team['overall']['won']):<13} {str(team['overall']['draw']):<13} "
                            f"{str(team['overall']['lost']):<13} {goal_difference:<13} {team['total']['points']}")
                positions = self.color_results(result, team_str, positions)
                if team['position'] == number_of_teams:
                    click.echo()
            self.print_colors(positions)

    def color_results(self, result, team_str, positions):
        if 'Champions League' in result or result == "Promotion":
            if result == "Promotion" and not(self.alreadyin('promotion', positions)):
                positions.extend([['promotion', self.colors.CL_POSITION]])
            elif "Champions League" in result and not(self.alreadyin('CL (play-offs)', positions)):
                positions.extend([['CL (play-offs)', self.colors.CL_POSITION]])
            click.secho(team_str, bold=True, fg=self.colors.CL_POSITION)
        elif 'Europa League' in result or result == "Promotion Play-off":
            if result == "Promotion Play-off" and not(self.alreadyin('promotion (play-offs', positions)):
                positions.extend([['promotion (play-offs)', self.colors.EL_POSITION]])
            elif "Europa League" in result and not(self.alreadyin('EL (play-offs)', positions)):
                positions.extend([['EL (play-offs)', self.colors.EL_POSITION]])
            click.secho(team_str, fg=self.colors.EL_POSITION)
        elif 'Relegation' in result:
            if not(self.alreadyin('relegation (play-offs)', positions)):
                positions.extend([['relegation (play-offs)', self.colors.RL_POSITION]])
            click.secho(team_str, fg=self.colors.RL_POSITION)
        else:
            click.secho(team_str, fg=self.colors.POSITION)
        return positions

    @staticmethod
    def alreadyin(test, listy):
        return bool([x for x in listy if test == x[0]])

    @staticmethod
    def print_colors(positions):
        for position in positions:
            try:
                click.secho(f"This color is {position[0]} position", fg=position[1])
            except IndexError:
                pass

    def league_scores(self, total_data, parameters):
        """Prints the data in a pretty format"""
        scores = sorted(total_data, key=lambda x: (x["league"]["data"]["country_id"], x['league_id']))
        for league, games in groupby(scores, key=lambda x: x['league_id']):
            league = Stdout.convert_leagueid_to_leaguename(league)
            games = sorted(games, key=lambda x: x["time"]["starting_at"]["date_time"])
            if league is None:
                continue
            games_copy = copy.deepcopy(games)
            league_prefix = list(set([x['league']['data']['name'] for x in games_copy]))
            match_status = list(set([x['time']['status'] for x in games_copy]))
            if parameters.type_sort == "live" and match_status != ["LIVE"]:
                continue
            if parameters.type_sort == "today" and match_status == ["LIVE"]:
                continue
            if league_prefix[0] == league:
                self.league_header(league)
            else:
                self.league_header(league + ' - ' + league_prefix[0])
            games = self.group_games(games, games_copy)
            self.print_matches(games, parameters)

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
        if parameters.type_sort == "today" and match["time"]["status"] in ["LIVE", "HT", "ET",
                                                                           "PEN_LIVE", "AET", "BREAK"]:
            return
        if matchday == "Regular Season" and print_matchday != match["round"]["data"]["name"]:
            print_matchday = match["round"]["data"]["name"]
            self.league_subheader(print_matchday, 'matchday')
        if parameters.show_odds:
            self.print_odds(match)
        self.scores(self.parse_result(match))
        if parameters.type_sort != "matches":
            self.print_datetime_status_matches(match)
        else:
            self.print_datetime_status(match)
        if parameters.show_details:
            self.print_details(match)
        click.echo()

    def league_header(self, league):
        """Prints the league header"""
        league_name = f" {league} "
        click.secho(f"{league_name:=^62}", fg=self.colors.MISC)

    def standings_header(self, league, prefix=None):
        """Prints the league header"""
        league_name = f" {league} - {prefix} "
        click.secho(f"{league_name:#^118}", fg=self.colors.MISC)
        click.echo()

    def league_subheader(self, subheader, type_header):
        """Prints the league matchday"""
        if type_header == 'matchday':
            league_subheader = " Matchday {0} ".format(subheader)
        else:
            league_subheader = " {0} ".format(subheader)
        click.secho(f"{league_subheader:-^62}", fg=self.colors.MISC)
        click.echo()

    def scores(self, result):
        """Prints out the scores in a pretty format"""
        winning_team = self.calculate_winning_team(result.goalsHomeTeam, result.goalsAwayTeam, '')
        if winning_team == 0:
            home_color, away_color = (self.colors.WIN, self.colors.LOSE)
        elif winning_team == 2:
            home_color, away_color = (self.colors.LOSE, self.colors.WIN)
        else:
            home_color = away_color = self.colors.TIE

        click.secho("{:25} {:>2}".format(result.homeTeam, result.goalsHomeTeam),
                    fg=home_color, nl=False)
        click.secho("  vs ", nl=False)
        click.secho('{:>2} {}'.format(result.goalsAwayTeam, result.awayTeam.rjust(26)), fg=away_color,
                    nl=False)

    def print_odds(self, match):
        odds = []
        for i, odd in enumerate(match["flatOdds"]["data"]):
            if match["flatOdds"]["data"][i]["market_id"] == 1:
                odds = odd["odds"]
        self.odds(self.parse_odd(odds, match["scores"]["localteam_score"],
                                 match["scores"]["visitorteam_score"], match["time"]["status"]))

    def print_datetime_status_matches(self, match):
        if match["time"]["status"] in ["LIVE", "HT", "ET", "PEN_LIVE", "AET", "BREAK"]:
            # print 0' instead of None'
            if match["time"]["minute"] is None:
                click.secho(f'   0\'',
                            fg=self.colors.TIME)
            # print minute
            else:
                click.secho(f'   {match["time"]["minute"]}\'',
                            fg=self.colors.TIME)
        elif match["time"]["status"] in ["FT", "FT_PEN", "TBA", "NS", "CANCL", "POSTP", "INT", "ABAN",
                                         "SUSP", "AWARDED", "DELAYED", "WO", "AU"]:
            click.secho(f'   {Stdout.convert_time(match["time"]["starting_at"]["date_time"])} '
                        f'{match["time"]["status"]}',
                        fg=self.colors.TIME)

    def print_datetime_status(self, match):
        if match["time"]["status"] in ["FT", "FT_PEN", "AET", "TBA"]:
            click.secho(f'   {Stdout.convert_time(match["time"]["starting_at"]["date"])} '
                        f'{match["time"]["status"]}',
                        fg=self.colors.TIME)
        elif match["time"]["status"] in ["NS", "CANCL", "POSTP", "INT", "ABAN", "SUSP", "AWARDED",
                                         "DELAYED", "WO", "AU"]:
            click.secho(f'   {Stdout.convert_time(match["time"]["starting_at"]["date_time"])} '
                        f'{match["time"]["status"]}',
                        fg=self.colors.TIME)

    def print_details(self, match):
        goals = []
        events = sorted(match["events"]["data"], key=lambda x: x["id"])
        for event in events:
            if event["type"] in ["goal", "penalty", "own-goal"] and event["minute"] is not None:
                player_name = Stdout.format_playername(event["player_name"])
                home_team = Stdout.convert_teamid_to_teamname(event["team_id"],
                                                              match["localTeam"]["data"]["id"])
                goal_type = Stdout.convert_type_to_prefix(event["type"])
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
        goals = self.convert_events_to_pretty_goals(events, match["scores"]["localteam_score"],
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
        if home_goals > away_goals:
            return 0
        # awayteam won
        elif home_goals < away_goals:
            return 2
        # draw
        elif home_goals == away_goals and game_status != 'NS':
            return 1
        # no winner yet
        else:
            return 'no_winner_yet'

    def convert_events_to_pretty_goals(self, events, home_goals, away_goals):
        goals = []
        # no home or away-goals scored (0-0)
        if home_goals == 0 and away_goals == 0:
            return goals
        # home scored and away didn't (x-0)
        if home_goals > 0 and away_goals == 0:
            goals = self.get_pretty_goals_clean_sheet("home", events)
            return goals
        # away didn't score and away did (0-x)
        if home_goals == 0 and away_goals > 0:
            goals = self.get_pretty_goals_clean_sheet("away", events)
            return goals
        if home_goals > 0 and away_goals > 0:
            goals = self.get_pretty_goals(events)
            return goals

    @staticmethod
    def get_pretty_goals_clean_sheet(team, events):
        goals = []
        for goal in events[team]:
            number_of_goals = len(events[team][goal][0]["minute"])
            if number_of_goals == 1:
                str_scorer = ''.join([goal, ' (', str(events[team][goal][0]['minute'][0]),
                                      str(events[team][goal][0]['type'][0]), ')'])
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
            return "-" if status == "NS" else score

        result = self.Result(
            data["localTeam"]["data"]["name"],
            match_status(data["time"]["status"], data["scores"]["localteam_score"]),
            data["visitorTeam"]["data"]["name"],
            match_status(data["time"]["status"], data["scores"]["visitorteam_score"]))

        return result

    def parse_odd(self, odds, home_goals, away_goals, status):
        """Parses the odds and returns a Odds namedtuple"""
        def winning_odd(odd):
            if odd == [None, None, None]:
                winning_team = self.calculate_winning_team(home_goals, away_goals, status)
                return winning_team
            for index, o in enumerate(odd):
                if o:
                    return index

        for i, _ in enumerate(odds):
            if len(str(odds[i]["value"])) <= 3:
                odds[i]["value"] = "{0:.2f}".format(odds[i]["value"])
            if len(str(odds[i]["value"])) > 4:
                odds[i]["value"] = "{0:.1f}".format(float(odds[i]["value"]))
            if odds[i]["label"] == "1":
                home_odd = odds[i]["value"]
                home_winning = odds[i]["winning"]
            elif odds[i]["label"] == "2":
                away_odd = odds[i]["value"]
                away_winning = odds[i]["winning"]
            elif odds[i]["label"] == "X":
                draw_odd = odds[i]["value"]
                draw_winning = odds[i]["winning"]
        try:
            odds = self.Odds(
                str(home_odd), str(draw_odd),  str(away_odd),
                winning_odd([home_winning, draw_winning, away_winning]))
        except UnboundLocalError:
            odds = self.Odds(
                '0.00', '0.00', '0.00',
                'no_winner_yet')

        return odds

    @staticmethod
    def convert_leagueid_to_leaguename(league):
        for leagues in LEAGUES_DATA:
            leaguename = list(leagues.values())[1]
            leagueids = list(leagues.values())[0]
            if str(league) in leagueids:
                return leaguename
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

    @staticmethod
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

    @staticmethod
    def convert_teamid_to_teamname(teamid, hometeam):
        return teamid == str(hometeam)

    @staticmethod
    def convert_type_to_prefix(goal_type):
        if goal_type == "goal":
            return ''
        elif goal_type == "penalty":
            return ' P'
        elif goal_type == "own-goal":
            return ' OG'

    @staticmethod
    def groupby_round(matches):
        for match in matches:
            try:
                x = match['round']['data']['name']
            except KeyError:
                return False
        return True
