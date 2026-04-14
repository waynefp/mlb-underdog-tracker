# Google Sheets Dashboard Tab — Setup Guide

Create a new tab called **"Dashboard"** in your MLB Underdog Tracker spreadsheet.
The formulas below reference the **"Tracking"** tab where your data lives.

Assumes the Tracking tab columns are:
- A: date, B: game_id, C: commence_time, D: home_team, E: away_team
- F: favorite, G: underdog, H: dog_odds_best, I: dog_odds_avg
- J: dog_best_book, K: fav_odds_best, L: fav_odds_avg
- M: home_is_dog, N: bucket, O: num_books
- P: winner, Q: dog_won, R: profit

**Adjust column letters if your layout differs.**

---

## Row 1: Title
| Cell | Value |
|------|-------|
| A1 | `⚾ MLB Underdog Tracker — Dashboard` |

---

## Row 3-8: Overall Summary
| Cell | Label | Cell | Formula |
|------|-------|------|---------|
| A3 | **Overall Record** | | |
| A4 | Total Games Tracked | B4 | `=COUNTA(Tracking!B2:B)` |
| A5 | Games Resolved | B5 | `=COUNTIF(Tracking!P2:P,"<>")` |
| A6 | Games Pending | B6 | `=B4-B5` |
| A7 | Underdog Wins | B7 | `=COUNTIF(Tracking!Q2:Q,TRUE)` |
| A8 | Underdog Losses | B8 | `=B5-B7` |

---

## Row 3-8: Column D-E — Key Metrics
| Cell | Label | Cell | Formula |
|------|-------|------|---------|
| D3 | **Key Metrics** | | |
| D4 | Win Rate | E4 | `=IF(B5>0,B7/B5,0)` |
| D5 | Total P/L | E5 | `=SUM(Tracking!R2:R)` |
| D6 | Avg P/L Per Bet | E6 | `=IF(B5>0,E5/B5,0)` |
| D7 | Total Wagered | E7 | `=B5*100` |
| D8 | ROI | E8 | `=IF(E7>0,E5/E7,0)` |

Format: E4/E8 as percentage, E5/E6/E7 as currency.

---

## Row 10-16: Performance by Bucket
| Cell | Label |
|------|-------|
| A10 | **By Bucket** |
| A11 | Bucket |
| B11 | Games |
| C11 | Wins |
| D11 | Losses |
| E11 | Win Rate |
| F11 | P/L |
| G11 | ROI |
| H11 | Break-Even Needed |

| Row | A (Bucket) | B (Games) | C (Wins) | D (Losses) | E (Win Rate) | F (P/L) | G (ROI) | H (Break-Even) |
|-----|------------|-----------|----------|------------|--------------|---------|---------|-----------------|
| 12 | slight | `=COUNTIFS(Tracking!N2:N,"slight",Tracking!P2:P,"<>")` | `=COUNTIFS(Tracking!N2:N,"slight",Tracking!Q2:Q,TRUE)` | `=B12-C12` | `=IF(B12>0,C12/B12,0)` | `=SUMIFS(Tracking!R2:R,Tracking!N2:N,"slight",Tracking!P2:P,"<>")` | `=IF(B12>0,F12/(B12*100),0)` | `=IF(B12>0,AVERAGEIFS(Tracking!H2:H,Tracking!N2:N,"slight",Tracking!P2:P,"<>")/100,0)` |
| 13 | moderate | `=COUNTIFS(Tracking!N2:N,"moderate",Tracking!P2:P,"<>")` | `=COUNTIFS(Tracking!N2:N,"moderate",Tracking!Q2:Q,TRUE)` | `=B13-C13` | `=IF(B13>0,C13/B13,0)` | `=SUMIFS(Tracking!R2:R,Tracking!N2:N,"moderate",Tracking!P2:P,"<>")` | `=IF(B13>0,F13/(B13*100),0)` | `=IF(B13>0,AVERAGEIFS(Tracking!H2:H,Tracking!N2:N,"moderate",Tracking!P2:P,"<>")/100,0)` |
| 14 | heavy | `=COUNTIFS(Tracking!N2:N,"heavy",Tracking!P2:P,"<>")` | `=COUNTIFS(Tracking!N2:N,"heavy",Tracking!Q2:Q,TRUE)` | `=B14-C14` | `=IF(B14>0,C14/B14,0)` | `=SUMIFS(Tracking!R2:R,Tracking!N2:N,"heavy",Tracking!P2:P,"<>")` | `=IF(B14>0,F14/(B14*100),0)` | `=IF(B14>0,AVERAGEIFS(Tracking!H2:H,Tracking!N2:N,"heavy",Tracking!P2:P,"<>")/100,0)` |
| 15 | very_heavy | `=COUNTIFS(Tracking!N2:N,"very_heavy",Tracking!P2:P,"<>")` | `=COUNTIFS(Tracking!N2:N,"very_heavy",Tracking!Q2:Q,TRUE)` | `=B15-C15` | `=IF(B15>0,C15/B15,0)` | `=SUMIFS(Tracking!R2:R,Tracking!N2:N,"very_heavy",Tracking!P2:P,"<>")` | `=IF(B15>0,F15/(B15*100),0)` | `=IF(B15>0,AVERAGEIFS(Tracking!H2:H,Tracking!N2:N,"very_heavy",Tracking!P2:P,"<>")/100,0)` |
| 16 | **TOTAL** | `=SUM(B12:B15)` | `=SUM(C12:C15)` | `=SUM(D12:D15)` | `=IF(B16>0,C16/B16,0)` | `=SUM(F12:F15)` | `=IF(B16>0,F16/(B16*100),0)` | |

