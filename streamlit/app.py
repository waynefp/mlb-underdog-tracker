"""
MLB Underdog Tracker — Streamlit Dashboard
Reads from Google Sheets and displays interactive charts.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
import json
import os
from datetime import datetime

# --- Page Config ---
st.set_page_config(
    page_title="MLB Underdog Tracker",
    page_icon="⚾",
    layout="wide",
)

# --- Google Sheets Connection ---
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_data():
    """Load tracking data from Google Sheets."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]

    # Load service account credentials from Streamlit secrets or file
    creds = None
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    except Exception:
        pass

    if creds is None and os.path.exists("baseball-data_service_account.json"):
        creds = Credentials.from_service_account_file("baseball-data_service_account.json", scopes=scopes)
    elif creds is None and os.path.exists("service_account.json"):
        creds = Credentials.from_service_account_file("service_account.json", scopes=scopes)

    if creds is None:
        st.error("No Google credentials found. Add service_account.json or configure Streamlit secrets.")
        return pd.DataFrame()

    gc = gspread.authorize(creds)

    # Open the spreadsheet — update this name if yours differs
    spreadsheet_name = os.environ.get("SHEET_NAME", "MLB Underdog Tracker")
    try:
        sheet = gc.open(spreadsheet_name).worksheet("Tracking")
    except gspread.SpreadsheetNotFound:
        st.error(f"Spreadsheet '{spreadsheet_name}' not found. Check the name and sharing permissions.")
        return pd.DataFrame()

    data = sheet.get_all_records()
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)

    # Type conversions
    numeric_cols = ["dog_odds_best", "dog_odds_avg", "fav_odds_best", "fav_odds_avg", "num_books", "profit"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "home_is_dog" in df.columns:
        df["home_is_dog"] = df["home_is_dog"].astype(str).str.upper().isin(["TRUE", "1", "YES"])

    if "dog_won" in df.columns:
        df["dog_won"] = df["dog_won"].astype(str).str.upper().isin(["TRUE", "1", "YES"])

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    return df


def break_even_rate(american_odds):
    """Required win rate to break even at given American odds."""
    if pd.isna(american_odds) or american_odds <= 0:
        return None
    decimal = (american_odds / 100) + 1
    return 1 / decimal


# --- Load Data ---
df = load_data()

# --- Header ---
st.title("⚾ MLB Underdog Tracker")
st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}  •  Click the ↻ button to refresh")

if df.empty:
    st.info("No data yet. The dashboard will populate as games are tracked.")
    st.stop()

# Split into resolved and pending
resolved = df[df["winner"].astype(str).str.len() > 0].copy()
pending = df[df["winner"].astype(str).str.len() == 0].copy()

# --- Top Metrics ---
st.markdown("---")
col1, col2, col3, col4, col5, col6 = st.columns(6)

total_games = len(df)
num_resolved = len(resolved)
num_pending = len(pending)

if num_resolved > 0:
    wins = resolved["dog_won"].sum()
    losses = num_resolved - wins
    win_rate = wins / num_resolved
    total_pl = resolved["profit"].sum()
    roi = total_pl / (num_resolved * 100) * 100
else:
    wins = losses = 0
    win_rate = total_pl = roi = 0

col1.metric("Total Tracked", total_games)
col2.metric("Resolved", num_resolved)
col3.metric("Pending", num_pending)
col4.metric("Record", f"{int(wins)}W - {int(losses)}L")
col5.metric("Total P/L", f"${total_pl:+,.2f}")
col6.metric("ROI", f"{roi:+.1f}%")

if num_resolved == 0:
    st.info("No resolved games yet — metrics and charts will appear once results come in.")
    if num_pending > 0:
        st.subheader("📋 Pending Games")
        st.dataframe(
            pending[["date", "underdog", "dog_odds_best", "favorite", "bucket", "dog_best_book"]],
            use_container_width=True,
            hide_index=True,
        )
    st.stop()

# --- Cumulative P/L Chart ---
st.markdown("---")
st.subheader("📈 Cumulative Profit/Loss")

resolved_sorted = resolved.sort_values("date").copy()
resolved_sorted["cum_profit"] = resolved_sorted["profit"].cumsum()
resolved_sorted["bet_number"] = range(1, len(resolved_sorted) + 1)

fig_pl = go.Figure()
fig_pl.add_trace(go.Scatter(
    x=resolved_sorted["bet_number"],
    y=resolved_sorted["cum_profit"],
    mode="lines+markers",
    line=dict(color="#2196F3", width=2),
    marker=dict(
        size=8,
        color=resolved_sorted["dog_won"].map({True: "#4CAF50", False: "#f44336"}),
    ),
    hovertext=resolved_sorted.apply(
        lambda r: f"{r['underdog']} (+{r['dog_odds_best']})<br>"
                  f"{'WIN' if r['dog_won'] else 'Loss'}: ${r['profit']:+.2f}<br>"
                  f"Cumulative: ${r['cum_profit']:+.2f}",
        axis=1
    ),
    hoverinfo="text",
))
fig_pl.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
fig_pl.update_layout(
    xaxis_title="Bet #",
    yaxis_title="Cumulative P/L ($)",
    height=400,
    margin=dict(l=40, r=20, t=20, b=40),
)
st.plotly_chart(fig_pl, use_container_width=True)

# --- Two-Column Charts ---
col_left, col_right = st.columns(2)

