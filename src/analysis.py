"""
Analysis functions — win rates, ROI, break-even calculations.
Used by the dashboard notebook and tracker status.
"""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


def load_resolved():
    """Load only resolved (completed) games from the ledger."""
    if not os.path.exists(config.TRACKING_CSV):
        return pd.DataFrame()
    df = pd.read_csv(config.TRACKING_CSV)
    return df[df["winner"].notna()].copy()


def american_to_decimal(american_odds):
    """Convert American odds to decimal odds."""
    if american_odds > 0:
        return (american_odds / 100) + 1
    else:
        return (100 / abs(american_odds)) + 1


def break_even_rate(american_odds):
    """
    Required win rate to break even at given American odds.
    e.g., +150 → needs 40% wins to break even.
    """
    decimal = american_to_decimal(american_odds)
    return 1 / decimal


def summary_by_bucket(df=None):
    """
    Summary stats grouped by odds bucket.
    Returns DataFrame with: games, wins, losses, win_rate, break_even_avg,
    edge (win_rate - break_even), total_profit, roi.
    """
    if df is None:
        df = load_resolved()
    if len(df) == 0:
        return pd.DataFrame()

    results = []
    for bucket in list(config.BUCKETS.keys()) + ["all"]:
        if bucket == "all":
            subset = df
        else:
            subset = df[df["bucket"] == bucket]

        if len(subset) == 0:
            continue

        games = len(subset)
        wins = int(subset["dog_won"].sum())
        losses = games - wins
        win_rate = wins / games
        avg_be = subset["dog_odds_best"].apply(break_even_rate).mean()
        total_profit = subset["profit"].sum()

        results.append({
            "bucket": bucket,
            "games": games,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 4),
            "break_even_avg": round(avg_be, 4),
            "edge": round(win_rate - avg_be, 4),
            "total_profit": round(total_profit, 2),
            "roi": round(total_profit / (games * config.FLAT_BET) * 100, 2),
        })

    return pd.DataFrame(results)


def cumulative_pl(df=None):
    """Calculate cumulative P/L over time. Returns DataFrame with date and cum_profit."""
    if df is None:
        df = load_resolved()
    if len(df) == 0:
        return pd.DataFrame()

    df = df.sort_values("date").copy()
    df["cum_profit"] = df["profit"].cumsum()
    df["bet_number"] = range(1, len(df) + 1)
    return df[["date", "bet_number", "underdog", "dog_odds_best", "bucket",
               "dog_won", "profit", "cum_profit"]]


def best_book_frequency(df=None):
    """Which sportsbook most often has the best underdog price?"""
    if df is None:
        df = load_resolved()
    if len(df) == 0:
        return pd.DataFrame()

    return (df["dog_best_book"]
            .value_counts()
            .reset_index()
            .rename(columns={"index": "book", "dog_best_book": "book",
                              "count": "times_best"}))


def home_vs_away(df=None):
    """Compare underdog performance: home dogs vs away dogs."""
    if df is None:
        df = load_resolved()
    if len(df) == 0:
        return pd.DataFrame()

    results = []
    for label, is_home in [("home_dog", True), ("away_dog", False)]:
        subset = df[df["home_is_dog"] == is_home]
        if len(subset) == 0:
            continue
        games = len(subset)
        wins = int(subset["dog_won"].sum())
        results.append({
            "type": label,
            "games": games,
            "wins": wins,
            "losses": games - wins,
            "win_rate": round(wins / games, 4),
            "total_profit": round(subset["profit"].sum(), 2),
            "roi": round(subset["profit"].sum() / (games * config.FLAT_BET) * 100, 2),
        })

    return pd.DataFrame(results)
