"""CLI entry point for odds-cli: parse arguments and dispatch commands."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from odds_cli import __version__
from odds_cli.odds import (
    american_to_decimal,
    american_to_implied_prob,
    kelly_criterion,
    expected_value,
    format_american,
    find_best_line,
    no_vig_probability,
    vig_percentage,
    parlay_odds,
    parlay_implied_prob,
)
from odds_cli.display import (
    render_table,
    render_box,
    render_footer,
    print_banner,
    star_marker,
    bold,
    dim,
    green,
    red,
    yellow,
    cyan,
    white_bold,
    color_odds,
    color_pnl,
)


# ─── Sample Data ───────────────────────────────────────────────────────────────
# Realistic sample data so the CLI works out of the box without an API key.
# When ODDS_API_KEY is set, live data would be fetched instead.

SAMPLE_DATA: dict[str, list[dict[str, Any]]] = {
    "nba": [
        {
            "away": "LAL", "home": "GSW", "time": "7:30 PM",
            "spread": "GSW -4.5", "ml_away": 170, "ml_home": -200, "ou": 228.5,
            "books": {
                "DraftKings": {"ml_away": 170, "ml_home": -200, "spread": "GSW -4.5", "ou": 228.5},
                "FanDuel":    {"ml_away": 165, "ml_home": -195, "spread": "GSW -4.0", "ou": 229.0},
                "BetMGM":     {"ml_away": 175, "ml_home": -210, "spread": "GSW -5.0", "ou": 228.0},
                "Caesars":    {"ml_away": 168, "ml_home": -198, "spread": "GSW -4.5", "ou": 228.5},
            },
        },
        {
            "away": "BOS", "home": "MIL", "time": "8:00 PM",
            "spread": "BOS -2.0", "ml_away": -130, "ml_home": 110, "ou": 221.0,
            "books": {
                "DraftKings": {"ml_away": -130, "ml_home": 110, "spread": "BOS -2.0", "ou": 221.0},
                "FanDuel":    {"ml_away": -125, "ml_home": 105, "spread": "BOS -1.5", "ou": 221.5},
                "BetMGM":     {"ml_away": -135, "ml_home": 115, "spread": "BOS -2.5", "ou": 220.5},
                "Caesars":    {"ml_away": -128, "ml_home": 108, "spread": "BOS -2.0", "ou": 221.0},
            },
        },
        {
            "away": "DEN", "home": "PHX", "time": "9:30 PM",
            "spread": "DEN -1.5", "ml_away": -120, "ml_home": 100, "ou": 232.0,
            "books": {
                "DraftKings": {"ml_away": -120, "ml_home": 100, "spread": "DEN -1.5", "ou": 232.0},
                "FanDuel":    {"ml_away": -118, "ml_home": -102, "spread": "DEN -1.5", "ou": 232.5},
                "BetMGM":     {"ml_away": -125, "ml_home": 105, "spread": "DEN -2.0", "ou": 231.5},
                "Caesars":    {"ml_away": -122, "ml_home": 102, "spread": "DEN -1.5", "ou": 232.0},
            },
        },
        {
            "away": "DAL", "home": "MIN", "time": "8:00 PM",
            "spread": "MIN -3.0", "ml_away": 140, "ml_home": -165, "ou": 219.5,
            "books": {
                "DraftKings": {"ml_away": 140, "ml_home": -165, "spread": "MIN -3.0", "ou": 219.5},
                "FanDuel":    {"ml_away": 138, "ml_home": -162, "spread": "MIN -3.0", "ou": 220.0},
                "BetMGM":     {"ml_away": 145, "ml_home": -170, "spread": "MIN -3.5", "ou": 219.0},
                "Caesars":    {"ml_away": 142, "ml_home": -168, "spread": "MIN -3.0", "ou": 219.5},
            },
        },
        {
            "away": "MIA", "home": "NYK", "time": "7:00 PM",
            "spread": "NYK -6.5", "ml_away": 240, "ml_home": -290, "ou": 210.0,
            "books": {
                "DraftKings": {"ml_away": 240, "ml_home": -290, "spread": "NYK -6.5", "ou": 210.0},
                "FanDuel":    {"ml_away": 235, "ml_home": -280, "spread": "NYK -6.0", "ou": 210.5},
                "BetMGM":     {"ml_away": 245, "ml_home": -300, "spread": "NYK -7.0", "ou": 209.5},
                "Caesars":    {"ml_away": 238, "ml_home": -285, "spread": "NYK -6.5", "ou": 210.0},
            },
        },
    ],
    "nfl": [
        {
            "away": "KC", "home": "BUF", "time": "1:00 PM",
            "spread": "BUF -3.0", "ml_away": 145, "ml_home": -170, "ou": 48.5,
            "books": {
                "DraftKings": {"ml_away": 145, "ml_home": -170, "spread": "BUF -3.0", "ou": 48.5},
                "FanDuel":    {"ml_away": 150, "ml_home": -175, "spread": "BUF -3.0", "ou": 49.0},
                "BetMGM":     {"ml_away": 140, "ml_home": -165, "spread": "BUF -2.5", "ou": 48.0},
                "Caesars":    {"ml_away": 148, "ml_home": -172, "spread": "BUF -3.0", "ou": 48.5},
            },
        },
        {
            "away": "PHI", "home": "DAL", "time": "4:25 PM",
            "spread": "PHI -5.5", "ml_away": -220, "ml_home": 185, "ou": 45.0,
            "books": {
                "DraftKings": {"ml_away": -220, "ml_home": 185, "spread": "PHI -5.5", "ou": 45.0},
                "FanDuel":    {"ml_away": -215, "ml_home": 180, "spread": "PHI -5.0", "ou": 45.5},
                "BetMGM":     {"ml_away": -225, "ml_home": 190, "spread": "PHI -6.0", "ou": 44.5},
                "Caesars":    {"ml_away": -218, "ml_home": 182, "spread": "PHI -5.5", "ou": 45.0},
            },
        },
        {
            "away": "SF", "home": "SEA", "time": "4:25 PM",
            "spread": "SF -1.5", "ml_away": -115, "ml_home": -105, "ou": 43.5,
            "books": {
                "DraftKings": {"ml_away": -115, "ml_home": -105, "spread": "SF -1.5", "ou": 43.5},
                "FanDuel":    {"ml_away": -112, "ml_home": -108, "spread": "SF -1.0", "ou": 44.0},
                "BetMGM":     {"ml_away": -118, "ml_home": -102, "spread": "SF -2.0", "ou": 43.0},
                "Caesars":    {"ml_away": -114, "ml_home": -106, "spread": "SF -1.5", "ou": 43.5},
            },
        },
    ],
    "mlb": [
        {
            "away": "NYY", "home": "BOS", "time": "7:10 PM",
            "spread": "BOS -1.5", "ml_away": 125, "ml_home": -145, "ou": 9.0,
            "books": {
                "DraftKings": {"ml_away": 125, "ml_home": -145, "spread": "BOS -1.5", "ou": 9.0},
                "FanDuel":    {"ml_away": 128, "ml_home": -148, "spread": "BOS -1.5", "ou": 9.0},
                "BetMGM":     {"ml_away": 122, "ml_home": -142, "spread": "BOS -1.5", "ou": 8.5},
                "Caesars":    {"ml_away": 126, "ml_home": -146, "spread": "BOS -1.5", "ou": 9.0},
            },
        },
        {
            "away": "LAD", "home": "SF", "time": "10:15 PM",
            "spread": "LAD -1.5", "ml_away": -175, "ml_home": 155, "ou": 8.5,
            "books": {
                "DraftKings": {"ml_away": -175, "ml_home": 155, "spread": "LAD -1.5", "ou": 8.5},
                "FanDuel":    {"ml_away": -170, "ml_home": 150, "spread": "LAD -1.5", "ou": 8.5},
                "BetMGM":     {"ml_away": -180, "ml_home": 160, "spread": "LAD -1.5", "ou": 8.0},
                "Caesars":    {"ml_away": -172, "ml_home": 152, "spread": "LAD -1.5", "ou": 8.5},
            },
        },
    ],
    "nhl": [
        {
            "away": "EDM", "home": "TOR", "time": "7:00 PM",
            "spread": "TOR -1.5", "ml_away": 130, "ml_home": -155, "ou": 6.5,
            "books": {
                "DraftKings": {"ml_away": 130, "ml_home": -155, "spread": "TOR -1.5", "ou": 6.5},
                "FanDuel":    {"ml_away": 135, "ml_home": -160, "spread": "TOR -1.5", "ou": 6.5},
                "BetMGM":     {"ml_away": 128, "ml_home": -152, "spread": "TOR -1.5", "ou": 6.0},
                "Caesars":    {"ml_away": 132, "ml_home": -158, "spread": "TOR -1.5", "ou": 6.5},
            },
        },
        {
            "away": "COL", "home": "VGK", "time": "10:00 PM",
            "spread": "VGK -1.5", "ml_away": 115, "ml_home": -135, "ou": 6.0,
            "books": {
                "DraftKings": {"ml_away": 115, "ml_home": -135, "spread": "VGK -1.5", "ou": 6.0},
                "FanDuel":    {"ml_away": 118, "ml_home": -138, "spread": "VGK -1.5", "ou": 6.0},
                "BetMGM":     {"ml_away": 112, "ml_home": -132, "spread": "VGK -1.5", "ou": 5.5},
                "Caesars":    {"ml_away": 116, "ml_home": -136, "spread": "VGK -1.5", "ou": 6.0},
            },
        },
    ],
}

SAMPLE_HISTORY = [
    {"date": "2026-01-10", "sport": "nba", "matchup": "LAL vs GSW", "side": "LAL", "odds": 170, "stake": 100, "result": "win"},
    {"date": "2026-01-10", "sport": "nba", "matchup": "BOS vs MIL", "side": "BOS", "odds": -130, "stake": 130, "result": "win"},
    {"date": "2026-01-11", "sport": "nfl", "matchup": "KC vs BUF", "side": "KC", "odds": 145, "stake": 100, "result": "loss"},
    {"date": "2026-01-12", "sport": "nba", "matchup": "DEN vs PHX", "side": "DEN", "odds": -120, "stake": 120, "result": "win"},
    {"date": "2026-01-13", "sport": "nba", "matchup": "DAL vs MIN", "side": "DAL", "odds": 140, "stake": 100, "result": "loss"},
    {"date": "2026-01-14", "sport": "nfl", "matchup": "PHI vs DAL", "side": "PHI", "odds": -220, "stake": 220, "result": "win"},
    {"date": "2026-01-15", "sport": "nba", "matchup": "MIA vs NYK", "side": "NYK", "odds": -290, "stake": 290, "result": "win"},
    {"date": "2026-01-15", "sport": "nba", "matchup": "LAL vs GSW", "side": "GSW", "odds": -200, "stake": 200, "result": "win"},
    {"date": "2026-01-16", "sport": "nba", "matchup": "BOS vs MIL", "side": "MIL", "odds": 110, "stake": 100, "result": "loss"},
    {"date": "2026-01-17", "sport": "nba", "matchup": "DEN vs PHX", "side": "PHX", "odds": 100, "stake": 100, "result": "loss"},
    {"date": "2026-01-18", "sport": "nfl", "matchup": "SF vs SEA", "side": "SF", "odds": -115, "stake": 115, "result": "win"},
    {"date": "2026-01-19", "sport": "nba", "matchup": "LAL vs GSW", "side": "LAL", "odds": 175, "stake": 100, "result": "win"},
    {"date": "2026-01-20", "sport": "nba", "matchup": "DAL vs MIN", "side": "MIN", "odds": -165, "stake": 165, "result": "win"},
    {"date": "2026-01-21", "sport": "nba", "matchup": "MIA vs NYK", "side": "MIA", "odds": 240, "stake": 100, "result": "loss"},
    {"date": "2026-01-22", "sport": "nba", "matchup": "BOS vs MIL", "side": "BOS", "odds": -125, "stake": 125, "result": "win"},
    {"date": "2026-01-23", "sport": "nfl", "matchup": "KC vs BUF", "side": "BUF", "odds": -170, "stake": 170, "result": "win"},
    {"date": "2026-01-24", "sport": "nba", "matchup": "DEN vs PHX", "side": "DEN", "odds": -118, "stake": 118, "result": "loss"},
    {"date": "2026-01-25", "sport": "nba", "matchup": "LAL vs GSW", "side": "GSW", "odds": -195, "stake": 195, "result": "win"},
    {"date": "2026-02-01", "sport": "nba", "matchup": "DAL vs MIN", "side": "DAL", "odds": 138, "stake": 100, "result": "win"},
    {"date": "2026-02-02", "sport": "nba", "matchup": "MIA vs NYK", "side": "NYK", "odds": -280, "stake": 280, "result": "loss"},
    {"date": "2026-02-03", "sport": "nba", "matchup": "BOS vs MIL", "side": "BOS", "odds": -130, "stake": 130, "result": "win"},
    {"date": "2026-02-04", "sport": "nfl", "matchup": "PHI vs DAL", "side": "PHI", "odds": -215, "stake": 215, "result": "win"},
    {"date": "2026-02-05", "sport": "nba", "matchup": "DEN vs PHX", "side": "PHX", "odds": 105, "stake": 100, "result": "win"},
    {"date": "2026-02-06", "sport": "nba", "matchup": "LAL vs GSW", "side": "LAL", "odds": 165, "stake": 100, "result": "loss"},
    {"date": "2026-02-07", "sport": "nba", "matchup": "DAL vs MIN", "side": "MIN", "odds": -162, "stake": 162, "result": "win"},
    {"date": "2026-02-08", "sport": "nba", "matchup": "MIA vs NYK", "side": "NYK", "odds": -285, "stake": 285, "result": "win"},
]


# ─── Config Helpers ────────────────────────────────────────────────────────────

CONFIG_DIR = Path.home() / ".config" / "odds-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "history.csv"


def get_api_key() -> Optional[str]:
    """Get API key from environment or config file."""
    key = os.environ.get("ODDS_API_KEY")
    if key:
        return key
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                config = json.load(f)
            return config.get("api_key")
        except (json.JSONDecodeError, KeyError):
            pass
    return None


def get_games(sport: str) -> list[dict[str, Any]]:
    """Get games for a sport. Uses sample data if no API key is configured."""
    api_key = get_api_key()
    if api_key:
        return _fetch_live_data(sport, api_key)

    sport_lower = sport.lower()
    if sport_lower not in SAMPLE_DATA:
        print(f"\n  {red('Error:')} Unknown sport '{sport}'.")
        print(f"  Supported: {', '.join(SAMPLE_DATA.keys())}\n")
        sys.exit(1)

    return SAMPLE_DATA[sport_lower]


def _fetch_live_data(sport: str, api_key: str) -> list[dict[str, Any]]:
    """Fetch live odds from The Odds API.

    This function requires the 'requests' library and a valid API key.
    """
    try:
        import requests
    except ImportError:
        print(f"\n  {red('Error:')} 'requests' library required for live data.")
        print(f"  Install with: pip install requests\n")
        sys.exit(1)

    sport_keys = {
        "nba": "basketball_nba",
        "nfl": "americanfootball_nfl",
        "mlb": "baseball_mlb",
        "nhl": "icehockey_nhl",
    }

    sport_lower = sport.lower()
    if sport_lower not in sport_keys:
        print(f"\n  {red('Error:')} Unknown sport '{sport}'.")
        print(f"  Supported: {', '.join(sport_keys.keys())}\n")
        sys.exit(1)

    url = "https://api.the-odds-api.com/v4/sports/{}/odds".format(sport_keys[sport_lower])
    params = {
        "apiKey": api_key,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"\n  {red('Error:')} Failed to fetch live data: {e}")
        print(f"  Falling back to sample data.\n")
        return SAMPLE_DATA.get(sport_lower, [])

    # Parse API response into our internal format
    games = []
    for event in data:
        game: dict[str, Any] = {
            "away": _abbreviate(event.get("away_team", "")),
            "home": _abbreviate(event.get("home_team", "")),
            "time": _format_commence(event.get("commence_time", "")),
            "books": {},
        }

        for bookmaker in event.get("bookmakers", []):
            book_name = bookmaker.get("title", "Unknown")
            book_data: dict[str, Any] = {}

            for market in bookmaker.get("markets", []):
                market_key = market.get("key")
                outcomes = market.get("outcomes", [])

                if market_key == "h2h":
                    for outcome in outcomes:
                        price = outcome.get("price", 0)
                        if outcome.get("name") == event.get("away_team"):
                            book_data["ml_away"] = price
                        else:
                            book_data["ml_home"] = price

                elif market_key == "spreads":
                    for outcome in outcomes:
                        point = outcome.get("point", 0)
                        if outcome.get("name") == event.get("home_team"):
                            fav = game["home"] if point < 0 else game["away"]
                            book_data["spread"] = f"{fav} {point}"
                            break

                elif market_key == "totals":
                    for outcome in outcomes:
                        if outcome.get("name") == "Over":
                            book_data["ou"] = outcome.get("point", 0)
                            break

            if book_data:
                game["books"][book_name] = book_data

        # Set primary line from first bookmaker
        if game["books"]:
            first_book = next(iter(game["books"].values()))
            game["ml_away"] = first_book.get("ml_away", 0)
            game["ml_home"] = first_book.get("ml_home", 0)
            game["spread"] = first_book.get("spread", "")
            game["ou"] = first_book.get("ou", 0)

        games.append(game)

    return games


def _abbreviate(team_name: str) -> str:
    """Create a 3-letter abbreviation from a team name."""
    abbreviations = {
        "Los Angeles Lakers": "LAL", "Golden State Warriors": "GSW",
        "Boston Celtics": "BOS", "Milwaukee Bucks": "MIL",
        "Denver Nuggets": "DEN", "Phoenix Suns": "PHX",
        "Dallas Mavericks": "DAL", "Minnesota Timberwolves": "MIN",
        "Miami Heat": "MIA", "New York Knicks": "NYK",
        "Kansas City Chiefs": "KC", "Buffalo Bills": "BUF",
        "Philadelphia Eagles": "PHI", "San Francisco 49ers": "SF",
        "Seattle Seahawks": "SEA",
        "New York Yankees": "NYY", "Boston Red Sox": "BOS",
        "Los Angeles Dodgers": "LAD",
        "Edmonton Oilers": "EDM", "Toronto Maple Leafs": "TOR",
        "Colorado Avalanche": "COL", "Vegas Golden Knights": "VGK",
    }
    return abbreviations.get(team_name, team_name[:3].upper())


def _format_commence(iso_time: str) -> str:
    """Format an ISO datetime string into a friendly time."""
    try:
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        return dt.strftime("%-I:%M %p")
    except (ValueError, AttributeError):
        return "TBD"


def load_history() -> list[dict[str, Any]]:
    """Load bet history from CSV file or return sample data."""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, newline="") as f:
                reader = csv.DictReader(f)
                history = []
                for row in reader:
                    row["odds"] = int(row["odds"])
                    row["stake"] = float(row["stake"])
                    history.append(row)
                return history
        except (csv.Error, KeyError, ValueError):
            pass

    return SAMPLE_HISTORY


# ─── Command Handlers ──────────────────────────────────────────────────────────

def cmd_slate(sport: str, args: argparse.Namespace) -> None:
    """Display tonight's slate for a sport."""
    games = get_games(sport)
    if not games:
        print(f"\n  {dim('No games found for')} {sport.upper()}\n")
        return

    headers = ["Matchup", "Time", "Spread", "ML Away", "ML Home", "O/U"]
    rows = []

    for g in games:
        matchup = f"{g['away']} @ {g['home']}"
        ml_away = color_odds(format_american(g["ml_away"]))
        ml_home = color_odds(format_american(g["ml_home"]))
        rows.append([
            bold(matchup),
            dim(g["time"]),
            yellow(g["spread"]),
            ml_away,
            ml_home,
            cyan(str(g["ou"])),
        ])

    title = f"{sport.upper()} ODDS \u2014 Tonight's Slate"
    alignments = ["left", "left", "left", "right", "right", "right"]

    print()
    print(render_table(title, headers, rows, alignments))

    api_key = get_api_key()
    source = "The Odds API" if api_key else "Sample Data"
    now = datetime.now().strftime("%-I:%M %p ET")
    footer_parts = [f"{len(games)} game{'s' if len(games) != 1 else ''}", f"Lines via {source}", f"Updated {now}"]
    print(render_footer(footer_parts))