Note on Break-Even (column H): This shows the average underdog odds divided by 100 for that bucket. The true break-even win rate formula is `1 / (1 + odds/100)`. Use this formula instead for H12-H15:
`=IF(B12>0, 1/(1+AVERAGEIFS(Tracking!H2:H,Tracking!N2:N,"slight",Tracking!P2:P,"<>")/100), 0)`
(Change "slight" for each bucket.)

---

## Row 18-22: Home vs Away Underdogs
| Cell | Label |
|------|-------|
| A18 | **Home vs Away** |
| A19 | Type |
| B19 | Games |
| C19 | Wins |
| D19 | Win Rate |
| E19 | P/L |

| Row | A | B | C | D | E |
|-----|---|---|---|---|---|
| 20 | Home Dog | `=COUNTIFS(Tracking!M2:M,TRUE,Tracking!P2:P,"<>")` | `=COUNTIFS(Tracking!M2:M,TRUE,Tracking!Q2:Q,TRUE)` | `=IF(B20>0,C20/B20,0)` | `=SUMIFS(Tracking!R2:R,Tracking!M2:M,TRUE,Tracking!P2:P,"<>")` |
| 21 | Away Dog | `=COUNTIFS(Tracking!M2:M,FALSE,Tracking!P2:P,"<>")` | `=COUNTIFS(Tracking!M2:M,FALSE,Tracking!Q2:Q,TRUE)` | `=IF(B21>0,C21/B21,0)` | `=SUMIFS(Tracking!R2:R,Tracking!M2:M,FALSE,Tracking!P2:P,"<>")` |

---

## Row 24-30: Best Sportsbook
| Cell | Label |
|------|-------|
| A24 | **Best Book Frequency** |
| A25 | Sportsbook |
| B25 | Times Best Price |
| C25 | % of Time |

| Row | A | B | C |
|-----|---|---|---|
| 26 | fanduel | `=COUNTIF(Tracking!J2:J,"fanduel")` | `=IF(B$4>0,B26/B$4,0)` |
| 27 | draftkings | `=COUNTIF(Tracking!J2:J,"draftkings")` | `=IF(B$4>0,B27/B$4,0)` |
| 28 | betmgm | `=COUNTIF(Tracking!J2:J,"betmgm")` | `=IF(B$4>0,B28/B$4,0)` |
| 29 | betrivers | `=COUNTIF(Tracking!J2:J,"betrivers")` | `=IF(B$4>0,B29/B$4,0)` |
| 30 | betus | `=COUNTIF(Tracking!J2:J,"betus")` | `=IF(B$4>0,B30/B$4,0)` |
| 31 | betonlineag | `=COUNTIF(Tracking!J2:J,"betonlineag")` | `=IF(B$4>0,B31/B$4,0)` |
| 32 | lowvig | `=COUNTIF(Tracking!J2:J,"lowvig")` | `=IF(B$4>0,B32/B$4,0)` |

Add more rows as you see new book names appear in the data.

---

## Row 34+: Recent Results (Last 10)
| Cell | Label |
|------|-------|
| A34 | **Recent Results** |
| A35 | Date |
| B35 | Underdog |
| C35 | Odds |
| D35 | Bucket |
| E35 | Result |
| F35 | P/L |

For rows 36-45, use OFFSET-based formulas to pull the last 10 resolved games.
This is harder with pure formulas — alternatively, use SORT + FILTER:

**Cell A36:**
`=IFERROR(SORT(FILTER(Tracking!A2:R,Tracking!P2:P<>""),1,FALSE),"No results yet")`

This will dump the most recent resolved games sorted by date descending.
You can limit to 10 by wrapping in ARRAY_CONSTRAIN:
`=IFERROR(ARRAY_CONSTRAIN(SORT(FILTER({Tracking!A2:A,Tracking!G2:G,Tracking!H2:H,Tracking!N2:N,Tracking!Q2:Q,Tracking!R2:R},Tracking!P2:P<>""),1,FALSE),10,6),"No results yet")`

---

## Formatting Tips
- Win Rate / ROI columns: Format as Percentage
- P/L columns: Format as Currency, use conditional formatting (green positive, red negative)
- Break-Even column: Format as Percentage
- Bold the header rows
- Freeze row 1
