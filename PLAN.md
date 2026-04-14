# MLB Underdog Betting Analysis — Project Plan

## High-Level Vision

Collect MLB odds data daily, filter to underdog scenarios, and watch for patterns
over time. Start with base assumptions about what makes a "good" underdog bet,
then let the accumulating data confirm, refute, or refine those assumptions.

This is a forward-looking experiment, not a backtest.

---

## High-Level Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1. MVP/POC | Daily data collection + filtering + tracking dashboard | **Start here** |
| 2. Enrich | Add situational factors (rest days, streaks, pitchers) | Later |
| 3. Odds Comparison | Multi-sportsbook price comparison tool | Later |
| 4. Refine | Adjust filters based on accumulated data, model break-evens | Later |

---

## Phase 1: MVP/POC — Detailed Plan

### Goal
Build a daily pipeline that:
1. Pulls today's MLB odds from multiple sportsbooks
2. Filters to qualifying underdog games
3. Records the odds and (next day) the results
4. Tracks cumulative performance over time

**Core question we're watching:** Do filtered underdog bets, despite losing
more often than winning, produce positive returns thanks to payout odds?

### Step 1: Project Setup
- Python project with virtual environment
- Dependencies: `requests`, `pandas`, `python-dotenv`, `matplotlib`
- `.env` file for API key (gitignored)
- Folder structure:
  ```
  Underdogs/
  ├── .env                  # ODDS_API_KEY=xxx
  ├── .gitignore
  ├── requirements.txt
  ├── config.py             # API config, filter thresholds, constants
  ├── data/
  │   ├── daily_odds/       # Raw daily JSON pulls
  │   ├── results/          # Game scores/outcomes
  │   └── tracking.csv      # Master ledger of all qualifying bets + outcomes
  ├── notebooks/
  │   └── dashboard.ipynb   # Running analysis + charts
  ├── src/
  │   ├── collect_odds.py   # Pull today's odds from Odds API
  │   ├── collect_scores.py # Pull completed game scores
  │   ├── filters.py        # Underdog qualification logic
  │   ├── tracker.py        # Update master ledger with new data + results
  │   └── analysis.py       # Win rate, ROI, break-even calculations
  └── PLAN.md
  ```

### Step 2: Daily Odds Collection
- Pull live MLB moneyline (h2h) odds via The Odds API
- Endpoint: `GET /v4/sports/baseball_mlb/odds`
- Params: `regions=us`, `markets=h2h`, `oddsFormat=american`
- Returns odds from DraftKings, FanDuel, BetMGM, Caesars, etc.
- Save raw JSON to `data/daily_odds/YYYY-MM-DD.json`
- **Credit cost:** 1 credit per pull (1 market, 1 region)
- **Plan:** Pull once per day (morning) = ~30 credits/month, well within free tier

### Step 3: Filtering — Starting Assumptions

These are our **initial filters** — they may be adjusted as data accumulates:

| Filter | Rule | Rationale |
|--------|------|-----------|
| **Exclude toss-ups** | Skip games where both teams between -125 and +125 | No clear underdog — not our target |
| **Exclude extreme favorites** | Skip games where favorite is -250 or stronger | Likely blowout, underdog has very low chance |
| **Qualifying range** | Underdog between +126 and +220 | Sweet spot: meaningful payout, reasonable chance |

**What we track for each qualifying game:**

| Field | Description |
|-------|-------------|
| `date` | Game date |
| `game_id` | Odds API event ID |
| `home_team` | Home team |
| `away_team` | Away team |
| `underdog` | Which team is the underdog |
| `dog_odds_best` | Best underdog moneyline across books |
| `dog_odds_avg` | Average underdog moneyline across books |
| `fav_odds_best` | Best favorite moneyline across books |
| `best_book` | Which sportsbook has best underdog price |
| `num_books` | How many books have lines |
| `home_dog` | Is the underdog at home? (True/False) |
| `bucket` | Odds bucket: slight (+126-150), moderate (+151-180), heavy (+181-220) |
| `winner` | Filled in after game completes |
| `dog_won` | True/False |
| `profit` | P/L on a flat $100 bet |