# --- Performance by Bucket ---
with col_left:
    st.subheader("🪣 Performance by Bucket")

    bucket_order = ["slight", "moderate", "heavy", "very_heavy"]
    bucket_data = []
    for bucket in bucket_order:
        subset = resolved[resolved["bucket"] == bucket]
        if len(subset) == 0:
            continue
        games = len(subset)
        bwins = int(subset["dog_won"].sum())
        blosses = games - bwins
        bwr = bwins / games
        avg_odds = subset["dog_odds_best"].mean()
        be_rate = break_even_rate(avg_odds) if avg_odds > 0 else 0
        bpl = subset["profit"].sum()

        bucket_data.append({
            "Bucket": bucket,
            "Games": games,
            "Wins": bwins,
            "Losses": blosses,
            "Win Rate": bwr,
            "Break-Even": be_rate,
            "Edge": bwr - (be_rate or 0),
            "P/L": bpl,
            "ROI": bpl / (games * 100) * 100,
        })

    if bucket_data:
        bdf = pd.DataFrame(bucket_data)

        fig_bucket = go.Figure()
        fig_bucket.add_trace(go.Bar(
            x=bdf["Bucket"], y=bdf["Win Rate"],
            name="Actual Win Rate", marker_color="#2196F3",
        ))
        fig_bucket.add_trace(go.Bar(
            x=bdf["Bucket"], y=bdf["Break-Even"],
            name="Break-Even Needed", marker_color="#FF9800", opacity=0.7,
        ))
        fig_bucket.update_layout(
            barmode="group",
            yaxis_tickformat=".0%",
            height=350,
            margin=dict(l=40, r=20, t=20, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig_bucket, use_container_width=True)

        # Summary table
        display_df = bdf.copy()
        display_df["Win Rate"] = display_df["Win Rate"].map("{:.1%}".format)
        display_df["Break-Even"] = display_df["Break-Even"].map("{:.1%}".format)
        display_df["Edge"] = display_df["Edge"].map("{:+.1%}".format)
        display_df["P/L"] = display_df["P/L"].map("${:+,.2f}".format)
        display_df["ROI"] = display_df["ROI"].map("{:+.1f}%".format)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

# --- Home vs Away ---
with col_right:
    st.subheader("🏠 Home vs Away Underdogs")

    ha_data = []
    for label, is_home in [("Home Dog", True), ("Away Dog", False)]:
        subset = resolved[resolved["home_is_dog"] == is_home]
        if len(subset) == 0:
            continue
        games = len(subset)
        hwins = int(subset["dog_won"].sum())
        ha_data.append({
            "Type": label,
            "Games": games,
            "Wins": hwins,
            "Losses": games - hwins,
            "Win Rate": hwins / games,
            "P/L": subset["profit"].sum(),
        })

    if ha_data:
        hadf = pd.DataFrame(ha_data)

        fig_ha = go.Figure()
        fig_ha.add_trace(go.Bar(
            x=hadf["Type"], y=hadf["Win Rate"],
            marker_color=["#4CAF50", "#2196F3"],
            text=hadf["Win Rate"].map(lambda x: f"{x:.1%}"),
            textposition="auto",
        ))
        fig_ha.update_layout(
            yaxis_tickformat=".0%",
            height=350,
            margin=dict(l=40, r=20, t=20, b=40),
        )
        st.plotly_chart(fig_ha, use_container_width=True)

        display_ha = hadf.copy()
        display_ha["Win Rate"] = display_ha["Win Rate"].map("{:.1%}".format)
        display_ha["P/L"] = display_ha["P/L"].map("${:+,.2f}".format)
        st.dataframe(display_ha, use_container_width=True, hide_index=True)

# --- Best Sportsbook ---
st.markdown("---")
col_book, col_recent = st.columns(2)

with col_book:
    st.subheader("🏆 Best Sportsbook for Underdog Prices")

    if "dog_best_book" in df.columns:
        book_counts = df["dog_best_book"].value_counts().reset_index()
        book_counts.columns = ["Sportsbook", "Times Best"]

        fig_book = px.bar(
            book_counts.head(8),
            x="Times Best", y="Sportsbook",
            orientation="h",
            color_discrete_sequence=["#4CAF50"],
        )
        fig_book.update_layout(
            height=350,
            margin=dict(l=40, r=20, t=20, b=40),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_book, use_container_width=True)

# --- Recent Results ---
with col_recent:
    st.subheader("📋 Recent Results")

    recent = resolved_sorted.tail(10).iloc[::-1]
    display_recent = recent[["date", "underdog", "dog_odds_best", "bucket", "dog_won", "profit"]].copy()
    display_recent["date"] = display_recent["date"].dt.strftime("%m/%d")
    display_recent.columns = ["Date", "Underdog", "Odds", "Bucket", "Won?", "P/L"]
    display_recent["Odds"] = display_recent["Odds"].map(lambda x: f"+{x:.0f}")
    display_recent["Won?"] = display_recent["Won?"].map({True: "✅", False: "❌"})
    display_recent["P/L"] = display_recent["P/L"].map(lambda x: f"${x:+,.2f}")

    st.dataframe(display_recent, use_container_width=True, hide_index=True)

# --- Pending Games ---
if len(pending) > 0:
    st.markdown("---")
    st.subheader(f"⏳ Pending Games ({len(pending)})")
    display_pending = pending[["date", "underdog", "dog_odds_best", "favorite", "bucket", "dog_best_book"]].copy()
    display_pending.columns = ["Date", "Underdog", "Odds", "Favorite", "Bucket", "Best Book"]
    display_pending["Odds"] = display_pending["Odds"].map(lambda x: f"+{x:.0f}" if pd.notna(x) else "")
    st.dataframe(display_pending, use_container_width=True, hide_index=True)

# --- Footer ---
st.markdown("---")
st.caption(
    f"📊 Tracking since {df['date'].min().strftime('%Y-%m-%d') if pd.notna(df['date'].min()) else 'N/A'} "
    f"• {total_games} total games • Data from The Odds API"
)
