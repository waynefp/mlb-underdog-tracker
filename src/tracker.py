"""
Master ledger management — add qualifying games, update with results, calculate P/L.
Usage:
    python -m src.tracker add       # Process today's odds and add qualifying games
    python -m src.tracker update    # Match scores to pending games and calc P/L
    python -m src.tracker status    # Print summary of current ledger
"""

import argparse
import json
import os
import sys
from datetime import date, timedelta

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
from src.filters import filter_events
from src.collect_scores import parse_winner


LEDGER_COLUMNS = [
    "date", "game_id", "commence_time", "home_team", "away_team",
    "favorite", "underdog", "dog_odds_best", "dog_odds_avg", "dog_best_book",
    "fav_odds_best", "fav_odds_avg", "home_is_dog", "bucket", "num_books",
    "winner", "dog_won", "profit",
]


def load_ledger():
    """Load or create the tracking CSV."""
    if os.path.exists(config.TRACKING_CSV):
        return pd.read_csv(config.TRACKING_CSV)
    return pd.DataFrame(columns=LEDGER_COLUMNS)


def save_ledger(df):
    """Save ledger to CSV."""
    os.makedirs(os.path.dirname(config.TRACKING_CSV), exist_ok=True)
    df.to_csv(config.TRACKING_CSV, index=False)
    print(f"Ledger saved: {len(df)} total rows")


def add_todays_games():
    """Load today's odds file, filter, and append qualifying games to ledger."""
    today = date.today().isoformat()
    odds_file = os.path.join(config.DAILY_ODDS_DIR, f"{today}.json")

    if not os.path.exists(odds_file):
        print(f"No odds file for {today}. Run collect_odds first.")
        return

    with open(odds_file) as f:
        events = json.load(f)

    qualifying = filter_events(events)
    if not qualifying:
        print("No qualifying underdog games today.")
        return

    ledger = load_ledger()

    # Avoid duplicates
    existing_ids = set(ledger["game_id"].values) if len(ledger) > 0 else set()
    new_games = [g for g in qualifying if g["game_id"] not in existing_ids]

    if not new_games:
        print("All qualifying games already in ledger.")
        return

    new_rows = pd.DataFrame(new_games)
    new_rows["date"] = today
    new_rows["winner"] = None
    new_rows["dog_won"] = None
    new_rows["profit"] = None

    ledger = pd.concat([ledger, new_rows], ignore_index=True)
    save_ledger(ledger)

    print(f"\nAdded {len(new_games)} qualifying games:")
    for g in new_games:
        print(f"  {g['underdog']} (+{g['dog_odds_best']}) vs {g['favorite']} "
              f"[{g['bucket']}] — best at {g['dog_best_book']}")


def update_results():
    """Match completed scores to pending games and calculate P/L."""
    ledger = load_ledger()
    pending = ledger[ledger["winner"].isna()]

    if len(pending) == 0:
        print("No pending games to update.")
        return

    # Load all available score files
    scores_by_id = {}
    if os.path.exists(config.RESULTS_DIR):
        for fname in os.listdir(config.RESULTS_DIR):
            if not fname.endswith(".json"):
                continue
            with open(os.path.join(config.RESULTS_DIR, fname)) as f:
                for event in json.load(f):
                    if event.get("completed"):
                        winner = parse_winner(event)
                        if winner:
                            scores_by_id[event["id"]] = winner

    updated = 0
    for idx in pending.index:
        game_id = ledger.at[idx, "game_id"]
        if game_id in scores_by_id:
            winner = scores_by_id[game_id]
            underdog = ledger.at[idx, "underdog"]
            dog_odds = ledger.at[idx, "dog_odds_best"]

            dog_won = winner == underdog
            if dog_won:
                profit = config.FLAT_BET * (dog_odds / 100)
            else:
                profit = -config.FLAT_BET

            ledger.at[idx, "winner"] = winner
            ledger.at[idx, "dog_won"] = dog_won
            ledger.at[idx, "profit"] = round(profit, 2)
            updated += 1

            result = "WIN" if dog_won else "loss"
            print(f"  {result}: {underdog} (+{dog_odds}) — P/L: ${profit:+.2f}")

    if updated > 0:
        save_ledger(ledger)
    print(f"\nUpdated {updated} of {len(pending)} pending games.")


def print_status():
    """Print a summary of the current ledger."""
    ledger = load_ledger()

    if len(ledger) == 0:
        print("Ledger is empty. Run 'add' to start tracking games.")
        return

    total = len(ledger)
    resolved = ledger[ledger["winner"].notna()]
    pending = ledger[ledger["winner"].isna()]

    print(f"\n{'='*50}")
    print(f"UNDERDOG TRACKER — STATUS")
    print(f"{'='*50}")
    print(f"Total games tracked:  {total}")
    print(f"Resolved:             {len(resolved)}")
    print(f"Pending:              {len(pending)}")

    if len(resolved) > 0:
        wins = resolved["dog_won"].sum()
        losses = len(resolved) - wins
        win_rate = wins / len(resolved) * 100
        total_profit = resolved["profit"].sum()

        print(f"\nRecord:  {int(wins)}W - {int(losses)}L ({win_rate:.1f}%)")
        print(f"Total P/L:  ${total_profit:+.2f}")
        print(f"Avg P/L per bet:  ${total_profit / len(resolved):+.2f}")

        print(f"\nBy bucket:")
        for bucket in config.BUCKETS:
            b = resolved[resolved["bucket"] == bucket]
            if len(b) > 0:
                bw = b["dog_won"].sum()
                bl = len(b) - bw
                bp = b["profit"].sum()
                print(f"  {bucket:10s}  {int(bw)}W-{int(bl)}L  "
                      f"P/L: ${bp:+.2f}")

    print(f"{'='*50}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["add", "update", "status"],
                        help="add: add today's qualifying games | "
                             "update: fill in results | status: print summary")
    args = parser.parse_args()

    if args.action == "add":
        add_todays_games()
    elif args.action == "update":
        update_results()
    elif args.action == "status":
        print_status()


if __name__ == "__main__":
    main()
