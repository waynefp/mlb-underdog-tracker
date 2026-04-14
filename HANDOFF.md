# MLB Underdog Tracker — Handoff Document

## Project Overview

A data-driven experiment tracking MLB underdog betting performance. The system
collects daily odds from multiple sportsbooks, filters to qualifying underdog
games, tracks outcomes, and analyzes whether underdog payouts offset their
lower win rate.

**Core hypothesis:** Filtered MLB underdogs — excluding toss-ups, extreme
favorites, and (eventually) top-pitcher matchups — may produce positive ROI
because the payout odds compensate for a lower win rate.

**Approach:** Forward-looking data collection (not backtesting). Start with
base assumptions, collect daily, watch patterns emerge, adjust over time.

---

## Architecture

```
The Odds API (free tier, 500 credits/mo)
       │
       ▼
n8n Workflows (Hostinger VPS)
  ├── Workflow 1: Daily Odds Collection (12:07 PM ET)
  │     → Fetch MLB moneyline odds
  │     → Filter to qualifying underdogs (Code node)
  │     → Append to Google Sheet
  │     → Telegram notification with daily picks
  │
  └── Workflow 2: Results Update (11 PM ET + 8 AM ET)
        → Fetch completed scores
        → Read pending games from Google Sheet
        → Match results, calculate P/L
        → Update Google Sheet
        → Telegram notification with results
       │
       ▼
Google Sheets ("MLB Underdog Tracker")
  ├── Tracking tab — master ledger of all games + outcomes
  └── Dashboard tab — formulas for summary stats
       │
       ▼
Streamlit Dashboard (planned — Streamlit Community Cloud)
  └── Interactive charts, mobile-friendly
```

---

## Current Filter Thresholds (config.py)

| Filter | Value | Purpose |
|--------|-------|---------|
| Toss-up range | -130 to +130 | Skip games too close to call |
| Extreme favorite | -300 or stronger | Skip blowout matchups |
| Qualifying underdog | +131 to +260 | Our target range |

### Odds Buckets
| Bucket | Range |
|--------|-------|
| slight | +131 to +150 |
| moderate | +151 to +180 |
| heavy | +181 to +220 |
| very_heavy | +221 to +260 |

**Philosophy:** Start with a wide net, narrow based on what the data shows.

---

## Key Files

### Local Python Project (legacy/reference)
Built first, before pivoting to n8n + Google Sheets. Still useful for local
analysis or if you want to run things manually.

| File | Purpose |
|------|---------|
| `config.py` | Filter thresholds, API settings, paths |
| `src/collect_odds.py` | Pull today's odds from Odds API |
| `src/collect_scores.py` | Pull completed game scores |
| `src/filters.py` | Underdog qualification logic (Python version) |
| `src/tracker.py` | Master ledger management (add/update/status) |
| `src/analysis.py` | Win rate, ROI, break-even calculations |
| `notebooks/dashboard.ipynb` | Jupyter dashboard with charts |

### n8n Workflows (active — running on VPS)
| File | Purpose |
|------|---------|
| `n8n/workflow_1_collect_odds.json` | Daily odds → filter → Sheet → Telegram |
| `n8n/workflow_2_update_results.json` | Scores → match → P/L → Sheet → Telegram |
| `n8n/SETUP.md` | Setup guide for n8n workflows |

**Note:** The n8n workflow JSONs are reference copies. The live workflows
are on the Hostinger VPS n8n instance and may have been updated directly
in n8n (IF node fix, schedule changes, etc.). See "Known Fixes" below.

### Google Sheets Dashboard
| File | Purpose |
|------|---------|
| `sheets/dashboard_formulas.md` | All formulas for the Dashboard tab |

### Streamlit Dashboard (ready to deploy)
| File | Purpose |
|------|---------|
| `streamlit/app.py` | Full Streamlit dashboard app |
| `streamlit/requirements.txt` | Python dependencies |
| `streamlit/DEPLOY.md` | Deployment guide (VPS or Community Cloud) |

---

## n8n Workflow Details

### Workflow 1: MLB Underdog Odds Collection
- **Schedule:** Daily 12:07 PM ET
- **API call:** `GET /v4/sports/baseball_mlb/odds?regions=us&markets=h2h&oddsFormat=american`
- **Auth:** Query Auth credential (`apiKey` parameter)
- **Filter logic:** JavaScript Code node — mirrors Python filters.py
- **Output:** Appends qualifying games to Google Sheet "Tracking" tab
- **Notification:** Telegram with list of qualifying underdogs

