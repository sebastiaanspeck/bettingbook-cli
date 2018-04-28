import requests
import click
import datetime
import json

import exceptions


class RequestHandler(object):
    BASE_URL = 'https://soccer.sportmonks.com/api/v2.0/'

    def __init__(self, params, league_data, writer):
        self.params = params
        self.league_data = league_data
        self.writer = writer

    def show_profile(self, profiledata):
        self.writer.show_profile(profiledata)

    def _get(self, url):
        """Handles soccer.sportsmonks requests"""
        req = requests.get(RequestHandler.BASE_URL + url, params=self.params)

        if req.status_code == requests.codes.ok:
            data = self.get_data(req, url)
            return req, data

        if req.status_code in [requests.codes.bad, requests.codes.server_error]:
            raise exceptions.APIErrorException('Invalid request. Check parameters.')

        if req.status_code == requests.codes.forbidden:
            raise exceptions.APIErrorException('This resource is restricted')

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

    def get_matches(self, parameters):
        """
        Queries the API and fetches the scores for fixtures
        based upon the league and time parameter
        """
        now = datetime.datetime.now()

        league_ids = self.get_league_ids()

        self.params['leagues'] = ','.join(val for val in league_ids)
        self.params['include'] = 'localTeam,visitorTeam,league,round,events,stage,flatOdds:filter(bookmaker_id|2)'

        if parameters.show_history:
            start = datetime.datetime.strftime(now - datetime.timedelta(days=parameters.days), '%Y-%m-%d')
            end = datetime.datetime.strftime(now - datetime.timedelta(days=1), '%Y-%m-%d')
        else:
            start = datetime.datetime.strftime(now + datetime.timedelta(days=1), '%Y-%m-%d')
            end = datetime.datetime.strftime(now + datetime.timedelta(days=parameters.days), '%Y-%m-%d')
        if parameters.league_name:
            try:
                league_id = self.get_league_abbrevation(parameters.league_name)
                self.params['leagues'] = ','.join(str(val) for val in league_id)
                self.get_match_data(parameters, start, end)
            except exceptions.APIErrorException:
                click.secho("No data for the given league.", fg="red", bold=True)
        else:
            try:
                self.get_match_data(parameters, start, end)
            except exceptions.APIErrorException:
                click.secho("No data available.", fg="red", bold=True)

    def get_match_data(self, parameters, start, end):
        if parameters.type_sort == "matches":
            response, fixtures_results = self._get(parameters.url + f'{start}/{end}')
        else:
            response, fixtures_results = self._get(parameters.url)
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
        self.writer.league_scores(fixtures_results, parameters)

    def get_standings(self, league_name):
        for league_id in self.get_league_abbrevation(league_name):
            url = f'leagues/{league_id}'
            try:
                _, league_data = self._get(url)
                current_season_id = league_data['current_season_id']
                url = f'standings/season/{current_season_id}'
                _, standings_data = self._get(url)
                if len(standings_data) == 0:
                    click.secho(f"\nLOG: No standings availble for {league_name} with id {league_id}.\n",
                                fg="red", bold=True)
                    continue
                self.writer.standings(standings_data, league_id)
            except exceptions.APIErrorException:
                # Click handles incorrect League codes so this will only come up
                # if that league does not have standings available. ie. Champions League
                click.secho(f"No standings availble for {league_name}.", fg="red", bold=True)
