import click
import os
import copy

import convert

from abc import ABCMeta
from itertools import groupby
from collections import namedtuple
from datetime import datetime

from json_handler import JsonHandler

jh = JsonHandler()
LEAGUES_DATA = jh.load_leagues()


def get_writer(output_format='stdout', output_file=None):
    return globals()[output_format.capitalize()](output_file)


class BaseWriter(object):
    __metaclass__ = ABCMeta

    def __init__(self, output_file):
        self.output_filename = output_file


class Stdout(BaseWriter):

    def __init__(self, output_file):
        super().__init__(output_file)
        self.Result = namedtuple("Result", "home_team, goals_home_team, away_team, goals_away_team")

        self.Odds = namedtuple("Odds", "odd_home_team, odd_draw, odd_away_team, winning_odd")

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
    def show_profile(profile_data):
        """Show the profile data"""
        click.secho(f"""Welcome back {profile_data['name']}
Your balance: {profile_data['balance']}
Your timezone: {profile_data['timezone']}""", fg="green")

    @staticmethod
    def show_leagues(leagues):
        click.secho("Showing the leagues that are in your Sportmonks API Plan. ")
        click.secho(f"{'ID':7} {'NAME':30} {'ABBREVIATION':15} {'LEAGUE NAME':15}", bold=True)
        league_data = []
        for league in leagues:
            league_abbreviation = convert.league_id_to_league_abbreviation(league['id'])
            league_name = convert.league_id_to_league_name(league['id'])
            league_data.append([league['id'], league['name'], league_abbreviation, league_name])
        league_data = sorted(league_data, key=lambda x: (x[2]))
        for league in league_data:
            click.secho(f"{league[0]:<7} {league[1]:<30} {league[2]:<15} {league[3]:<15}")

    def standings(self, standings_data, league_id, show_details):
        """ Prints the league standings in a pretty way """
        for standing in standings_data:
            self.standings_header(convert.league_id_to_league_name(league_id), show_details, standing['name'])
            number_of_teams = len(standing['standings']['data'])
            positions = list()
            if show_details:
                click.secho(f"{'POS':6}  {'CLUB':20}    {'PLAYED':8}    {'WON':8}    {'DRAW':8}    {'LOST':8}    "
                            f"{'GOALS':8}    {'GOAL DIFF':8}    {'POINTS':8}    {'RECENT FORM':8}")
            else:
                click.secho(f"{'POS':6}  {'CLUB':20}    {'PLAYED':8}    {'GOAL DIFF':6}    {'POINTS':8}")
            for team in standing['standings']['data']:
                goal_difference = team['total']['goal_difference']
                position = team['position']
                result = team['result']
                recent_form = " ".join(team['recent_form'])
                goals = str(team['overall']['goals_scored']) + ":" + str(team['overall']['goals_against'])

                while len(goals) < 4:
                    goals = goals + " "

                if show_details:
                    team_str = (f"{position:<7} {team['team_name']:<20} {str(team['overall']['games_played']):>9}"
                                f"{str(team['overall']['won']):>9} {str(team['overall']['draw']):>12} "
                                f"{str(team['overall']['lost']):>11} {goals:>12} "
                                f"{goal_difference:>15} {team['total']['points']:>9} {recent_form:>16}")
                else:
                    team_str = (f"{position:<7} {team['team_name']:<20} {str(team['overall']['games_played']):>9}"
                                f"{goal_difference:>15} {team['total']['points']:>9}")
                positions = self.color_position(result, team_str, positions)
                if team['position'] == number_of_teams:
                    click.echo()
            positions = self.remove_duplicates(positions)
            self.print_colors(positions)

    def color_position(self, result, team_str, positions):
        """Based on the result, color the position"""
        if result is None:
            click.secho(team_str, fg=self.colors.POSITION)
        elif 'Champions League' in result or result == "Promotion":
            if result == "Promotion":
                positions.append(('promotion', self.colors.CL_POSITION))
            elif "Champions League" in result:
                positions.append(('CL (play-offs)', self.colors.CL_POSITION))
            click.secho(team_str, bold=True, fg=self.colors.CL_POSITION)
        elif 'Europa League' in result or result == "Promotion Play-off":
            if result == "Promotion Play-off":
                positions.append(('promotion (play-offs)', self.colors.EL_POSITION))
            elif "Europa League" in result:
                positions.append(('EL (play-offs)', self.colors.EL_POSITION))
            click.secho(team_str, fg=self.colors.EL_POSITION)
        elif 'Relegation' in result:
            positions.append(('relegation (play-offs)', self.colors.RL_POSITION))
            click.secho(team_str, fg=self.colors.RL_POSITION)
        else:
            click.secho(team_str, fg=self.colors.POSITION)
        return positions

    @staticmethod
    def print_colors(positions):
        """Print the color which explains the corresponding position"""
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
        self.update_time()
        for league, games in groupby(scores, key=lambda x: x['league_id']):
            league = convert.league_id_to_league_name(league)
            games = sorted(games, key=lambda x: x["time"]["starting_at"]["date_time"])
            if league is '':
                continue
            games_copy = copy.deepcopy(games)
            league_prefix = list(set([x['league']['data']['name'] for x in games_copy]))
            match_status = set([x['time']['status'] for x in games_copy])
            skip_league = self.get_skip_league(match_status, parameters.type_sort, parameters.place_bet)
            if skip_league:
                continue
            if league_prefix[0] == league:
                self.league_header(league)
            else:
                self.league_header(league + ' - ' + league_prefix[0])
            games = self.group_games(games, games_copy)
            self.print_matches(games, parameters)
        return self.bet_matches

    def group_games(self, games, games_copy):
        """Group the games based on round or stage"""
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
        """Print the matches"""
        skip_match_statuses = self.get_match_statuses_to_skip(parameters.type_sort, parameters.place_bet)
        for matchday, matches in games:
            print_matchday = ''
            if len(str(matchday)) < 3:
                self.league_subheader(matchday, 'matchday')
            else:
                self.league_subheader(matchday, 'stage')
            for match in matches:
                self.print_match(match, parameters, print_matchday, matchday, skip_match_statuses)

    def print_match(self, match, parameters, print_matchday, matchday, skip_match_statuses):
        """Print match and all other match-details"""
        if match["time"]["status"] in skip_match_statuses:
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
            self.print_datetime_status(match, parameters)
        else:
            self.print_datetime_status_matches(match)
        if parameters.show_details:
            self.print_details(match)
        click.echo()

    def update_time(self):
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
            click.secho(f"{league_name:#^138}", fg=self.colors.MISC)
        else:
            click.secho(f"{league_name:#^73}", fg=self.colors.MISC)
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
        winning_team = self.calculate_winning_team(result.goals_home_team, result.goals_away_team, '')
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

        click.secho(f"{result.home_team:{x}} {result.goals_home_team:>2}",
                    fg=home_color, nl=False)
        click.secho("  vs ", nl=False)
        click.secho(f"{result.goals_away_team:>2} {result.away_team.rjust(26)}",
                    fg=away_color, nl=False)

    def print_odds(self, match):
        """Print the odds"""
        odds_dict = {"1": [], "X": [], "2": []}

        for odds in match["flatOdds"]["data"]:
            for odd in odds["odds"]:
                odds_dict = self.fill_odds(odd, odds_dict)
        self.odds(self.parse_odd(odds_dict, match["scores"]["localteam_score"],
                                 match["scores"]["visitorteam_score"], match["time"]["status"]))

    @staticmethod
    def fill_odds(odd, odds):
        """Fills the odds with all odds"""
        odds[odd["label"]].append(float(odd["value"]))
        return odds

    def print_datetime_status(self, match, parameters):
        """Prints the date/time in a pretty format based on the match status"""
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
            if parameters.type_sort == "live":
                click.secho(f'   {convert.datetime(match["time"]["starting_at"]["date_time"])} '
                            f'{match["time"]["status"]}',
                            fg=self.colors.TIME)
            elif parameters.type_sort == "today":
                click.secho(f'   {convert.time(match["time"]["starting_at"]["time"])} '
                            f'{match["time"]["status"]}',
                            fg=self.colors.TIME)

    def print_datetime_status_matches(self, match):
        """Prints the date/time in a pretty format based on the match status"""
        if match["time"]["status"] in ["FT", "FT_PEN", "AET", "TBA"]:
            click.secho(f'   {convert.date(match["time"]["starting_at"]["date"])} '
                        f'{match["time"]["status"]}',
                        fg=self.colors.TIME)
        elif match["time"]["status"] in ["NS", "CANCL", "POSTP", "INT", "ABAN", "SUSP", "AWARDED",
                                         "DELAYED", "WO", "AU"]:
            click.secho(f'   {convert.datetime(match["time"]["starting_at"]["date_time"])} '
                        f'{match["time"]["status"]}',
                        fg=self.colors.TIME)

    def print_details(self, match):
        """Prints the match details in a pretty format"""
        goals = []
        events = sorted(match["events"]["data"], key=lambda x: x["id"])
        for event in events:
            if event["type"] in ["goal", "penalty", "own-goal"] and event["minute"] is not None:
                player_name = convert.player_name(event["player_name"])
                home_team = convert.team_id_to_team_name(event["team_id"], match["localTeam"]["data"]["id"])
                goal_type = convert.goal_type_to_prefix(event["type"])
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
        goals = convert.events_to_pretty_goals(events, match["scores"]["localteam_score"],
                                               match["scores"]["visitorteam_score"])
        self.goals(goals)

    def odds(self, odds):
        """Prints the odds in a pretty format"""
        if odds.winning_odd == 0:
            home_color, draw_color, away_color = (self.colors.WIN, self.colors.LOSE, self.colors.LOSE)
        elif odds.winning_odd == 1:
            home_color, draw_color, away_color = (self.colors.LOSE, self.colors.WIN, self.colors.LOSE)
        elif odds.winning_odd == 2:
            home_color, draw_color, away_color = (self.colors.LOSE, self.colors.LOSE, self.colors.WIN)
        else:
            home_color, draw_color, away_color = (self.colors.ODDS, self.colors.ODDS, self.colors.ODDS)
        click.secho("{}".format(odds.odd_home_team.rjust(28)), fg=home_color, nl=False)
        click.secho(" {} ".format(odds.odd_draw), fg=draw_color, nl=False)
        click.secho("{}".format(odds.odd_away_team), fg=away_color, nl=True)

    @staticmethod
    def merge_duplicate_keys(dicts):
        """Merge duplicate keys in dicts"""
        d = {}
        for i_dict in dicts:
            for key in i_dict:
                try:
                    d[key][0]["minute"] += i_dict[key][0]["minute"]
                    d[key][0]["type"] += i_dict[key][0]["type"]
                except KeyError:
                    d[key] = i_dict[key]
        return d

    @staticmethod
    def calculate_winning_team(home_goals, away_goals, game_status):
        # home team won
        """Calculate the winning team"""
        if home_goals > away_goals and game_status != "TBA":
            return "1"
        # away team won
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
        """Get the goals in a pretty-format"""
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
        """Get the goals in a pretty-format"""
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
            """If the status is NS or TBA, return "-", else return the score """
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
            """Returns the winning_odd"""
            winning_team = self.calculate_winning_team(home_goals, away_goals, status)
            return winning_team

        def average_odd(odd_in):
            """Calculates the average odd"""
            try:
                return sum(odd_in) / len(odd_in)
            except (ValueError, ZeroDivisionError):
                return 0.00

        home_odd, draw_odd, away_odd = '', '', ''
        for label, values in odds.items():
            odd = average_odd(values)
            odd = "{0:.2f}".format(odd)
            if label == "1":
                home_odd = odd
            elif label == "2":
                away_odd = odd
            else:
                draw_odd = odd
            try:
                odds = self.Odds(
                    str(home_odd), str(draw_odd), str(away_odd),
                    winning_odd())
            except UnboundLocalError:
                odds = self.Odds(
                    '0.00', '0.00', '0.00',
                    'no_winner_yet')
        return odds

    @staticmethod
    def groupby_round(matches):
        """Group the matches by round"""
        for match in matches:
            try:
                match['round']['data']['name']
            except KeyError:
                return False
        return True

    @staticmethod
    def remove_duplicates(li):
        my_set = set()
        res = []
        for e in li:
            if e not in my_set:
                res.append(e)
                my_set.add(e)
        #
        return res

    @staticmethod
    def get_match_statuses_to_skip(type_sort, place_bet):
        if type_sort == "today" and place_bet is True:
            return ["FT", "FT_PEN", "CANCL", "POSTP", "INT", "ABAN",
                    "SUSP", "AWARDED", "DELAYED", "TBA", "WO", "AU",
                    "LIVE", "HT", "ET", "PEN_LIVE", "AET", "BREAK", "AU"]
        elif type_sort == "today" or type_sort == "matches":
            return ["LIVE", "HT", "ET", "PEN_LIVE", "AET", "BREAK", "AU"]
        elif type_sort == "live":
            return ["NS", "FT", "FT_PEN", "CANCL", "POSTP", "INT", "ABAN",
                    "SUSP", "AWARDED", "DELAYED", "TBA", "WO", "AU"]
        else:
            return []

    @staticmethod
    def get_skip_league(match_status, type_sort, place_bet):
        if type_sort == "live" and match_status == {"NS"}:
            return True
        elif type_sort == "live" and match_status == {"FT"}:
            return True
        elif type_sort == "today" and match_status == {"LIVE"}:
            return True
        elif type_sort == "today" and place_bet and match_status == {"FT"}:
            return True
        else:
            return False