def cmd_best_line(sport: str, args: argparse.Namespace) -> None:
    """Display best available lines across sportsbooks."""
    games = get_games(sport)
    if not games:
        print(f"\n  {dim('No games found for')} {sport.upper()}\n")
        return

    # Collect all book names
    all_books: list[str] = []
    for g in games:
        for book_name in g.get("books", {}):
            if book_name not in all_books:
                all_books.append(book_name)

    if not all_books:
        print(f"\n  {dim('No multi-book data available.')}\n")
        return

    headers = ["Matchup"] + all_books + ["Best"]
    rows = []

    for g in games:
        matchup = f"{g['away']} @ {g['home']}"
        books = g.get("books", {})

        # Away ML row
        away_odds_by_book = {}
        away_cells = [bold(matchup) + dim(f"  ({g['away']})")]
        for book in all_books:
            if book in books and "ml_away" in books[book]:
                odds_val = books[book]["ml_away"]
                away_odds_by_book[book] = odds_val
                away_cells.append(color_odds(format_american(odds_val)))
            else:
                away_cells.append(dim("--"))

        if away_odds_by_book:
            best_book, best_odds = find_best_line(away_odds_by_book)
            away_cells.append(color_odds(format_american(best_odds)) + " " + star_marker())
        else:
            away_cells.append(dim("--"))
        rows.append(away_cells)

        # Home ML row
        home_odds_by_book = {}
        home_cells = [dim(f"  {' ' * len(matchup)}") + dim(f"  ({g['home']})")]
        for book in all_books:
            if book in books and "ml_home" in books[book]:
                odds_val = books[book]["ml_home"]
                home_odds_by_book[book] = odds_val
                home_cells.append(color_odds(format_american(odds_val)))
            else:
                home_cells.append(dim("--"))

        if home_odds_by_book:
            # For the home side (usually the favorite), best line = highest odds (least negative)
            best_book, best_odds = find_best_line(home_odds_by_book)
            home_cells.append(color_odds(format_american(best_odds)) + " " + star_marker())
        else:
            home_cells.append(dim("--"))
        rows.append(home_cells)

    title = f"{sport.upper()} BEST LINES \u2014 Across Books"
    alignments = ["left"] + ["right"] * (len(all_books) + 1)

    print()
    print(render_table(title, headers, rows, alignments))
    print(render_footer([f"{len(games)} games", f"{len(all_books)} books compared", f"{star_marker()} = best available"]))


