"""
Pitcher data utilities — MLB Stats API (free, no key required).
Used by the Streamlit backtest tab and n8n workflow pitcher lookup.
"""

import requests
import pandas as pd
from datetime import datetime

MLB_API = "https://statsapi.mlb.com/api/v1"

# Team name normalization — Odds API names → MLB API names
TEAM_NAME_MAP = {
    "Athletics":            "Athletics",
    "Oakland Athletics":    "Athletics",
    "Arizona Diamondbacks": "D-backs",
    "D-backs":              "D-backs",
    "Chicago White Sox":    "White Sox",
    "Chicago Cubs":         "Cubs",
    "New York Yankees":     "Yankees",
    "New York Mets":        "Mets",
    "Los Angeles Dodgers":  "Dodgers",
    "Los Angeles Angels":   "Angels",
    "San Francisco Giants": "Giants",
    "Tampa Bay Rays":       "Rays",
    "Boston Red Sox":       "Red Sox",
    "Toronto Blue Jays":    "Blue Jays",
    "Kansas City Royals":   "Royals",
    "Minnesota Twins":      "Twins",
    "Cleveland Guardians":  "Guardians",
    "Detroit Tigers":       "Tigers",
    "Milwaukee Brewers":    "Brewers",
    "St. Louis Cardinals":  "Cardinals",
    "Cincinnati Reds":      "Reds",
    "Pittsburgh Pirates":   "Pirates",
    "Philadelphia Phillies":"Phillies",
    "Atlanta Braves":       "Braves",
    "Miami Marlins":        "Marlins",
    "Washington Nationals": "Nationals",
    "Colorado Rockies":     "Rockies",
    "San Diego Padres":     "Padres",
    "Seattle Mariners":     "Mariners",
    "Houston Astros":       "Astros",
    "Texas Rangers":        "Rangers",
    "Baltimore Orioles":    "Orioles",
}


def normalize_team(name):
    """Return a short normalized team name for matching."""
    if not name:
        return ""
    mapped = TEAM_NAME_MAP.get(name)
    if mapped:
        return mapped.lower()
    # Fallback: last word (e.g. "Milwaukee Brewers" → "brewers")
    return name.strip().split()[-1].lower()


