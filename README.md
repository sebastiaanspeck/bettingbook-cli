BettingBook CLI
=====

A CLI to keep track of your soccer bets.

Install
=====

An API key from [sportsmonks.com](https://sportmonks.com/) will be required and you can register for one [here](http://sportsmonks.com/register).

### Build from source

```bash
$ git clone https://github.com/sebastiaanspeck/bettingbook-cli.git
$ cd bettingbook-cli/bettingbook
```

#### Note:
Currently supports Windows. Might work on other platforms, but this is not yet tested.

To get colorized terminal output on Windows, make sure to install [ansicon](https://github.com/adoxa/ansicon/releases/latest) and [colorama](https://pypi.python.org/pypi/colorama).

Usage
====

### View live scores from various leagues

```bash
$ main.py --live
```

### View matches from various leagues for today

```bash
$ main.py --today
```

#### Note:
--live only shows the matches that are live now or are finished, to view games that have not started yet, use --today

### Get scores for all leagues with a set time period

```bash
$ main.py --matches --days=10 # get scores for all the seven leagues over the coming 10 days
```

### Get scores for a particular league

```bash
$ main.py --matches --league=DE1 # DE1 is the league code for Bundesliga
$ main.py --matches --league=FR1 --history --days=15 # get scores for all the French Ligue 1 games over the past 15 days
$ main.py --matches --league=EN1 --history --details # get scores for all the Premier League games over the past 6 days and showing the goalscorers.
```

### View account details

```bash
$ main.py --account
```

### Help
```bash
$ main.py --help
```
### List of supported leagues and their league codes

- England:
  - EN1: Premier League
- Netherlands:
  - NL1: Eredivisie
- Germany:
  - DE1: Bundesliga
- Belgium:
  - BE1: Jupiler Pro League
- France:
  - FR1: Ligue 1
- Italy:
  - IT1: Serie A
- Spain:
  - ES1: Primera Division

### Supported leagues

For a full list of supported leagues [see this](bettingbook/leagueids.py).

### Commands and possible arguments
- --live: --league, --details
- --today: --league, --details
- --matches: --league, --days, --history, --details
- --standings: ---league

Todo
====
- [ ] Add more competitions (divisions under the first divisions)
- [ ] Add cups
- [ ] Add Champions League and Europa League
- [x] Add detailed information to match results
- [x] Add detailed information to match results in games where both teams scored
- [x] Add league filter for live scores
- [x] Add league standings
- [ ] Add --details to league standings (details are won, draw, lost, goal for, goal against)
- [ ] Add option to get matches for a specific team
- [ ] Add odds to match overviews
- [x] Add color coding for Europa league and Champions League
- [x] Differentiation between straight CL and CL playoff spots, and the same for EL spots
- [ ] Add betting functions
- [ ] A built-in watch feature so you can run once with --live and just leave the program running.

License
====
Open sourced under [MIT License](LICENSE)

Notes
===
This project is still in development