def cmd_kelly(sport: str, prob: float, args: argparse.Namespace) -> None:
    """Display Kelly criterion sizing for each game."""
    if prob <= 0 or prob >= 1:
        print(f"\n  {red('Error:')} Probability must be between 0 and 1 (exclusive).\n")
        sys.exit(1)

    games = get_games(sport)
    if not games:
        print(f"\n  {dim('No games found for')} {sport.upper()}\n")
        return

    headers = ["Matchup", "Side", "Odds", "Implied", "Your Prob", "Edge", "Kelly %", "EV/$100"]
    rows = []

    for g in games:
        matchup = f"{g['away']} @ {g['home']}"

        # Calculate for both sides
        for side, odds_key, team in [("away", "ml_away", g["away"]), ("home", "ml_home", g["home"])]:
            odds = g[odds_key]
            implied = american_to_implied_prob(odds)
            edge = prob - implied
            kf = kelly_criterion(prob, odds)
            ev = expected_value(prob, odds, 100.0)

            # Colorize based on edge
            edge_str = f"{edge*100:+.1f}%"
            kelly_str = f"{kf*100:.1f}%"
            ev_str = f"${ev:+.2f}"

            if edge > 0:
                edge_str = green(edge_str)
                kelly_str = green(kelly_str)
                ev_str = green(ev_str)
            else:
                edge_str = red(edge_str)
                kelly_str = red(kelly_str) if kf > 0 else dim("0.0%")
                ev_str = red(ev_str)

            rows.append([
                bold(matchup) if side == "away" else "",
                cyan(team),
                color_odds(format_american(odds)),
                dim(f"{implied*100:.1f}%"),
                yellow(f"{prob*100:.1f}%"),
                edge_str,
                kelly_str,
                ev_str,
            ])

    title = f"{sport.upper()} KELLY SIZING \u2014 Your Prob: {prob*100:.0f}%"
    alignments = ["left", "left", "right", "right", "right", "right", "right", "right"]

    print()
    print(render_table(title, headers, rows, alignments))
    print(render_footer([
        f"Assessed probability: {prob*100:.1f}%",
        "Kelly = (bp - q) / b",
        "Positive Kelly = edge exists",
    ]))