def get_season_pitcher_stats(season=None):
    """
    Fetch all qualified pitcher stats for a season.
    Returns a dict: {person_id: {name, whip, era, ip, ...}}
    """
    if season is None:
        season = datetime.now().year

    url = f"{MLB_API}/stats"
    params = {
        "stats": "season",
        "group": "pitching",
        "season": season,
        "sportId": 1,
        "limit": 1000,
        "offset": 0,
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return {}

    splits = data.get("stats", [{}])[0].get("splits", [])
    result = {}
    for s in splits:
        pid  = s.get("player", {}).get("id")
        name = s.get("player", {}).get("fullName", "")
        stat = s.get("stat", {})
        try:
            ip   = float(stat.get("inningsPitched", 0) or 0)
            whip = float(stat.get("whip", 99) or 99)
            era  = float(stat.get("era", 99) or 99)
        except (ValueError, TypeError):
            continue
        if pid:
            result[pid] = {"name": name, "whip": whip, "era": era, "ip": ip}

    return result


def get_top_pitcher_ids(whip_threshold=1.10, min_ip=25, season=None):
    """
    Return a set of MLB person IDs whose WHIP is at or below the threshold.
    Also returns the full stats dict for display purposes.
    """
    stats = get_season_pitcher_stats(season)
    top_ids = set()
    rows = []
    for pid, s in stats.items():
        if s["ip"] >= min_ip and s["whip"] <= whip_threshold:
            top_ids.add(pid)
            rows.append({"Name": s["name"], "WHIP": s["whip"],
                         "ERA": s["era"], "IP": s["ip"]})

    df = pd.DataFrame(rows).sort_values("WHIP") if rows else pd.DataFrame()
    return top_ids, df


def get_games_for_date(date_str):
    """
    Fetch MLB schedule for a date. Returns list of game dicts:
    [{game_pk, home_name, away_name, home_id, away_id}, ...]
    """
    url = f"{MLB_API}/schedule"
    params = {"sportId": 1, "date": date_str, "hydrate": "probablePitcher"}
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []

    games = []
    for date_entry in data.get("dates", []):
        for g in date_entry.get("games", []):
            games.append({
                "game_pk":   g["gamePk"],
                "home_name": g["teams"]["home"]["team"]["name"],
                "away_name": g["teams"]["away"]["team"]["name"],
                "home_id":   g["teams"]["home"]["team"]["id"],
                "away_id":   g["teams"]["away"]["team"]["id"],
                "home_probable_id": (g["teams"]["home"].get("probablePitcher") or {}).get("id"),
                "away_probable_id": (g["teams"]["away"].get("probablePitcher") or {}).get("id"),
            })
    return games


def get_actual_starter_id(game_pk, side):
    """
    Get the actual starting pitcher person ID from a completed game boxscore.
    side: 'home' or 'away'
    Returns person_id or None.
    """
    url = f"{MLB_API}/game/{game_pk}/boxscore"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return None

    pitchers = data.get("teams", {}).get(side, {}).get("pitchers", [])
    if not pitchers:
        return None
    return pitchers[0]  # first pitcher = starter


def match_game(home_team, away_team, mlb_games):
    """
    Match an Odds API game (home_team, away_team) to an MLB schedule game.
    Returns the matched game dict or None.
    """
    home_norm = normalize_team(home_team)
    away_norm = normalize_team(away_team)

    for g in mlb_games:
        mlb_home = normalize_team(g["home_name"])
        mlb_away = normalize_team(g["away_name"])
        if mlb_home == home_norm and mlb_away == away_norm:
            return g
        # Partial match fallback
        if home_norm in mlb_home and away_norm in mlb_away:
            return g
        if mlb_home in home_norm and mlb_away in away_norm:
            return g

    return None


def build_pitcher_flag_lookup(df, whip_threshold=1.10, min_ip=25, season=None):
    """
    For each row in df (tracking data), determine if the favorite's starter
    had a WHIP at or below the threshold.

    Returns df with added columns:
      - fav_starter_name
      - fav_starter_whip
      - fav_starter_ip
      - top_pitcher_flag  (True/False/None if unknown)
    """
    if season is None:
        season = datetime.now().year

    top_ids, _ = get_top_pitcher_ids(whip_threshold, min_ip, season)
    pitcher_stats = get_season_pitcher_stats(season)

    result_rows = []
    date_cache = {}  # date_str → list of mlb games

    for _, row in df.iterrows():
        date_str = row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"])[:10]

        if date_str not in date_cache:
            date_cache[date_str] = get_games_for_date(date_str)
        mlb_games = date_cache[date_str]

        matched = match_game(row.get("home_team", ""), row.get("away_team", ""), mlb_games)

        starter_id   = None
        starter_name = None
        starter_whip = None
        starter_ip   = None
        flag         = None

        if matched:
            # Determine which side the favorite is on
            fav = row.get("favorite", "")
            fav_norm = normalize_team(fav)
            home_norm = normalize_team(matched["home_name"])
            fav_side = "home" if fav_norm == home_norm else "away"

            # Try actual starter first (for completed games), fall back to probable
            starter_id = get_actual_starter_id(matched["game_pk"], fav_side)
            if not starter_id:
                key = "home_probable_id" if fav_side == "home" else "away_probable_id"
                starter_id = matched.get(key)

            if starter_id and starter_id in pitcher_stats:
                ps = pitcher_stats[starter_id]
                starter_name = ps["name"]
                starter_whip = ps["whip"]
                starter_ip   = ps["ip"]
                flag = starter_id in top_ids

        result_rows.append({
            "fav_starter_name": starter_name,
            "fav_starter_whip": starter_whip,
            "fav_starter_ip":   starter_ip,
            "top_pitcher_flag": flag,
        })

    extra = pd.DataFrame(result_rows, index=df.index)
    return pd.concat([df, extra], axis=1)