### Workflow 2: MLB Underdog Results Update
- **Schedule:** 11:07 PM ET (evening — East Coast games) + 8:03 AM ET (morning — West Coast)
- **API call:** `GET /v4/sports/baseball_mlb/scores?daysFrom=2`
- **Auth:** Same Query Auth credential
- **Match logic:** JavaScript Code node — matches game_id from scores to pending Sheet rows
- **Output:** Updates winner, dog_won, profit columns in Google Sheet
- **Notification:** Telegram with results, labeled "Evening Update" or "Morning Final"
- **P/L calc:** Win = $100 × (american_odds / 100), Loss = -$100

### Known Fixes Applied in n8n (not in JSON files)
These were fixed directly in n8n during testing:

1. **IF node condition:** The `_no_games`/`_no_updates` check didn't work
   with strict type validation. Fixed by changing condition to:
   - Type: Number
   - Value: `{{ $json.dog_odds_best }}`
   - Operator: `larger than 0`

2. **Scores daysFrom:** Changed from `1` to `2` to catch games that cross
   midnight or when there's a gap.

3. **API auth:** Uses Query Auth credential (not Variables, which require
   Enterprise n8n). Credential name: "Odds API", key name: "apiKey".

4. **Google Sheets Append:** Node needed manual configuration of the
   spreadsheet/sheet selection after import — doesn't carry over from JSON.

---

## Google Sheet Structure

**Spreadsheet:** "MLB Underdog Tracker"

**Tracking tab columns (A-R):**
```
date | game_id | commence_time | home_team | away_team | favorite |
underdog | dog_odds_best | dog_odds_avg | dog_best_book | fav_odds_best |
fav_odds_avg | home_is_dog | bucket | num_books | winner | dog_won | profit
```

**Dashboard tab:** Formulas reference the Tracking tab. See `sheets/dashboard_formulas.md`.

---

## API Credit Usage

| Action | Credits | Frequency |
|--------|---------|-----------|
| Odds pull | 1 | 1x/day |
| Scores pull | 1 | 2x/day |
| **Monthly total** | | **~90 credits** |

Free tier: 500 credits/month. Plenty of headroom.

---

## Telegram Notifications

- **Bot:** Configured in n8n with Telegram Bot API credentials
- **Daily odds (~12 PM):** Lists qualifying underdogs with odds, bucket, best book
- **Evening results (~11 PM):** "🌙 Evening Update" — East Coast results
- **Morning results (~8 AM):** "☀️ Morning Final" — remaining results + confirmation

---

## What's Next (Planned)

### Immediate
- [ ] Set up Google Sheets Dashboard tab (formulas ready in `sheets/`)
- [ ] Deploy Streamlit dashboard to Streamlit Community Cloud
- [ ] Needs: Google Service Account for Sheets API access

### Phase 2: Enrichment
- [ ] Starting pitcher data (MLB Stats API — free)
- [ ] Filter out games with top-25 pitchers
- [ ] Rest days, prior game result, streaks
- [ ] Home/away deeper analysis
- [ ] Series position (game 1 vs 2 vs 3)

### Phase 3: Odds Comparison
- [ ] Side-by-side sportsbook comparison view
- [ ] Price discrepancy alerts
- [ ] Best-price-available tracking

### Phase 4: Strategy
- [ ] Break-even modeling with confidence intervals
- [ ] Kelly Criterion position sizing
- [ ] Bankroll simulation

---

## Hypotheses Being Tested

1. Underdogs in the +131 to +260 range win often enough to be profitable
2. The "sweet spot" is moderate underdogs (+151 to +180)
3. Home underdogs perform better than away underdogs
4. Teams coming off rest days perform better as underdogs
5. Removing extreme favorite matchups improves the dataset
6. Shopping across books for best price meaningfully impacts ROI

---

## Environment & Dependencies

- **Python:** 3.11+
- **n8n:** Self-hosted on Hostinger VPS
- **Google Sheets:** Primary data store
- **Telegram:** Notification channel
- **Odds API:** Free tier, Query Auth credential
- **Streamlit:** Planned dashboard (Community Cloud)