def cmd_compare(matchup_query: str, args: argparse.Namespace) -> None:
    """Compare a specific matchup across all sportsbooks."""
    query = matchup_query.lower().replace(" vs ", " ").replace(" @ ", " ").replace("vs.", " ")
    query_parts = query.split()

    # Search all sports for matching game
    found_game: Optional[dict[str, Any]] = None
    for sport, games in SAMPLE_DATA.items():
        for game in games:
            away_lower = game["away"].lower()
            home_lower = game["home"].lower()
            if any(part in away_lower or part in home_lower for part in query_parts):
                found_game = game
                break
        if found_game:
            break

    if not found_game:
        print(f"\n  {red('Error:')} No matching game found for '{matchup_query}'.")
        print(f"  {dim('Try a team abbreviation like:')} odds compare \"LAL vs GSW\"\n")
        sys.exit(1)

    g = found_game
    books = g.get("books", {})
    if not books:
        print(f"\n  {dim('No multi-book data available for this matchup.')}\n")
        return

    matchup_str = f"{g['away']} vs {g['home']}"
    headers = ["Sportsbook", f"ML {g['away']}", f"ML {g['home']}", "Spread", "O/U"]
    rows = []

    for book_name, book_data in books.items():
        ml_away = color_odds(format_american(book_data.get("ml_away", 0)))
        ml_home = color_odds(format_american(book_data.get("ml_home", 0)))
        spread = yellow(book_data.get("spread", "--"))
        ou = cyan(f"O/U {book_data.get('ou', '--')}")
        rows.append([bold(book_name), ml_away, ml_home, spread, ou])

    # Add no-vig row
    all_away = [b["ml_away"] for b in books.values() if "ml_away" in b]
    all_home = [b["ml_home"] for b in books.values() if "ml_home" in b]
    if all_away and all_home:
        avg_away = round(sum(all_away) / len(all_away))
        avg_home = round(sum(all_home) / len(all_home))
        nv_a, nv_h = no_vig_probability(avg_away, avg_home)
        vig = vig_percentage(avg_away, avg_home)
        rows.append([
            dim("No-Vig True%"),
            dim(f"{nv_a*100:.1f}%"),
            dim(f"{nv_h*100:.1f}%"),
            dim(f"Vig: {vig:.1f}%"),
            "",
        ])

    title = f"{matchup_str} \u2014 Book Comparison"
    alignments = ["left", "right", "right", "left", "left"]

    print()
    print(render_table(title, headers, rows, alignments))
    print(render_footer([f"{len(books)} books", f"Game time: {g['time']}"]))


