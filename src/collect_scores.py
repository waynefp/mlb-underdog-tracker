"""
Pull completed MLB game scores from The Odds API.
Usage: python -m src.collect_scores [--days-ago N]
"""

import argparse
import json
import os
import sys
from datetime import date, timedelta

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


def fetch_scores(days_ago=1):
    """Fetch completed MLB scores. days_ago=1 gets yesterday's results."""
    url = f"{config.ODDS_API_BASE}/sports/{config.SPORT}/scores"
    params = {
        "apiKey": config.ODDS_API_KEY,
        "daysFrom": days_ago,
    }

    resp = requests.get(url, params=params)
    resp.raise_for_status()

    remaining = resp.headers.get("x-requests-remaining", "?")
    used = resp.headers.get("x-requests-used", "?")
    print(f"API credits — used: {used}, remaining: {remaining}")

    return resp.json()


def save_scores(data, target_date=None):
    """Save scores JSON to data/results/YYYY-MM-DD.json."""
    target_date = target_date or date.today().isoformat()
    os.makedirs(config.RESULTS_DIR, exist_ok=True)

    filepath = os.path.join(config.RESULTS_DIR, f"{target_date}.json")
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    completed = [g for g in data if g.get("completed")]
    print(f"Saved {len(data)} events ({len(completed)} completed) to {filepath}")
    return filepath


def parse_winner(event):
    """Determine winner from a completed scores event."""
    if not event.get("completed") or not event.get("scores"):
        return None

    scores = {s["name"]: int(s["score"]) for s in event["scores"] if s["score"]}
    if len(scores) < 2:
        return None

    return max(scores, key=scores.get)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days-ago", type=int, default=1,
                        help="How many days back to fetch scores (default: 1)")
    args = parser.parse_args()

    if not config.ODDS_API_KEY or config.ODDS_API_KEY == "your_api_key_here":
        print("ERROR: Set your ODDS_API_KEY in the .env file first.")
        sys.exit(1)

    target = date.today() - timedelta(days=args.days_ago)
    print(f"Fetching MLB scores (looking back {args.days_ago} day(s))...")
    data = fetch_scores(days_ago=args.days_ago)

    if not data:
        print("No score data returned.")
        return

    save_scores(data, target_date=target.isoformat())

    completed = [g for g in data if g.get("completed")]
    for game in completed:
        winner = parse_winner(game)
        if winner:
            print(f"  {game['home_team']} vs {game['away_team']} — Winner: {winner}")

    print(f"Done. {len(completed)} completed games.")
    return data


if __name__ == "__main__":
    main()
