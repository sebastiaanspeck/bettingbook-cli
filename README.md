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

### View your bettingbook

```bash
$ python main.py --bettingbook
```

### View account details

```bash
$ python main.py --account
```

### Place bet

```bash
$ python main.py --bet # This shows all bets for today
$ python main.py --bet --league=PL # This shows all bets in a specific league for today (PL is Premier League)
```

### View matches from various leagues for today

```bash
$ soccer --today
```

### View live scores from various leagues

```bash
$ soccer --live
```

#### Note:
--live only shows the matches that are live now or are finished, to view have not started yet, use --today


### Get scores for a particular league

```bash
$ soccer --league=BL # BL is the league code for Bundesliga
$ soccer --league=FL --time=15 # get scores for all the French Ligue games over the past 15 days
```

### Get information about players of a team

```bash
$ soccer --team=JUVE --players
```

### Get scores for all seven leagues with a set time period

```bash
$ soccer --time=10 # get scores for all the seven leagues over the past 10 days
```

### Help
```bash
$ soccer --help
```
### List of supported leagues and their league codes

- England:
  - GB1: Premier League
- France:
  - FR1: Ligue 1
- Germany:
  - DE1: Bundesliga
- Italy:
  - IT1: Serie A
- Netherlands:
  - NL1: Eredivisie
- Spain:
  - ES1: La Liga

### Team and team codes

For a full list of supported leagues [see this](bettingbook/leagues.json).

Todo
====
- [x] Add more competitions
- [x] Add league filter for live scores
- [ ] Add league standings
- [ ] Add odds to match overviews
- [ ] Color coding for Europa league and differentiation between straight CL and CL playoff spots, and the same for EL spots
- [ ] A built in watch feature so you can run once with --live and just leave the program running.

License
====
Open sourced under [MIT License](LICENSE)

Notes
===
This project is still in development