def cmd_convert(american_str: str, args: argparse.Namespace) -> None:
    """Convert odds between formats."""
    try:
        american = int(american_str)
    except ValueError:
        print(f"\n  {red('Error:')} Invalid odds value '{american_str}'. Use an integer like -150 or +200.\n")
        sys.exit(1)

    if american == 0:
        print(f"\n  {red('Error:')} American odds cannot be zero.\n")
        sys.exit(1)

    decimal_odds = american_to_decimal(american)
    implied = american_to_implied_prob(american)

    content = [
        f"{bold('American:')}    {color_odds(format_american(american))}",
        f"{bold('Decimal:')}     {cyan(f'{decimal_odds:.3f}')}",
        f"{bold('Implied:')}     {yellow(f'{implied*100:.1f}%')}",
        f"{bold('Fractional:')}  {dim(_to_fractional(decimal_odds))}",
        "",
        f"{bold('$100 stake:')}  Win {green(f'${100 * (decimal_odds - 1):.2f}')} / Return {cyan(f'${100 * decimal_odds:.2f}')}",
    ]

    print()
    print(render_box("Odds Conversion", content))
    print()


def _to_fractional(decimal_odds: float) -> str:
    """Convert decimal odds to fractional representation."""
    from fractions import Fraction
    frac = Fraction(decimal_odds - 1).limit_denominator(100)
    return f"{frac.numerator}/{frac.denominator}"


