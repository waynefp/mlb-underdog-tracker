"""
Pull today's MLB moneyline odds from The Odds API and save raw JSON.
Usage: python -m src.collect_odds
"""

import json
import os
import sys
from datetime import date

import requests

# Allow running as module from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


def fetch_odds():
    """Fetch current MLB moneyline odds from all US sportsbooks."""
    url = f"{config.ODDS_API_BASE}/sports/{config.SPORT}/odds"
    params = {
        "apiKey": config.ODDS_API_KEY,
        "regions": config.REGIONS,
        "markets": config.MARKETS,
        "oddsFormat": config.ODDS_FORMAT,
    }

    resp = requests.get(url, params=params)
    resp.raise_for_status()

    # Log remaining credits from response headers
    remaining = resp.headers.get("x-requests-remaining", "?")
    used = resp.headers.get("x-requests-used", "?")
    print(f"API credits — used: {used}, remaining: {remaining}")

    return resp.json()


def save_odds(data, target_date=None):
    """Save raw odds JSON to data/daily_odds/YYYY-MM-DD.json."""
    target_date = target_date or date.today().isoformat()
    os.makedirs(config.DAILY_ODDS_DIR, exist_ok=True)

    filepath = os.path.join(config.DAILY_ODDS_DIR, f"{target_date}.json")
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Saved {len(data)} events to {filepath}")
    return filepath


def main():
    if not config.ODDS_API_KEY or config.ODDS_API_KEY == "your_api_key_here":
        print("ERROR: Set your ODDS_API_KEY in the .env file first.")
        sys.exit(1)

    print(f"Fetching MLB odds for {date.today().isoformat()}...")
    data = fetch_odds()

    if not data:
        print("No MLB events found. Season may not be active.")
        return

    filepath = save_odds(data)
    print(f"Done. {len(data)} games saved.")
    return data


if __name__ == "__main__":
    main()