### Step 4: Score Collection & Ledger Update
- Pull completed scores via `GET /v4/sports/baseball_mlb/scores`
- Match results back to qualifying games in the ledger
- Calculate profit/loss per game:
  - Dog wins: profit = `$100 × (american_odds / 100)`
  - Dog loses: profit = `-$100`
- **Credit cost:** 1 credit per scores pull

### Step 5: Running Analysis (Dashboard Notebook)
As data accumulates, the notebook will show:

- **Record:** W-L count overall and per bucket
- **ROI:** Cumulative return on flat $100 bets
- **Win rate vs. break-even rate** per bucket
  - Break-even: `100 / (american_odds + 100)` → e.g., +150 needs 40% wins
- **Cumulative P/L chart** over time (the key visual)
- **Best book frequency:** Which sportsbook consistently offers best underdog prices
- **Home vs. away underdog performance**

### Step 6: Review & Adjust
After ~2-4 weeks of data:
- Are any buckets trending positive?
- Should we tighten or loosen the qualifying range?
- Is the toss-up cutoff (-125) in the right place?
- Are home underdogs performing differently than away?
- Document adjustments and reasoning in the notebook

---

## Phase 2: Enrichment (Future)

Layer in additional factors to see if they sharpen the edge:

- **Starting pitchers:** Cross-reference with pitcher data (free MLB Stats API)
  - Exclude games with top-25 pitchers on the mound
  - Track: does removing ace matchups improve underdog ROI?
- **Rest days:** Flag underdogs coming off a day off
- **Prior game result:** Coming off a loss vs. a win
- **Win/loss streaks:** Team on a losing streak may be undervalued
- **Series position:** Game 1 vs. game 2/3
- **Day/night games**
- **Division/interleague**

Each factor gets added as a column in the ledger so we can slice the data.

---

## Phase 3: Odds Comparison Tool (Future)

### Goal
Side-by-side comparison of today's odds across sportsbooks, highlighting
where the best underdog prices are.

### Approach
- Pull odds from 2-3 books (DraftKings, FanDuel, BetMGM) — already in Phase 1 data
- Display: Streamlit app or simple HTML table
- Highlight: best price per game, price discrepancies between books
- Flag games that qualify under our filters
- ~30 credits/day if pulling every 30 min (still well within free tier)

---

## Phase 4: Refine & Model (Future)

- Adjust all filter thresholds based on accumulated data
- Break-even modeling with confidence intervals
- Bankroll management / Kelly Criterion sizing
- Simulation of different strategies against collected data
- Decision: is any strategy actually viable long-term?

---

## API Credit Budget (Free Tier: 500/month)

| Activity | Credits | Frequency | Monthly Est. |
|----------|---------|-----------|-------------|
| Daily odds pull | 1 | 1x/day | ~30 |
| Daily scores pull | 1 | 1x/day | ~30 |
| Ad-hoc checks | 1 | As needed | ~20 |
| **Total** | | | **~80** |

Plenty of room within the free 500 credits. No need to upgrade unless we
add frequent intraday pulls in Phase 3.

---

## Tech Stack

- **Language:** Python 3.11+
- **Analysis:** pandas, numpy, matplotlib/seaborn
- **Notebooks:** Jupyter
- **API:** requests + local JSON caching
- **Future app:** Streamlit (simplest path to interactive UI)
- **Config:** python-dotenv for API keys

---

## Starting Assumptions to Watch

These are hypotheses, not conclusions. The data will tell us:

1. Underdogs in the +126 to +220 range win often enough to be profitable
2. The "sweet spot" is moderate underdogs (+151 to +180)
3. Home underdogs perform better than away underdogs
4. Teams coming off rest days perform better as underdogs
5. Removing extreme favorite matchups improves the dataset
6. Shopping across books for best price meaningfully impacts ROI