def cmd_bankroll(args: argparse.Namespace) -> None:
    """Display bankroll summary statistics."""
    history = load_history()

    if not history:
        print(f"\n  {dim('No betting history found.')}")
        print(f"  {dim('Add bets to')} {HISTORY_FILE}\n")
        return

    wins = [h for h in history if h["result"] == "win"]
    losses = [h for h in history if h["result"] == "loss"]
    total = len(history)
    win_count = len(wins)
    loss_count = len(losses)
    win_pct = (win_count / total * 100) if total > 0 else 0

    # Calculate P&L
    total_pnl = 0.0
    total_staked = 0.0
    daily_pnl: dict[str, float] = {}
    all_odds: list[int] = []

    for bet in history:
        stake = bet["stake"]
        odds = bet["odds"]
        total_staked += stake
        all_odds.append(odds)

        if bet["result"] == "win":
            profit = stake * (american_to_decimal(odds) - 1)
            total_pnl += profit
        else:
            total_pnl -= stake

        date = bet["date"]
        if date not in daily_pnl:
            daily_pnl[date] = 0.0
        if bet["result"] == "win":
            daily_pnl[date] += stake * (american_to_decimal(odds) - 1)
        else:
            daily_pnl[date] -= stake

    roi = (total_pnl / total_staked * 100) if total_staked > 0 else 0
    avg_odds = round(sum(all_odds) / len(all_odds)) if all_odds else 0

    # Best/worst day
    best_day = max(daily_pnl.items(), key=lambda x: x[1]) if daily_pnl else ("--", 0)
    worst_day = min(daily_pnl.items(), key=lambda x: x[1]) if daily_pnl else ("--", 0)

    # Current streak
    streak_type = ""
    streak_count = 0
    for bet in reversed(history):
        if streak_count == 0:
            streak_type = bet["result"]
            streak_count = 1
        elif bet["result"] == streak_type:
            streak_count += 1
        else:
            break
    streak_str = f"{'W' if streak_type == 'win' else 'L'}{streak_count}"

    # Format best/worst day dates
    def _fmt_date(d: str) -> str:
        try:
            dt = datetime.strptime(d, "%Y-%m-%d")
            return dt.strftime("%b %d")
        except ValueError:
            return d

    content = [
        f"{bold('Record:')}       {white_bold(f'{win_count}-{loss_count}')} ({yellow(f'{win_pct:.1f}%')})",
        f"{bold('Net P&L:')}      {color_pnl(total_pnl)}",
        f"{bold('ROI:')}          {green(f'{roi:.1f}%') if roi > 0 else red(f'{roi:.1f}%')}",
        f"{bold('Total Staked:')} {dim(f'${total_staked:,.2f}')}",
        f"{bold('Avg Odds:')}     {color_odds(format_american(avg_odds))}",
        f"{bold('Best Day:')}     {green(f'+${best_day[1]:,.2f}')} {dim(f'({_fmt_date(best_day[0])})')}",
        f"{bold('Worst Day:')}    {red(f'-${abs(worst_day[1]):,.2f}')} {dim(f'({_fmt_date(worst_day[0])})')}",
        f"{bold('Current Run:')}  {green(streak_str) if streak_type == 'win' else red(streak_str)}",
    ]

    print()
    print(render_box("Bankroll Summary", content))

    # Recent bets table
    recent = history[-8:]
    headers = ["Date", "Matchup", "Side", "Odds", "Stake", "Result", "P&L"]
    rows = []
    for bet in reversed(recent):
        odds = bet["odds"]
        stake = bet["stake"]
        if bet["result"] == "win":
            pnl = stake * (american_to_decimal(odds) - 1)
            result_str = green("W")
            pnl_str = green(f"+${pnl:.2f}")
        else:
            pnl = -stake
            result_str = red("L")
            pnl_str = red(f"-${stake:.2f}")

        rows.append([
            dim(bet["date"]),
            bold(bet["matchup"]),
            cyan(bet["side"]),
            color_odds(format_american(odds)),
            dim(f"${stake:.0f}"),
            result_str,
            pnl_str,
        ])

    print()
    print(render_table("Recent Bets", headers, rows, ["left", "left", "left", "right", "right", "center", "right"]))
    print(render_footer([f"{total} total bets", f"Tracking since {history[0]['date']}"]))


