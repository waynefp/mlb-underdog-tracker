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

# --- Filter Thresholds (Starting Assumptions) ---
# Games where both sides are between these values are "toss-ups" — skip them
TOSSUP_MIN = -130
TOSSUP_MAX = 130

# Favorites stronger than this are "extreme" — skip these games
EXTREME_FAVORITE_CUTOFF = -300

# Qualifying underdog range (American odds)
UNDERDOG_MIN = 131   # Must be at least this much of an underdog
UNDERDOG_MAX = 260   # Expanded to capture heavy underdogs (can trim later)

# --- Odds Buckets ---
BUCKETS = {
    "slight":   (131, 150),
    "moderate": (151, 180),
    "heavy":    (181, 220),
    "very_heavy": (221, 260),
}

# --- Betting ---
FLAT_BET = 100  # Dollar amount for flat bet tracking

# --- Paths ---
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DAILY_ODDS_DIR = os.path.join(DATA_DIR, "daily_odds")
RESULTS_DIR = os.path.join(DATA_DIR, "results")
TRACKING_CSV = os.path.join(DATA_DIR, "tracking.csv")
