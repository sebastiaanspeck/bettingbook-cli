import click
from collections import namedtuple

from config_handler import ConfigHandler
from request_handler import RequestHandler
from json_handler import JsonHandler
from exceptions import IncorrectParametersException
from writers import get_writer
from betting import Betting
import convert
import time

jh = JsonHandler()
LEAGUES_DATA = jh.load_leagues()
LEAGUES = [list(x.keys())[0] for x in LEAGUES_DATA]


def get_params(api_token, timezone):
    params = {}
    if api_token:
        params['api_token'] = api_token
    else:
        params['api_token'] = ch.get('auth', 'api_token')
    if timezone:
        params['tz'] = timezone
    else:
        params['tz'] = ch.get('profile', 'timezone')
    return params


def check_options(history, bet, live, today, refresh, matches):
    if history and live or history and today:
        raise IncorrectParametersException('--history and --days is not supported for --live/--today. '
                                           'Use --matches to use these parameters')
    if bet and live:
        raise IncorrectParametersException('--bet is not yet supported for --live. '
                                           'Use --matches or --today to use this parameters')
    if matches and refresh:
        raise IncorrectParametersException('--refresh is not supported for --matches. '
                                           'Use --live or --today to use this parameters')


def check_options_standings(leagues, history):
    if not leagues:
        raise IncorrectParametersException("Please specify a league. "
                                           "Example --standings --league=EN1")
    if history:
        raise IncorrectParametersException("--history and --days is not supported for --standings. "
                                           "Use --matches to use these parameters")
    for league in leagues:
        if league.endswith("C") and league not in ["WC", "EC"]:
            raise IncorrectParametersException(f"Standings for {league} not supported")


ch = ConfigHandler()


@click.command()
@click.option('--api_token', default=ch.load_config_file,
              help="API key to use.")
@click.option('--timezone', default=ch.load_config_file,
              help="Timezone to use. See https://bit.ly/2glGdNY "
                   "for a list of accepted timezones")
@click.option('--live', '-L', is_flag=True,
              help="Shows live scores from various leagues.")
@click.option('--today', '-T', is_flag=True,
              help="Shows matches from various leagues for today.")
@click.option('--matches', '-M', is_flag=True,
              help="Shows matches from various leagues for a longer period.")
@click.option('--standings', '-S', is_flag=True,
              help="Standings for a particular league.")
@click.option('--league', '-l', type=click.Choice(LEAGUES), multiple=True,
              help="Show fixtures from a particular league.")
@click.option('--days', '-d', default=7, show_default=True,
              help=("The number of days in the future for which you "
                    "want to see the scores, or the number of days "
                    "in the past when used with --history"))
@click.option('--history', '-H', is_flag=True, default=False,
              help="Displays past games when used with --time command.")
@click.option('--details', '-D', is_flag=True, default=False,
              help="Displays goal-scorers under the score and a more detailed standing.")
@click.option('--odds', '-O', is_flag=True, default=False,
              help="Displays the odds above the score.")
@click.option('--not-started', '-NS', is_flag=True, default=False,
              help="Only show matches that haven't started yet")              
@click.option('--refresh', '-R', is_flag=True, default=False,
              help="Refresh the data every minute.")
@click.option('--bet', '-B', is_flag=True, default=False,
              help="Place a bet.")
@click.option('--profile', '-P', is_flag=True,
              help="Show your profile (name, balance, timezone)")
@click.option('--all-bets', '-AB', is_flag=True,
              help="Show all your bets")
@click.option('--open-bets', '-OB', is_flag=True,
              help="Show your open bets")
@click.option('--closed-bets', '-CB', is_flag=True,
              help="Show your closed bets")
@click.option('--watch-bets', '-WB', is_flag=True,
              help="Watch all matches you've placed a bet on")              
@click.option('--possible-leagues', '-PL', is_flag=True,
              help="Show all leagues that are in your Sportmonks API Plan.")
def main(api_token, timezone, live, today, matches, standings, league, days, history, details, odds, not_started, refresh, bet,
         profile, all_bets, open_bets, closed_bets, watch_bets, possible_leagues):
    params = get_params(api_token, timezone)

    try:
        writer = get_writer()
        rh = RequestHandler(params, LEAGUES_DATA, writer, ch)
        betting = Betting(params, LEAGUES_DATA, writer, rh, ch)
        betting.main()

        Parameters = namedtuple("parameters", "url, msg, league_name, days, "
                                              "show_history, show_details, show_odds, not_started, refresh, place_bet, date_format, type_sort")


        def get_multi_matches(filename, parameters):
            bets = betting.get_bets(ch.get_data('betting_files')[filename])
            match_ids = ','.join([i[0] for i in bets])
            predictions = [i[0] + ';' + i[1] for i in bets]
            return rh.get_multi_matches(match_ids, predictions, parameters)

        def bet_matches(type):    
            date_format = convert.format_date(ch.get('profile', 'date_format'))
            parameters = Parameters('fixtures/multi',
                                    ["No open bets at the moment.",
                                    "There was problem getting live scores, check your parameters"],
                                    None, None, None, details, True, False, True, None, date_format, 'watch_bets')
            if type == 'open' and watch_bets:
                filename = 'open_bets'
                while True:
                    quit = get_multi_matches(filename, parameters)
                    if quit:
                        return
                    else:    
                        time.sleep(60)
            elif type == 'open':
                filename = 'open_bets'
            else:    
                filename = 'closed_bets'

            get_multi_matches(filename, parameters)
            return

        if live or today or matches:
            check_options(history, bet, live, today, refresh, matches)
            date_format = convert.format_date(ch.get('profile', 'date_format'))
            if bet:
                odds = True
            if live:
                not_started = False
                parameters = Parameters('livescores/now',
                                        ["No live action at this moment",
                                         "There was problem getting live scores, check your parameters"],
                                        league, days, history, details, odds, not_started, refresh, bet, date_format, "live")
            elif today:
                parameters = Parameters('livescores',
                                        ["No matches today",
                                         "There was problem getting today's scores, check your parameters"],
                                        league, days, history, details, odds, not_started, refresh, bet, date_format, "today")
            else:
                parameters = Parameters('fixtures/between/',
                                        [[f"No matches in the past {str(days)} days."],
                                         [f"No matches in the coming {str(days)} days."]],
                                        league, days, history, details, odds, not_started, refresh, bet, date_format, "matches")
            rh.get_matches(parameters)
            return

        if standings:
            check_options_standings(league, history)
            rh.get_standings(league, details)
            return

        if profile:
            rh.show_profile()
            return

        if all_bets:
            betting.view_bets('open')
            betting.view_bets('closed')
            return

        if open_bets:
            if details:
                bet_matches('open')
            else:  
                betting.view_bets('open')
            return

        if closed_bets:
            if details:
                bet_matches('closed')
            else:    
                betting.view_bets('closed')
            return

        if watch_bets:
            bet_matches('open')

        if possible_leagues:
            rh.show_leagues()
            return

    except IncorrectParametersException as e:
        click.secho(str(e), fg="red", bold=True)


if __name__ == '__main__':
    main()