def cmd_parlay(legs_str: list[str], args: argparse.Namespace) -> None:
    """Analyze a multi-leg parlay: combined odds, implied probability, and payout."""
    legs: list[int] = []
    for raw in legs_str:
        try:
            val = int(raw)
            if val == 0:
                raise ValueError
            legs.append(val)
        except ValueError:
            print(f"\n  {red('Error:')} Invalid odds '{raw}'. Use integers like -150 or +200.\n")
            sys.exit(1)

    if len(legs) < 2:
        print(f"\n  {red('Error:')} A parlay requires at least 2 legs.\n")
        sys.exit(1)

    combined_american = parlay_odds(legs)
    combined_prob = parlay_implied_prob(legs)
    combined_decimal = american_to_decimal(combined_american)

    # Per-leg breakdown table
    headers = ["Leg", "Odds", "Implied %", "Decimal", "No-Vig %"]
    rows: list[list[str]] = []
    running_true_prob = 1.0

    for i, american in enumerate(legs, 1):
        implied = american_to_implied_prob(american)
        decimal = american_to_decimal(american)
        # Rough no-vig for a single line (treat as 50/50 market against its mirror)
        # We show raw implied here; true prob is just the implied without vig context for single legs
        rows.append([
            bold(f"Leg {i}"),
            color_odds(format_american(american)),
            yellow(f"{implied * 100:.1f}%"),
            cyan(f"{decimal:.3f}"),
            dim(f"{implied * 100:.1f}%"),
        ])
        running_true_prob *= implied

    # Separator + combined row
    rows.append([dim("─" * 5), dim("─" * 6), dim("─" * 9), dim("─" * 7), dim("─" * 8)])
    rows.append([
        white_bold(f"{len(legs)}-Leg Parlay"),
        color_odds(format_american(combined_american)),
        yellow(f"{combined_prob * 100:.2f}%"),
        cyan(f"{combined_decimal:.3f}"),
        dim(f"{running_true_prob * 100:.2f}%"),
    ])

    title = f"{len(legs)}-LEG PARLAY — Combined Analysis"
    alignments = ["left", "right", "right", "right", "right"]

    print()
    print(render_table(title, headers, rows, alignments))

    # Payout summary box
    stake = 100.0
    payout = stake * combined_decimal
    profit = payout - stake
    break_even = (1.0 / combined_decimal) * 100

    content = [
        f"{bold('Legs:')}            {white_bold(str(len(legs)))}",
        f"{bold('Combined Odds:')}   {color_odds(format_american(combined_american))}",
        f"{bold('Hit Probability:')} {yellow(f'{combined_prob * 100:.2f}%')}",
        f"{bold('Break-even Prob:')} {dim(f'{break_even:.2f}%')}",
        "",
        f"{bold('$100 stake:')} win {green(f'${profit:,.2f}')} / return {cyan(f'${payout:,.2f}')}",
    ]
    print()
    print(render_box("Parlay Payout", content))
    print(render_footer([
        f"{len(legs)} legs",
        f"Hit prob: {combined_prob * 100:.2f}%",
        "Tip: parlays carry higher vig than singles",
    ]))


