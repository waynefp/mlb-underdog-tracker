# n8n Workflow Setup Guide

## Before Importing

### 1. Create a "Query Auth" Credential for the Odds API
- In n8n, go to **Credentials → Create New**
- Search for and select **"Query Auth"** (under HTTP Request types)
- Configure:
  - **Credential Name:** `Odds API`
  - **Name:** `apiKey`
  - **Value:** `<your-odds-api-key>`
- Save
- Both workflows' HTTP Request nodes will reference this credential, and n8n will automatically append `?apiKey=...` to every Odds API call

### 2. Create the Google Sheet
- Create a new Google Sheet named **"MLB Underdog Tracker"**
- Name the first tab **"Tracking"**
- Add these column headers in Row 1:

```
date | game_id | commence_time | home_team | away_team | favorite | underdog | dog_odds_best | dog_odds_avg | dog_best_book | fav_odds_best | fav_odds_avg | home_is_dog | bucket | num_books | winner | dog_won | profit
```

### 3. Ensure Credentials Exist in n8n
- **Google Sheets** — OAuth2 or Service Account credentials
- **Telegram** — Bot API token (from @BotFather)

---

## Import & Configure Workflow 1: "MLB Underdog Odds Collection"

1. **Import** `workflow_1_collect_odds.json` via n8n → Workflows → Import
2. **Configure these nodes:**

   **"Fetch MLB Odds"** node:
   - Under "Credential for Query Auth", select the `Odds API` credential

   **"Append to Tracking Sheet"** node:
   - Select your Google Sheets credential
   - Select the "MLB Underdog Tracker" spreadsheet
   - Select the "Tracking" sheet tab

   **"Send Telegram"** node:
   - Select your Telegram Bot credential
   - Set `chatId` to your Telegram chat ID
     (message @userinfobot on Telegram to get your ID)

3. **Test:** Click "Execute Workflow" manually to verify
4. **Activate** the workflow — runs daily at 12:07 PM ET

---

## Import & Configure Workflow 2: "MLB Underdog Results Update"

1. **Import** `workflow_2_update_results.json` via n8n → Workflows → Import
2. **Configure these nodes:**

   **"Fetch MLB Scores"** node:
   - Under "Credential for Query Auth", select the same `Odds API` credential

   **"Read Pending Games"** node:
   - Select your Google Sheets credential
   - Select the "MLB Underdog Tracker" spreadsheet
   - Select the "Tracking" sheet tab
   - Filter: column `winner` equals `` (empty string)

   **"Update Tracking Sheet"** node:
   - Select your Google Sheets credential
   - Select the same spreadsheet + sheet
   - Match column: `game_id`

   **"Send Telegram"** node:
   - Select your Telegram Bot credential
   - Set `chatId` (same as Workflow 1)

3. **Test:** Run manually after Workflow 1 has added some games
4. **Activate** the workflow — runs daily at 11:03 AM ET

---

## Schedule Summary

| Workflow | Time (ET) | What it does |
|----------|-----------|-------------|
| Odds Collection | 12:07 PM | Pull today's lines, filter, save to sheet, notify |
| Results Update | 11:03 AM | Match yesterday's scores, calc P/L, update sheet, notify |

---

## Telegram Messages You'll Receive

**Daily odds report (~12:07 PM):**
```
⚾ MLB Underdog Report — 2026-04-08

📊 Filter Results:
Games today: 8
Toss-ups: 1 | Extreme: 2 | Out of range: 1

✅ 4 Qualifying Underdogs:

🔹 Athletics (Away) +180
   vs New York Yankees (-200)
   Bucket: moderate | Best: fanduel
```

**Daily results report (~11:03 AM):**
```
⚾ MLB Underdog Results — 2026-04-09

📊 Updated: 4 games
Record today: 1W - 3L
P/L today: -$120.00

✅ Athletics (+180) vs New York Yankees
   WIN | +$180 | moderate

❌ Colorado Rockies (+174) vs San Diego Padres
   Loss | -$100 | moderate
```
