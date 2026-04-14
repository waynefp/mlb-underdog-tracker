"""
Filter raw odds data to qualifying underdog games.
Applies toss-up, extreme favorite, and range filters from config.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


def extract_best_odds(event):
    """
    From a raw Odds API event, extract the best moneyline odds per team
    across all bookmakers.

    Returns dict: {
        "home_team": str,
        "away_team": str,
        "odds": {
            team_name: {"best": int, "avg": float, "best_book": str, "all": {book: odds}},
            ...
        },
        "num_books": int,
    }
    """
    home = event["home_team"]
    away = event["away_team"]
    team_odds = {home: [], away: []}
    team_books = {home: {}, away: {}}

    for bookmaker in event.get("bookmakers", []):
        book_name = bookmaker["key"]
        for market in bookmaker.get("markets", []):
            if market["key"] != "h2h":
                continue
            for outcome in market["outcomes"]:
                name = outcome["name"]
                price = outcome["price"]
                if name in team_odds:
                    team_odds[name].append(price)
                    team_books[name][book_name] = price

    if not team_odds[home] or not team_odds[away]:
        return None

    result = {
        "home_team": home,
        "away_team": away,
        "odds": {},
        "num_books": len(event.get("bookmakers", [])),
    }

    for team in [home, away]:
        prices = team_odds[team]
        best = max(prices)
        best_book = [b for b, p in team_books[team].items() if p == best][0]
        result["odds"][team] = {
            "best": best,
            "avg": round(sum(prices) / len(prices), 1),
            "best_book": best_book,
            "all": team_books[team],
        }

    return result


def identify_favorite_underdog(odds_info):
    """
    Given extracted odds, determine favorite and underdog.
    Returns (favorite_team, underdog_team) or None if can't determine.

    In American odds: more negative = bigger favorite, more positive = bigger underdog.
    """
    home = odds_info["home_team"]
    away = odds_info["away_team"]

    home_best = odds_info["odds"][home]["best"]
    away_best = odds_info["odds"][away]["best"]

    # The team with the lower (more negative) best odds is the favorite
    if home_best < away_best:
        return home, away
    elif away_best < home_best:
        return away, home
    else:
        return None  # True toss-up, identical odds


def is_tossup(odds_info, favorite, underdog):
    """Check if both teams' best odds fall within the toss-up range."""
    fav_odds = odds_info["odds"][favorite]["best"]
    dog_odds = odds_info["odds"][underdog]["best"]
    return (config.TOSSUP_MIN <= fav_odds <= config.TOSSUP_MAX and
            config.TOSSUP_MIN <= dog_odds <= config.TOSSUP_MAX)


def is_extreme_favorite(odds_info, favorite):
    """Check if the favorite's odds are beyond the extreme cutoff."""
    fav_odds = odds_info["odds"][favorite]["best"]
    return fav_odds <= config.EXTREME_FAVORITE_CUTOFF


def is_qualifying_underdog(odds_info, underdog):
    """Check if the underdog's best odds fall within our target range."""
    dog_odds = odds_info["odds"][underdog]["best"]
    return config.UNDERDOG_MIN <= dog_odds <= config.UNDERDOG_MAX


def get_bucket(dog_odds):
    """Assign an odds bucket label based on American odds value."""
    for label, (low, high) in config.BUCKETS.items():
        if low <= dog_odds <= high:
            return label
    return "out_of_range"


def filter_events(events):
    """
    Process a list of raw Odds API events and return qualifying underdog games.

    Returns list of dicts ready for the tracking ledger.
    """
    qualifying = []
    stats = {"total": len(events), "no_odds": 0, "no_sides": 0,
             "tossup": 0, "extreme": 0, "out_of_range": 0, "qualified": 0}

    for event in events:
        odds_info = extract_best_odds(event)
        if not odds_info:
            stats["no_odds"] += 1
            continue

        sides = identify_favorite_underdog(odds_info)
        if not sides:
            stats["no_sides"] += 1
            continue
        favorite, underdog = sides

        if is_tossup(odds_info, favorite, underdog):
            stats["tossup"] += 1
            continue

        if is_extreme_favorite(odds_info, favorite):
            stats["extreme"] += 1
            continue

        if not is_qualifying_underdog(odds_info, underdog):
            stats["out_of_range"] += 1
            continue

        dog_odds = odds_info["odds"][underdog]
        fav_odds = odds_info["odds"][favorite]

        qualifying.append({
            "game_id": event["id"],
            "commence_time": event.get("commence_time", ""),
            "home_team": odds_info["home_team"],
            "away_team": odds_info["away_team"],
            "favorite": favorite,
            "underdog": underdog,
            "dog_odds_best": dog_odds["best"],
            "dog_odds_avg": dog_odds["avg"],
            "dog_best_book": dog_odds["best_book"],
            "fav_odds_best": fav_odds["best"],
            "fav_odds_avg": fav_odds["avg"],
            "home_is_dog": underdog == odds_info["home_team"],
            "bucket": get_bucket(dog_odds["best"]),
            "num_books": odds_info["num_books"],
        })
        stats["qualified"] += 1

    print(f"Filter results: {stats}")
    return qualifying
