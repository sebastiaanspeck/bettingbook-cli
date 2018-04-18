import requests
import exceptions
import click


class GetData(object):
    BASE_URL = 'https://soccer.sportmonks.com/api/v2.0/'

    def __init__(self, params, league_ids, writer):
        self.params = params
        self.league_ids = league_ids
        self.writer = writer

    def _get(self, url):
        req = requests.get(GetData.BASE_URL + url, params=self.params)

        if req.status_code == requests.codes.ok:
            return req

        if req.status_code == requests.codes.bad:
            raise exceptions.APIErrorException('Invalid request. Check parameters.')

        if req.status_code == requests.codes.forbidden:
            raise exceptions.APIErrorException('This resource is restricted')

        if req.status_code == requests.codes.not_found:
            raise exceptions.APIErrorException('This resource does not exist. Check parameters')

        if req.status_code == requests.codes.too_many_requests:
            raise exceptions.APIErrorException('You have exceeded your allowed requests per minute/day')

    def get_countries(self):
        coun = []
        url = 'countries'

        response = self._get(url)

        countries = response.json()['data']

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

        response = self._get(url)

        comptitions = response.json()['data']

        for competition in comptitions:
            competition_name = competition['name']
            competition_id = competition['id']
            if competition_name not in comp:
                comp.extend([[competition_name, competition_id]])

        comp = sorted(comp, key=lambda x: str(x[0]))

        return comp

    def get_today_scores(self):
        url = 'livescores'

        self.params['leagues'] = ','.join(str(val) for val in self.league_ids.values())
        self.params['include'] = 'localTeam,visitorTeam'
        response = self._get(url)

        if response.status_code == requests.codes.ok:
            scores = response.json()['data']
            if len(scores) == 0:
                click.secho("No matches today", fg="red", bold=True)
                return
            self.writer.today_scores(scores)
        else:
            click.secho("There was problem getting todays scores", fg="red", bold=True)

    def get_live_scores(self):
        url = 'livescores/now'

        self.params['leagues'] = ','.join(str(val) for val in self.league_ids.values())
        self.params['include'] = 'localTeam,visitorTeam'
        response = self._get(url)

        if response.status_code == requests.codes.ok:
            scores = response.json()['data']
            if len(scores) == 0:
                click.secho("No live action currently", fg="red", bold=True)
                return
            self.writer.today_scores(scores)
        else:
            click.secho("There was problem getting live scores", fg="red", bold=True)
