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
$ main.py --matches --league=NL1 --history --odds # get odds for all the Eredivisie games over the past 6 days and showing the odds (in corresponding colors).
```

### View account details

```bash
$ main.py --account
```

### Help
```bash
$ main.py --help
```
### List of supported leagues & cups and their league codes

- Germany:
  - DE1: Bundesliga
  - DEC: DFB Pokal
- France:
  - FR1: Ligue 1
  - FRC: Coupe de France
- Spain:
  - ES1: La Liga
  - ESC: Copa Del Rey
- Italy:
  - IT1: Serie A
  - ITC: Coppa Italia
- England:
  - EN1: Premier League
  - ENC: FA Cup
- Netherlands:
  - NL1: Eredivisie
  - NL2: Jupiler League/Eerste Divisie
  - NLC: KNVB Beker
- Belgium:
  - BE1: Pro League
  - BEC: Belgian Cup
- Europe:
  - CL: Champions League
  - EL: Europa League
  - WCEQ: WC Qualification Europe
  - WC: World Cup
  - EQ: Euro Qualification
  - EC: European Chamionship

### Supported leagues & cups

For a full list of supported leagues & cups [see this](bettingbook/leagues.json).

### Commands and possible arguments
- --live (-L):
  - --league (-l)
  - --details (-D)
  - --odds (-O)
- --today (-T):
  - --league (-l)
  - --details (-D)
  - --odds (-O)
- --matches (-M):
  - --league (-l)
  - --days (-d)
  - --history (-H)
  - --details (-D)
  - --odds (-O)
- --standings (-S):
  - --league (-l)

Commands (live, today, matches, standings) and flags (details, odds, history) can be used like -UPPERCASE.  
Parameters (league, days) can also be used like -lowercase


### Abbreviations
The abbreviations you can see when using live, today or matches are explained down here:

Abbreviation | Definition | Information
--- | --- | ---
NS |	Not Started	| The initial status of a game
LIVE |	Live |	The game is currently inplay
HT |	Half-Time |	The game currently is in half-time
FT |	Full-Time	| The game has ended after 90 minutes
ET |	Extra-Time |	The game currently is in extra time, can happen in knockout games
PEN_LIVE |	Penalty Shootout |	ET status didn't get a winner, penalties are taken to determine the winner
AET |	Finished after extra time	| The game has finished after 120 minutes
BREAK |	Regular time finished	| Waiting for extra time or penalties to start
FT_PEN | Full-Time after penalties |	Finished after penalty shootout
CANCL |	Cancelled	| The game has been cancelled
POSTP	| Postponed	| The game has been postponed
INT	| Interrupted	| The game has been interrupted. Can be due to bad weather
ABAN | Abandoned | The game has abandoned and will continue at a later time or day
SUSP | Suspended | The game has suspended and will continue at a later time or day
AWARDED	| Awarded |	Winner is beeing decided externally
DELAYED	| Delayed	| The game is delayed so it wil start later
TBA	| To Be Announced	| Fixture will be updated with exact time later
WO | Walkover	| Awarding of a victory to a contestant because there are no other contestants
AU | Awaiting Updates | Can occur when there is a connectivity issue or something


Todo
====
- [ ] Add more competitions (divisions under the first divisions)
- [ ] Add option to get matches for a specific team
- [ ] Add betting functions
- [ ] A built-in watch feature so you can run once with --live and just leave the program running.
- [x] Add odds to match overviews
- [x] Add color coding for Europa league and Champions League
- [x] Add cups
- [x] Add Champions League and Europa League
- [x] Add detailed information to match results
- [x] Add league filter for live scores
- [x] Add league standings
- [x] Add --details to league standings (details are won, draw, lost, goal for, goal against)

License
====
Open sourced under [MIT License](LICENSE)

Notes
===
This project is still in development
