import requests
import click
import datetime
import json
import time

import convert
from exceptions import APIErrorException
from betting import Betting


class RequestHandler(object):
    BASE_URL = "https://v3.football.api-sports.io/"

    # API-Football fixture status codes mapped to internal state IDs
    # (used by convert.state_id_to_status and writers.py)
    _STATUS_TO_STATE_ID = {
        "NS": 1,
        "TBD": 13,
        "1H": 2,
        "HT": 3,
        "2H": 4,
        "ET": 22,
        "BT": 7,
        "P": 6,
        "SUSP": 11,
        "INT": 31,
        "FT": 5,
        "AET": 18,
        "PEN": 19,
        "PST": 10,
        "CANC": 12,
        "ABD": 20,
        "AWD": 15,
        "WO": 14,
        "LIVE": 2,
    }

    # API-Football goal detail strings → internal type IDs (convert.GOAL_TYPE_IDS keys)
    _EVENT_TYPE_IDS = {
        "Normal Goal": 14,
        "Own Goal": 15,
        "Penalty": 16,
    }

    def __init__(self, params, league_data, writer, config_handler):
        self.params = params
        self.league_data = league_data
        self.writer = writer
        self.config_handler = config_handler
        self._season_cache = {}

    def _headers(self):
        return {"x-apisports-key": self.params.get("api_token", "")}

    def show_profile(self):
        self.writer.show_profile(self.config_handler.get_data("profile"))

    def get_leagues(self):
        """Return leagues in a shape compatible with bettingbook.get_possible_leagues()."""
        items = self._get("leagues", {"current": "true"}) or []
        result = []
        for item in items:
            league = item.get("league", {})
            if league.get("id") and league.get("name"):
                result.append(
                    {
                        "id": league["id"],
                        "name": league["name"],
                        "short_code": "",
                    }
                )
        return result

    def show_leagues(self):
        leagues = self.get_leagues()
        self.writer.show_leagues(leagues)

    def _get(self, endpoint, extra_params=None):
        """GET from API-Football; handles auth, error checking, and pagination."""
        params = {}
        if self.params.get("tz") and endpoint == "fixtures":
            params["timezone"] = self.params["tz"]
        if extra_params:
            params.update(extra_params)

        req = requests.get(
            RequestHandler.BASE_URL + endpoint,
            headers=self._headers(),
            params=params,
        )
        if req.status_code != requests.codes.ok:
            self._show_request_error(req)

        body = json.loads(req.text)
        errors = body.get("errors")
        if errors:
            if isinstance(errors, dict) and errors:
                raise APIErrorException(next(iter(errors.values())))
            elif isinstance(errors, list) and errors:
                raise APIErrorException(str(errors[0]))

        data = body.get("response", [])
        paging = body.get("paging", {})
        total_pages = int(paging.get("total", 1))
        for page in range(2, total_pages + 1):
            page_params = dict(params)
            page_params["page"] = page
            next_req = requests.get(
                RequestHandler.BASE_URL + endpoint,
                headers=self._headers(),
                params=page_params,
            )
            if next_req.status_code != requests.codes.ok or not next_req.text:
                continue
            next_data = json.loads(next_req.text).get("response", [])
            if next_data:
                data.extend(next_data)
        return data

    def reset_params(self):
        self.params = {
            "api_token": self.config_handler.get("auth", "api_token"),
            "tz": self.config_handler.get("profile", "timezone"),
        }

    @staticmethod
    def _show_request_error(req):
        if req.status_code in [
            requests.codes.bad,
            requests.codes.server_error,
            requests.codes.unauthorized,
        ]:
            raise APIErrorException("Invalid request. Check your parameters.")
        elif req.status_code == requests.codes.forbidden:
            raise APIErrorException(
                "The data you requested is not accessible from your plan."
            )
        elif req.status_code == requests.codes.not_found:
            raise APIErrorException("This resource does not exist. Check parameters")
        elif req.status_code == requests.codes.too_many_requests:
            raise APIErrorException(
                "You have exceeded your allowed requests per minute/day"
            )
        elif req.status_code == requests.codes.unprocessable_entity:
            raise APIErrorException("Unprocessable request. Check your parameters.")
        else:
            raise APIErrorException("Whoops... Something went wrong!")

    def get_league_ids(self):
        league_ids = []
        for x in self.league_data:
            ids = list(x.values())[0]
            for league_id in ids:
                league_ids.extend([league_id])
        return league_ids

    def get_league_abbreviation(self, league_name):
        for x in self.league_data:
            abbreviation = list(x.keys())[0]
            ids = list(x.values())[0]
            if league_name == abbreviation:
                return ids
        return None

    # ------------------------------------------------------------------ #
    #  Normalisation: API-Football → internal shape                        #
    # ------------------------------------------------------------------ #

    def _normalize_fixture(self, item):
        """Convert an API-Football fixture object to the internal format
        expected by writers.py and convert.py."""
        fix = item["fixture"]
        league = item["league"]
        teams = item["teams"]
        goals = item.get("goals") or {}

        status_short = (fix.get("status") or {}).get("short", "NS")
        state_id = self._STATUS_TO_STATE_ID.get(status_short, 1)

        # "2021-03-17T12:00:00+00:00" → "2021-03-17 12:00:00"
        raw_date = fix.get("date", "")
        starting_at = (
            (raw_date[:10] + " " + raw_date[11:19]) if len(raw_date) >= 19 else ""
        )

        round_name, stage_name = self._parse_round(league.get("round", ""))

        events = self._normalize_events(item.get("events") or [], teams["home"]["id"])

        # Deterministic integer from country name used for sorting by league
        country_name = league.get("country", "")
        country_id = sum(ord(c) for c in country_name)

        return {
            "id": fix["id"],
            "state_id": state_id,
            "starting_at": starting_at,
            "starting_at_timestamp": fix.get("timestamp", 0),
            "minute": (fix.get("status") or {}).get("elapsed"),
            "extra_minute": (fix.get("status") or {}).get("extra"),
            "league_id": league["id"],
            "league": {
                "id": league["id"],
                "name": league["name"],
                "country_id": country_id,
            },
            "participants": [
                {
                    "id": teams["home"]["id"],
                    "name": teams["home"]["name"],
                    "meta": {"location": "home"},
                },
                {
                    "id": teams["away"]["id"],
                    "name": teams["away"]["name"],
                    "meta": {"location": "away"},
                },
            ],
            "scores": [
                {
                    "description": "CURRENT",
                    "score": {"participant": "home", "goals": goals.get("home") or 0},
                },
                {
                    "description": "CURRENT",
                    "score": {"participant": "away", "goals": goals.get("away") or 0},
                },
            ],
            # round=None → writers.groupby_round raises TypeError → falls back to stage
            "round": {"name": round_name} if round_name is not None else None,
            "stage": {"name": stage_name or "Regular Season"},
            "events": events,
            "odds": [],
            "periods": [],
        }

    def _normalize_events(self, raw_events, home_team_id):
        """Map API-Football goal events to the internal events format."""
        events = []
        for event_id, ev in enumerate(raw_events, start=1):
            if ev.get("type") != "Goal":
                continue
            type_id = self._EVENT_TYPE_IDS.get(ev.get("detail", ""))
            if type_id is None:
                continue
            events.append(
                {
                    "id": event_id,
                    "type_id": type_id,
                    "minute": (ev.get("time") or {}).get("elapsed"),
                    "player_name": (ev.get("player") or {}).get("name"),
                    "participant_id": (ev.get("team") or {}).get("id"),
                }
            )
        return events

    @staticmethod
    def _parse_round(round_str):
        """Parse "Regular Season - 27" → (27, "Regular Season").
        Returns (None, stage_name) for non-numeric rounds so writers.py
        falls back to stage grouping."""
        if not round_str:
            return None, "Regular Season"
        if " - " in round_str:
            stage, rnd = round_str.rsplit(" - ", 1)
            if rnd.strip().isdigit():
                return int(rnd.strip()), stage.strip()
        return None, round_str

    def _get_current_season(self, league_id):
        """Return the current season year for a league via /leagues?id=.
        Result is cached per league_id to avoid redundant API calls."""
        if league_id in self._season_cache:
            return self._season_cache[league_id]
        try:
            data = self._get("leagues", {"id": league_id}) or []
            if data:
                for season in data[0].get("seasons") or []:
                    if season.get("current"):
                        self._season_cache[league_id] = season["year"]
                        return season["year"]
        except (APIErrorException, KeyError, TypeError, IndexError):
            pass
        now = datetime.datetime.now()
        fallback = now.year if now.month >= 7 else now.year - 1
        self._season_cache[league_id] = fallback
        return fallback

    def _normalize_standings(self, standings_response):
        """Convert API-Football standings response to the internal format
        expected by writers.standings()."""
        league_info = standings_response.get("league", {})
        groups = league_info.get("standings", [])
        multiple_groups = len(groups) > 1
        result = []
        for group_idx, group in enumerate(groups):
            for entry in group:
                all_stats = entry.get("all", {})
                goals = all_stats.get("goals", {})
                result.append(
                    {
                        "stage_id": 1,
                        "group_id": group_idx if multiple_groups else None,
                        "position": entry.get("rank", 0),
                        "points": entry.get("points", 0),
                        "result": entry.get("description") or "",
                        "participant": {
                            "name": (entry.get("team") or {}).get("name", "Unknown")
                        },
                        "stage": {"name": league_info.get("name", "")},
                        "group": (
                            {"name": entry.get("group", "")}
                            if multiple_groups
                            else None
                        ),
                        "details": [
                            {"type_id": 129, "value": all_stats.get("played", 0)},
                            {"type_id": 130, "value": all_stats.get("win", 0)},
                            {"type_id": 131, "value": all_stats.get("draw", 0)},
                            {"type_id": 132, "value": all_stats.get("lose", 0)},
                            {"type_id": 133, "value": goals.get("for", 0)},
                            {"type_id": 134, "value": goals.get("against", 0)},
                        ],
                    }
                )
        return result

    # ------------------------------------------------------------------ #
    #  Fixture fetching helpers                                            #
    # ------------------------------------------------------------------ #

    def _fetch_live(self, league_ids=None):
        """Fetch live fixtures. One API call."""
        if league_ids:
            live_param = "-".join(str(lid) for lid in league_ids)
        else:
            live_param = "all"
        items = self._get("fixtures", {"live": live_param}) or []
        return [self._normalize_fixture(item) for item in items]

    def _fetch_today(self, league_ids=None):
        """Fetch today's fixtures.
        Without a league filter: one API call for all plan leagues.
        With a league filter: one call per league ID."""
        today = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d")
        if league_ids:
            fixtures = []
            for league_id in league_ids:
                season = self._get_current_season(league_id)
                items = (
                    self._get(
                        "fixtures",
                        {"date": today, "league": league_id, "season": season},
                    )
                    or []
                )
                fixtures.extend(self._normalize_fixture(item) for item in items)
            return fixtures
        items = self._get("fixtures", {"date": today}) or []
        return [self._normalize_fixture(item) for item in items]

    def _fetch_range(self, start, end, league_ids=None):
        """Fetch fixtures for a date range.
        API-Football requires league + season for range queries, so one
        call per league ID."""
        all_ids = league_ids or self.get_league_ids()
        fixtures = []
        for league_id in all_ids:
            season = self._get_current_season(league_id)
            items = (
                self._get(
                    "fixtures",
                    {
                        "league": league_id,
                        "season": season,
                        "from": start,
                        "to": end,
                    },
                )
                or []
            )
            fixtures.extend(self._normalize_fixture(item) for item in items)
        return fixtures

    def _attach_odds(self, fixtures):
        """Fetch Match Winner odds for each NS fixture and attach inline.
        Only called when -O / --odds is requested."""
        label_map = {"Home": "1", "Draw": "X", "Away": "2"}
        for fixture in fixtures:
            if convert.state_id_to_status(fixture.get("state_id", 1)) != "NS":
                continue
            try:
                odds_data = (
                    self._get("odds", {"fixture": fixture["id"], "bet": 1}) or []
                )
                if not odds_data:
                    continue
                for bookmaker in odds_data[0].get("bookmakers") or []:
                    for bet in bookmaker.get("bets") or []:
                        if bet.get("name") != "Match Winner":
                            continue
                        for val in bet.get("values") or []:
                            label = label_map.get(val.get("value", ""))
                            if label:
                                fixture["odds"].append(
                                    {"label": label, "value": val.get("odd", "0")}
                                )
                        break
                    break
            except (APIErrorException, KeyError, IndexError, TypeError):
                pass

    def _attach_events(self, fixtures):
        """Fetch goal events per started fixture for --details display.
        API-Football does not include events in list responses."""
        for fixture in fixtures:
            if fixture.get("state_id", 1) in (1, 10, 12, 13):
                continue
            try:
                raw_events = (
                    self._get("fixtures/events", {"fixture": fixture["id"]}) or []
                )
                home_id = next(
                    (
                        p["id"]
                        for p in fixture.get("participants", [])
                        if p["meta"]["location"] == "home"
                    ),
                    None,
                )
                fixture["events"] = self._normalize_events(raw_events, home_id)
            except (APIErrorException, KeyError, TypeError):
                pass

    # ------------------------------------------------------------------ #
    #  Public interface (unchanged from Sportmonks version)               #
    # ------------------------------------------------------------------ #

    def set_params(self, include_odds=False):
        pass  # no-op: params are now passed explicitly per _get() call

    @staticmethod
    def set_start_end(days):
        now = datetime.datetime.now()
        if days < 0:
            start = datetime.datetime.strftime(
                now + datetime.timedelta(days=days), "%Y-%m-%d"
            )
            end = datetime.datetime.strftime(
                now - datetime.timedelta(days=1), "%Y-%m-%d"
            )
        else:
            start = datetime.datetime.strftime(now, "%Y-%m-%d")
            end = datetime.datetime.strftime(
                now + datetime.timedelta(days=days), "%Y-%m-%d"
            )
        return start, end

    def get_matches(self, parameters):
        if parameters.league_name:
            if parameters.refresh:
                while True:
                    self.get_match_data_for_leagues(parameters)
                    time.sleep(60)
            else:
                self.get_match_data_for_leagues(parameters)
        else:
            if parameters.refresh:
                while True:
                    self.try_to_get_match_data(parameters)
                    time.sleep(60)
            else:
                self.try_to_get_match_data(parameters)

    def get_match_data_for_leagues(self, parameters):
        for i, league_abbr in enumerate(parameters.league_name):
            league_ids = self.get_league_abbreviation(league_abbr)
            if not league_ids:
                continue
            self.try_to_get_match_data(parameters, i == 0, league_ids=league_ids)

    def try_to_get_match_data(self, parameters, first=False, league_ids=None):
        start, end = self.set_start_end(parameters.days)
        try:
            self.get_match_data(parameters, start, end, first, league_ids=league_ids)
        except APIErrorException as e:
            if parameters.show_odds and "not accessible from your plan" in str(e):
                click.secho(
                    "Odds not available on your plan, showing matches without odds.",
                    fg="yellow",
                    bold=True,
                )
                try:
                    self.get_match_data(
                        parameters,
                        start,
                        end,
                        first,
                        league_ids=league_ids,
                        include_odds=False,
                    )
                except APIErrorException as e2:
                    click.secho(str(e2), fg="red", bold=True)
            else:
                click.secho(str(e), fg="red", bold=True)

    def get_match_data(
        self, parameters, start, end, first=False, league_ids=None, include_odds=None
    ):
        if include_odds is None:
            include_odds = parameters.show_odds or parameters.place_bet

        type_sort = parameters.type_sort
        if type_sort == "live":
            fixtures = self._fetch_live(league_ids)
        elif type_sort == "today":
            fixtures = self._fetch_today(league_ids)
        else:
            fixtures = self._fetch_range(start, end, league_ids)

        if include_odds and fixtures:
            self._attach_odds(fixtures)

        if parameters.show_details and fixtures:
            self._attach_events(fixtures)

        if not fixtures:
            if type_sort == "matches":
                if parameters.days < 0:
                    click.secho(
                        f"No matches in the past {abs(parameters.days)} days.",
                        fg="red",
                        bold=True,
                    )
                else:
                    click.secho(
                        f"No matches in the coming {parameters.days} days.",
                        fg="red",
                        bold=True,
                    )
            else:
                click.secho(parameters.msg[0], fg="red", bold=True)
            return

        bet_matches = self.writer.league_scores(fixtures, parameters, first)
        if parameters.place_bet:
            if bet_matches:
                self.place_bet(bet_matches)
            else:
                click.secho(
                    "There are no matches in the selected timespan to bet on.",
                    fg="red",
                    bold=True,
                )

    def get_multi_matches(self, match_ids, predictions, parameters):
        if not match_ids:
            click.secho(parameters.msg[0], fg="red", bold=True)
            return True
        ids_param = "-".join(match_ids.split(","))
        items = self._get("fixtures", {"ids": ids_param}) or []
        fixtures = [self._normalize_fixture(item) for item in items]
        if not fixtures:
            click.secho(parameters.msg[0], fg="red", bold=True)
            return
        self.writer.league_scores(fixtures, parameters, True, predictions)

    def get_standings(self, leagues, show_details):
        for league in leagues:
            for league_id in self.get_league_abbreviation(league):
                try:
                    season = self._get_current_season(league_id)
                    standings_data = self._get(
                        "standings", {"league": league_id, "season": season}
                    )
                    if not standings_data:
                        continue
                    normalized = self._normalize_standings(standings_data[0])
                    if not normalized:
                        continue
                    self.writer.standings(normalized, league_id, show_details)
                except APIErrorException as e:
                    click.secho(str(e), fg="red", bold=True)
                except (KeyError, TypeError):
                    pass

    def place_bet(self, bet_matches):
        match_bet = click.prompt(
            "Give the numbers of the matches you want to bet on (comma-separated)"
        ).split(",")
        match_bet = sorted(self.check_match_bet(match_bet, len(bet_matches)))
        if match_bet == "no_matches":
            click.secho("There are no valid matches selected.", fg="red", bold=True)
        else:
            matches = []
            for match_id in match_bet:
                try:
                    matches.extend([str(bet_matches[int(match_id) - 1])])
                except (IndexError, ValueError):
                    pass
            match_data = self.get_match_bet(",".join(matches))
            match_data = self.check_match_data(match_data)
            if match_data == "no_matches":
                click.secho("There are no valid matches selected.", fg="red", bold=True)
            else:
                self.place_bet_betting(match_data)

    def get_match_bet(self, matches):
        """Fetch fixtures by ID and attach odds (used by the betting workflow)."""
        ids_param = "-".join(matches.split(","))
        items = self._get("fixtures", {"ids": ids_param}) or []
        fixtures = [self._normalize_fixture(item) for item in items]
        self._attach_odds(fixtures)
        return fixtures

    @staticmethod
    def check_match_bet(match_bet, max_match_id):
        matches = set()
        for match_id in match_bet:
            try:
                if int(match_id) < 1 or int(match_id) > max_match_id:
                    click.secho(
                        f"The match with id {match_id} is an invalid match.",
                        fg="red",
                        bold=True,
                    )
                else:
                    matches.add(match_id)
            except ValueError:
                click.secho(
                    f"The match with id {match_id} is an invalid match.",
                    fg="red",
                    bold=True,
                )
        if not matches:
            return "no_matches"
        return matches

    @staticmethod
    def check_match_data(match_data):
        matches = []
        for match in match_data:
            home = convert.get_home_team(match).get("name", "")
            away = convert.get_away_team(match).get("name", "")
            status = convert.state_id_to_status(match.get("state_id"))
            if not match.get("odds"):
                click.secho(
                    f"The match {home} - {away} doesn't have any odds available (yet).",
                    fg="red",
                    bold=True,
                )
            elif status != "NS":
                click.secho(
                    f"The match {home} - {away} has already started.",
                    fg="red",
                    bold=True,
                )
            else:
                matches.append(match)
        return matches if matches else "no_matches"

    def place_bet_betting(self, matches):
        bet = Betting(
            self.params, self.league_data, self.writer, self, self.config_handler
        )
        bet.place_bet(matches)
