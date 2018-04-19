import requests
import click
import datetime
import json

import exceptions


class GetData(object):
    BASE_URL = 'https://soccer.sportmonks.com/api/v2.0/'

    def __init__(self, params, league_ids, writer):
        self.params = params
        self.league_ids = league_ids
        self.writer = writer

    def show_profile(self, profiledata):
        self.writer.show_profile(profiledata)

    def _get(self, url):
        """Handles soccer.sportsmonks requests"""
        req = requests.get(GetData.BASE_URL + url, params=self.params)

        if req.status_code == requests.codes.ok:
            data = self.get_data(req, url)
            return req, data

        if req.status_code == requests.codes.bad:
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
                req = requests.get(GetData.BASE_URL + url, params=self.params)
                next_parts = json.loads(req.text)
                next_data = next_parts.get('data')
                if next_data:
                    data.extend(next_data)
        return data

    def get_countries(self):
        coun = []
        url = 'countries'

        response, countries = self._get(url)

        for country in countries:
            contry_name = country['name']
            country_id = country['id']
            if contry_name not in coun:
                coun.extend([[contry_name, country_id]])
        coun = sorted(coun, key=lambda x: str(x[0]))

        return coun

    def get_competitions(self):
        comp = []
        url = 'leagues'

        response, competitions = self._get(url)

        for competition in competitions:
            competition_name = competition['name']
            competition_id = competition['id']
            if competition_name not in comp:
                comp.extend([[competition_name, competition_id]])

        comp = sorted(comp, key=lambda x: str(x[0]))

        return comp

    def get_today_scores(self):
        """Gets the scores for today"""
        url = 'livescores'

        self.params['leagues'] = ','.join(str(val) for val in self.league_ids.values())
        self.params['include'] = 'localTeam,visitorTeam'
        response, scores = self._get(url)

        if response.status_code == requests.codes.ok:
            if len(scores) == 0:
                click.secho("No matches today", fg="red", bold=True)
                return
            self.writer.today_scores(scores)
        else:
            click.secho("There was problem getting todays scores", fg="red", bold=True)

    def get_live_scores(self):
        """Gets the live scores"""
        url = 'livescores/now'

        self.params['leagues'] = ','.join(str(val) for val in self.league_ids.values())
        self.params['include'] = 'localTeam,visitorTeam'
        response, scores = self._get(url)

        if response.status_code == requests.codes.ok:
            if len(scores) == 0:
                click.secho("No live action currently", fg="red", bold=True)
                return
            self.writer.today_scores(scores)
        else:
            click.secho("There was problem getting live scores", fg="red", bold=True)

    def get_matches(self, league_id, time, show_history):
        """
        Queries the API and fetches the scores for fixtures
        based upon the league and time parameter
        """
        url = 'fixtures/between/'
        now = datetime.datetime.now()

        self.params['leagues'] = ','.join(str(val) for val in self.league_ids.values())
        self.params['include'] = 'localTeam,visitorTeam,league'

        if show_history:
            start = datetime.datetime.strftime(now - datetime.timedelta(days=time), '%Y-%m-%d')
            end = datetime.datetime.strftime(now - datetime.timedelta(days=1), '%Y-%m-%d')
        else:
            start = datetime.datetime.strftime(now, '%Y-%m-%d')
            end = datetime.datetime.strftime(now + datetime.timedelta(days=time), '%Y-%m-%d')
        if league_id:
            try:
                league_name = self.league_ids[league_id]
                self.params['leagues'] = league_name
                response, fixtures_results = self._get(url + f'{start}/{end}')
                # no fixtures in the timespan. display a help message and return
                if len(fixtures_results) == 0:
                    if show_history:
                        click.secho("No {league} matches in the past {days} days.".format(league=league_id,
                                                                                          days=time),
                                    fg="red", bold=True)
                    else:
                        click.secho("No {league} matches in the coming {days} days.".format(league=league_id,
                                                                                            days=time),
                                    fg="red", bold=True)
                    return
                self.writer.league_scores(fixtures_results)
            except exceptions.APIErrorException:
                click.secho("No data for the given league.", fg="red", bold=True)
        else:
            try:
                response, fixtures_results = self._get(url + f'{start}/{end}')
                if len(fixtures_results) == 0:
                    if show_history:
                        click.secho("No {league} matches in the past {days} days.".format(league=league_id,
                                                                                          days=time),
                                    fg="red", bold=True)
                    else:
                        click.secho("No {league} matches in the coming {days} days.".format(league=league_id,
                                                                                            days=time),
                                    fg="red", bold=True)
                    return
                self.writer.league_scores(fixtures_results)
            except exceptions.APIErrorException:
                click.secho("No data available.", fg="red", bold=True)
