"""
Configuration for the MLB Underdogs project.
Filter thresholds, API settings, and constants.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Odds API ---
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
ODDS_API_BASE = "https://api.the-odds-api.com/v4"
SPORT = "baseball_mlb"
REGIONS = "us"
MARKETS = "h2h"
ODDS_FORMAT = "american"

# --- Filter Thresholds ---
TOSSUP_MIN = -130
TOSSUP_MAX = 130
EXTREME_FAVORITE_CUTOFF = -300

# Qualifying underdog range — keep at 131 so watch_low games are still captured
UNDERDOG_MIN = 131
UNDERDOG_MAX = 260

# --- Odds Buckets ---
# Buckets define how games are labeled in tracking.
# watch_low and watch_high are tracked for data but excluded from wager alerts.
BUCKETS = {
    "watch_low":   (131, 135),   # track only — underperforming, no wager yet
    "slight":      (136, 150),   # standard wager
    "prime":       (151, 160),   # strong performer — split from old moderate
    "moderate":    (161, 190),   # dead zone — low unit wager
    "heavy":       (191, 220),   # strong performer — upper portion of old heavy
    "very_heavy":  (241, 249),   # strong performer — split from watch_high
    "watch_high":  (250, 260),   # wager for now, watching for potential track_only
}

# Buckets collected and tracked but NOT included in wager notifications
TRACK_ONLY_BUCKETS = {"watch_low"}

# Suggested unit multipliers per bucket (relative to FLAT_BET = 1 unit)
# Used as defaults in the Streamlit simulator
DEFAULT_MULTIPLIERS = {
    "watch_low":   0.0,   # track only
    "slight":      1.0,
    "prime":       1.0,
    "moderate":    0.5,   # dead zone — half unit
    "heavy":       1.0,
    "very_heavy":  1.25,
    "watch_high":  1.0,
}

# --- Betting ---
FLAT_BET = 100  # Dollar amount per unit

# --- Paths ---
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DAILY_ODDS_DIR = os.path.join(DATA_DIR, "daily_odds")
RESULTS_DIR = os.path.join(DATA_DIR, "results")
TRACKING_CSV = os.path.join(DATA_DIR, "tracking.csv")
