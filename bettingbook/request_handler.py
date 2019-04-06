import requests
import click
import datetime
import json
import sched
import time

import exceptions
from betting import Betting

class RequestHandler(object):
    BASE_URL = 'https://soccer.sportmonks.com/api/v2.0/'

    def __init__(self, params, league_data, writer, config_handler):
        self.params = params
        self.league_data = league_data
        self.writer = writer
        self.config_handler = config_handler

    def show_profile(self):
        self.writer.show_profile(self.config_handler.get_data('profile'))

    def _get(self, url):
        """Handles soccer.sportsmonks requests"""
        req = requests.get(RequestHandler.BASE_URL + url, params=self.params)

        if req.status_code == requests.codes.ok:
            data = self.get_data(req, url)
            return data

        if req.status_code in [requests.codes.bad, requests.codes.server_error]:
            raise exceptions.APIErrorException('Invalid request. Check parameters.')

        if req.status_code == requests.codes.forbidden:
            raise exceptions.APIErrorException('The data you requested is not accessible from your plan.')

        if req.status_code == requests.codes.not_found:
            raise exceptions.APIErrorException('This resource does not exist. Check parameters')

        if req.status_code == requests.codes.too_many_requests:
            raise exceptions.APIErrorException('You have exceeded your allowed requests per minute/day')

    def get_data(self, req, url):
        parts = json.loads(req.text)
        data = parts.get('data')
        meta = parts.get('meta')
        pagination = meta.get('pagination')
        if pagination:
            pages = int(pagination['total_pages'])
        else:
            pages = 1
        if pages > 1:
            for i in range(2, pages + 1):
                self.params['page'] = i
                req = requests.get(RequestHandler.BASE_URL + url, params=self.params)
                next_parts = json.loads(req.text)
                next_data = next_parts.get('data')
                if next_data:
                    data.extend(next_data)
        return data

    def get_league_ids(self):
        league_ids = []
        for x in self.league_data:
            ids = list(x.values())[0]
            for league_id in ids:
                league_ids.extend([league_id])
        return league_ids

    def get_league_abbrevation(self, league_name):
        for x in self.league_data:
            abbrevation = list(x.keys())[0]
            ids = list(x.values())[0]
            if league_name == abbrevation:
                return ids
        return None

    def set_params(self):
        league_ids = self.get_league_ids()
        self.params['leagues'] = ','.join(val for val in league_ids)
        self.params['include'] = 'localTeam,visitorTeam,league,round,events,stage,odds'

    @staticmethod
    def set_start_end(show_history, days):
        now = datetime.datetime.now()
        if show_history:
            start = datetime.datetime.strftime(now - datetime.timedelta(days=days), '%Y-%m-%d')
            end = datetime.datetime.strftime(now - datetime.timedelta(days=1), '%Y-%m-%d')
        else:
            start = datetime.datetime.strftime(now, '%Y-%m-%d')
            end = datetime.datetime.strftime(now + datetime.timedelta(days=days), '%Y-%m-%d')
        return start, end

    def get_matches(self, parameters):
        """
        Queries the API and fetches the scores for fixtures
        based upon the league and time parameter
        """
        self.set_params()
        start, end = self.set_start_end(parameters.show_history, parameters.days)
        if parameters.league_name:
            try:
                league_id = self.get_league_abbrevation(parameters.league_name)
                self.params['leagues'] = ','.join(str(val) for val in league_id)
                self.get_match_data(parameters, start, end)
            except exceptions.APIErrorException as e:
                click.secho(str(e), fg="red", bold=True)
        else:
            try:
                self.get_match_data(parameters, start, end)
            except exceptions.APIErrorException as e:
                click.secho(str(e), fg="red", bold=True)

    def get_match_data(self, parameters, start, end):
        s = sched.scheduler(time.time, time.sleep)
        if parameters.type_sort == "matches":
            fixtures_results = self._get(parameters.url + f'{start}/{end}')
        else:
            fixtures_results = self._get(parameters.url)
        # no fixtures in the timespan. display a help message and return
        if len(fixtures_results) == 0:
            if parameters.type_sort == "matches":
                if parameters.show_history:
                    click.secho(''.join(parameters.msg[0]), fg="red", bold=True)
                else:
                    click.secho(''.join(parameters.msg[1]), fg="red", bold=True)
            else:
                click.secho(parameters.msg[0], fg="red", bold=True)
            return
        bet_matches = self.writer.league_scores(fixtures_results, parameters)
        if parameters.place_bet:
            self.place_bet(bet_matches)
        if parameters.refresh:
            s.enter(60, 1, self.get_match_data, (parameters, start, end,))
            s.run()

    def get_standings(self, league_name, show_details):
        for league_id in self.get_league_abbrevation(league_name):
            url = f'leagues/{league_id}'
            try:
                league_data = self._get(url)
                current_season_id = league_data['current_season_id']
                url = f'standings/season/{current_season_id}'
                standings_data = self._get(url)
                if len(standings_data) == 0:
                    continue
                self.writer.standings(standings_data, league_id, show_details)
            except exceptions.APIErrorException as e:
                click.secho(str(e), fg="red", bold=True)
                
    def place_bet(self, bet_matches):
        match_bet = click.prompt("Give the numbers of the matches on which you want to bet (comma-separated)").split(',')
        match_bet = sorted(self.check_match_bet(match_bet, len(bet_matches)))
        if match_bet == 'no_matches':
            click.secho("There are no valid matches selected.", fg="red", bold=True)
        else:
            matches = []
            for match_id in match_bet:
                try:
                    matches.extend([str(bet_matches[int(match_id)-1])])
                except (IndexError, ValueError):
                    pass
            matches = ','.join(val for val in matches)
            match_data = self.get_match_bet(matches)
            match_data = self.check_match_data(match_data)
            if match_data == 'no_matches':
                click.secho("There are no valid matches selected.", fg="red", bold=True)
            else:
                self.place_bet_betting(match_data)

    def get_match_bet(self, matches):
        url = f'fixtures/multi/{matches}'
        self.params['include'] = 'localTeam,visitorTeam,league,round,events,stage,odds'
        matches = self._get(url)
        return matches

    @staticmethod
    def check_match_bet(match_bet, max_match_id):
        matches = set()
        for match_id in match_bet:
            try:
                if 0 <= int(match_id) > max_match_id:
                    click.secho(f"The match with id {match_id} is an invalid match.", fg="red", bold=True)
                else:
                    matches.add(match_id)
            except ValueError:
                click.secho(f"The match with id {match_id} is an invalid match.", fg="red", bold=True)
                continue
        if len(matches) == 0:
            return 'no_matches'
        return matches

    @staticmethod
    def check_match_data(match_data):
        matches = []
        for match in match_data:
            if len(match['odds']['data']) == 0:
                click.secho(f"The match {match['localTeam']['data']['name']} - {match['visitorTeam']['data']['name']} "
                            f"doesn't have any odds available (yet).", fg="red", bold=True)
            elif match['time']['status'] != 'NS':
                click.secho(f"The match {match['localTeam']['data']['name']} - {match['visitorTeam']['data']['name']} "
                            f"has already started.", fg="red", bold=True)
            else:
                matches.extend([match])
        if len(matches) == 0:
            return 'no_matches'
        return matches

    def place_bet_betting(self, matches):
        bet = Betting(self.params, self.league_data, self.writer, self, self.config_handler)
        bet.place_bet(matches)
