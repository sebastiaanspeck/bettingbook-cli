# BettingBook CLI

A CLI to keep track of your soccer bets.

## Install

An API key from [Sportsmonks](https://sportmonks.com/) will be required and you should [register](http://sportmonks.com/register) yourself to get an API Key.

## Build from source

```bash
git clone https://github.com/sebastiaanspeck/bettingbook-cli.git
cd bettingbook-cli/src
```

### Notes

- Currently only tested on Windows and MacOS with Python 3. Might work on other platforms, but this is not yet tested.

- To get colorized terminal output on Windows, make sure to install [ansicon](https://github.com/adoxa/ansicon/releases/latest) and [colorama](https://pypi.python.org/pypi/colorama).

- You need the packages click and requests. You can install these using pip (pip install \<package\>).

## Usage

### View live scores from various leagues

```bash
bettingbook.py --live
```

### View matches from various leagues for today

```bash
bettingbook.py --today
```

#### Note

--live only shows the matches that are live now or are finished, to view games that have not started yet, use --today

### Get scores for all leagues with a set time period

```bash
bettingbook.py --matches --days=10 # get scores for all leagues over the coming 10 days
```

### Get scores for a particular league

```bash
bettingbook.py --matches --league=DE1 # DE1 is the league code for Bundesliga
bettingbook.py --matches --league=FR1 --history --days=15 # get scores for all the French Ligue 1 games over the past 15 days
bettingbook.py --matches --league=EN1 --history --details # get scores for all the Premier League games over the past 6 days and showing the goalscorers.
bettingbook.py --matches --league=NL1 --history --odds # get odds for all the Eredivisie games over the past 6 days and showing the odds (in corresponding colors).
```

### View all your bets

```bash
bettingbook.py --all-bets
```

### View profile details

```bash
bettingbook.py --profile
```

### Help

```bash
bettingbook.py --help
```

## Supported leagues & cups

For a full list of supported leagues & cups [see this](src/league_files/all_leagues.json) or run:

```bash
bettingbook.py --all-leagues
```

## Commands and possible arguments

- --live (-L):
  - --league (-l)
  - --details (-D)
  - --odds (-O)
  - --bet (-B)
  - --refresh (-R)
- --today (-T):
  - --league (-l)
  - --details (-D)
  - --odds (-O)
  - --bet (-B)
  - --refresh (-R)
- --matches (-M):
  - --league (-l)
  - --days (-d)
  - --history (-H)
  - --details (-D)
  - --odds (-O)
  - --bet (-B)
- --standings (-S):
  - --league (-l)
- --all-bets (-AB)
- --open-bets (-OB)
- --closed-bets (-CB)
- --profile (-P)
- --possible-leagues (-PL)

## Abbreviations

The abbreviations you can see when using live, today or matches are explained down here:

Abbreviation | Definition | Information
--- | --- | ---
NS | Not Started | The initial status of a game
LIVE | Live | The game is currently in-play
HT | Half-Time | The game currently is in half-time
FT | Full-Time | The game has ended after 90 minutes
ET | Extra-Time | The game currently is in extra time, can happen in knockout games
PEN_LIVE | Penalty Shootout | ET status didn't get a winner, penalties are taken to determine the winner
AET | Finished after extra time | The game has finished after 120 minutes
BREAK | Regular time finished | Waiting for extra time or penalties to start
FT_PEN | Full-Time after penalties | Finished after penalty shootout
CANCL | Cancelled | The game has been cancelled
POSTP | Postponed | The game has been postponed
INT | Interrupted | The game has been interrupted. Can be due to bad weather
ABAN | Abandoned | The game has abandoned and will continue at a later time or day
SUSP | Suspended | The game has suspended and will continue at a later time or day
AWARDED | Awarded | Winner is being decided externally
DELAYED | Delayed | The game is delayed so it will start later
TBA | To Be Announced | Fixture will be updated with exact time later
WO | Walkover | Awarding of a victory to a contestant because there are no other contestants
AU | Awaiting Updates | Can occur when there is a connectivity issue or something

## TODO

- [ ] Add more competitions (divisions under the first divisions)
- [ ] Add option to get matches for a specific team
- [ ] Add support to show cards
- [ ] Add support for live betting
- [x] Update balance at runtime
- [x] Add built-in watch feature so you can run once with --live and just leave the program running.
- [x] Add option to view active/finished bets.
- [x] Add odds to match overviews
- [x] Add color coding for Europa league and Champions League
- [x] Add cups
- [x] Add Champions League and Europa League
- [x] Add detailed information to match results
- [x] Add league filter for live scores
- [x] Add league standings
- [x] Add --details to league standings (details are won, draw, lost, goal for, goal against)
- [x] Add betting functions

## License

Open sourced under [MIT License](LICENSE).

## State

This project is still in development. It works but it may contain bugs. If you find a bug, please open an issue via Github.