# ─── Argument Parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for odds-cli."""
    parser = argparse.ArgumentParser(
        prog="odds",
        description="Check live sports odds from your terminal.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  odds nba                         Show tonight's NBA slate
  odds nfl --best-line             Compare NFL lines across books
  odds nba --kelly 0.58            Kelly sizing at 58%% win prob
  odds compare "LAL vs GSW"        Compare one matchup across books
  odds convert -150                Convert odds formats
  odds bankroll                    Show bankroll summary
  odds parlay -150 +130 -110       Analyze a 3-leg parlay""",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # --- Sport command (nba, nfl, mlb, nhl) ---
    for sport in ["nba", "nfl", "mlb", "nhl"]:
        sport_parser = subparsers.add_parser(sport, help=f"Show {sport.upper()} odds")
        sport_parser.add_argument(
            "--best-line",
            action="store_true",
            help="Compare lines across sportsbooks",
        )
        sport_parser.add_argument(
            "--kelly",
            type=float,
            metavar="PROB",
            help="Calculate Kelly sizing at given probability (0-1)",
        )

    # --- Compare command ---
    compare_parser = subparsers.add_parser("compare", help="Compare a matchup across books")
    compare_parser.add_argument(
        "matchup",
        help='Matchup to compare (e.g., "LAL vs GSW")',
    )

    # --- Convert command ---
    convert_parser = subparsers.add_parser("convert", help="Convert odds formats")
    convert_parser.add_argument(
        "odds_value",
        help="American odds to convert (e.g., -150, +200)",
    )

    # --- Bankroll command ---
    subparsers.add_parser("bankroll", help="Show bankroll summary")

    # --- Parlay command ---
    parlay_parser = subparsers.add_parser(
        "parlay",
        help="Analyze a multi-leg parlay",
        description="Calculate combined odds, hit probability, and payout for a parlay.",
    )
    parlay_parser.add_argument(
        "legs",
        nargs="+",
        metavar="ODDS",
        help="American odds for each leg (e.g., -150 +130 -110)",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> None:
    """Main entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        print(print_banner())
        parser.print_help()
        return

    sport_commands = {"nba", "nfl", "mlb", "nhl"}

    if args.command in sport_commands:
        if args.kelly is not None:
            cmd_kelly(args.command, args.kelly, args)
        elif args.best_line:
            cmd_best_line(args.command, args)
        else:
            cmd_slate(args.command, args)

    elif args.command == "compare":
        cmd_compare(args.matchup, args)

    elif args.command == "convert":
        cmd_convert(args.odds_value, args)

    elif args.command == "bankroll":
        cmd_bankroll(args)

    elif args.command == "parlay":
        cmd_parlay(args.legs, args)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
