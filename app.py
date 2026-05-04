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
import os
from datetime import datetime

# --- Page Config ---
st.set_page_config(
    page_title="MLB Underdog Tracker",
    page_icon="⚾",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Bucket definitions — mirrors config.py so the app is self-contained
# ---------------------------------------------------------------------------
NEW_BUCKETS = {
    "watch_low":   (131, 135),
    "slight":      (136, 150),
    "prime":       (151, 160),
    "moderate":    (161, 190),
    "heavy":       (191, 220),
    "very_heavy":  (241, 249),
    "watch_high":  (250, 260),
}

BUCKET_ORDER = ["watch_low", "slight", "prime", "moderate", "heavy", "very_heavy", "watch_high"]

BUCKET_LABELS = {
    "watch_low":   "Watch Low  (+131–135)",
    "slight":      "Slight  (+136–150)",
    "prime":       "Prime  (+151–160)",
    "moderate":    "Moderate  (+161–190)  ⚠️",
    "heavy":       "Heavy  (+191–220)",
    "very_heavy":  "Very Heavy  (+241–249)",
    "watch_high":  "Watch High  (+250–260)",
}

TRACK_ONLY = {"watch_low"}

DEFAULT_MULTIPLIERS = {
    "watch_low":   0.0,
    "slight":      1.0,
    "prime":       1.0,
    "moderate":    0.5,
    "heavy":       1.0,
    "very_heavy":  1.25,
    "watch_high":  1.0,
}

# ---------------------------------------------------------------------------
# Google Sheets loader
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300)
def load_data():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = None
    try:
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]), scopes=scopes
            )
    except Exception:
        pass

    if creds is None and os.path.exists("baseball-data_service_account.json"):
        creds = Credentials.from_service_account_file(
            "baseball-data_service_account.json", scopes=scopes
        )
    elif creds is None and os.path.exists("service_account.json"):
        creds = Credentials.from_service_account_file("service_account.json", scopes=scopes)

    if creds is None:
        st.error("No Google credentials found.")
        return pd.DataFrame()

    gc = gspread.authorize(creds)
    sheet_name = os.environ.get("SHEET_NAME", "MLB Underdog Tracker")
    try:
        sheet = gc.open(sheet_name).worksheet("Tracking")
    except gspread.SpreadsheetNotFound:
        st.error(f"Spreadsheet '{sheet_name}' not found.")
        return pd.DataFrame()

    data = sheet.get_all_records()
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)

    for col in ["dog_odds_best", "dog_odds_avg", "fav_odds_best", "fav_odds_avg", "num_books", "profit"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "home_is_dog" in df.columns:
        df["home_is_dog"] = df["home_is_dog"].astype(str).str.upper().isin(["TRUE", "1", "YES"])
    if "dog_won" in df.columns:
        df["dog_won"] = df["dog_won"].astype(str).str.upper().isin(["TRUE", "1", "YES"])
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    return df


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def break_even_rate(american_odds):
    if pd.isna(american_odds) or american_odds <= 0:
        return None
    return 1 / ((american_odds / 100) + 1)


def assign_new_bucket(odds):
    """Assign a game to the new bucket structure based on its odds."""
    for name, (lo, hi) in NEW_BUCKETS.items():
        if lo <= odds <= hi:
            return name
    return "out_of_range"


def recalc_profit(row, multipliers, base_unit):
    bucket = row.get("new_bucket", "out_of_range")
    unit = base_unit * multipliers.get(bucket, 0.0)
    if unit == 0:
        return 0.0
    if row["dog_won"]:
        return round(unit * (row["dog_odds_best"] / 100), 2)
    return -unit


def subrange_stats(df_resolved, step=5):
    """Compute W/L/P/L/ROI for every step-wide odds band that has data."""
    if df_resolved.empty:
        return pd.DataFrame()
    lo_floor = int(df_resolved["dog_odds_best"].min() // step * step)
    hi_ceil  = int(df_resolved["dog_odds_best"].max() // step * step) + step
    rows = []
    for lo in range(lo_floor, hi_ceil, step):
        hi = lo + step - 1
        sub = df_resolved[
            (df_resolved["dog_odds_best"] >= lo) &
            (df_resolved["dog_odds_best"] <= hi)
        ]
        if sub.empty:
            continue
        games   = len(sub)
        wins    = int(sub["dog_won"].sum())
        losses  = games - wins
        wr      = wins / games
        avg_o   = sub["dog_odds_best"].mean()
        be      = break_even_rate(avg_o) or 0
        pl      = float(sub["profit"].sum())
        wagered = games * 100
        rows.append({
            "Range": f"+{lo}–{hi}",
            "_lo": lo,
            "Games": games,
            "W": wins,
            "L": losses,
            "Win%": wr,
            "Break-Even": be,
            "Edge": wr - be,
            "P/L": pl,
            "ROI": pl / wagered * 100,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Load & split data
# ---------------------------------------------------------------------------
df = load_data()

st.title("⚾ MLB Underdog Tracker")
st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}  •  Click ↻ to refresh")

if df.empty:
    st.info("No data yet.")
    st.stop()

resolved = df[df["winner"].astype(str).str.len() > 0].copy()
pending  = df[df["winner"].astype(str).str.len() == 0].copy()

num_resolved = len(resolved)
num_pending  = len(pending)
total_games  = len(df)

if num_resolved > 0:
    wins     = int(resolved["dog_won"].sum())
    losses   = num_resolved - wins
    total_pl = float(resolved["profit"].sum())
    roi      = total_pl / (num_resolved * 100) * 100
else:
    wins = losses = 0
    total_pl = roi = 0.0

# Attach new bucket assignments to resolved (used by simulator & analysis)
if num_resolved > 0:
    resolved = resolved.copy()
    resolved["new_bucket"] = resolved["dog_odds_best"].apply(assign_new_bucket)

# ---------------------------------------------------------------------------
# Top metrics — always visible
# ---------------------------------------------------------------------------
st.markdown("---")
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Tracked", total_games)
c2.metric("Resolved", num_resolved)
c3.metric("Pending", num_pending)
c4.metric("Record", f"{wins}W – {losses}L")
c5.metric("Total P/L", f"${total_pl:+,.2f}")
c6.metric("ROI", f"{roi:+.1f}%")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_dash, tab_sim, tab_analysis = st.tabs([
    "📊 Dashboard",
    "⚖️ Unit Sizing Simulator",
    "🔬 Sub-Range Analysis",
])


# ===========================================================
# TAB 1 — Dashboard  (unchanged logic, uses stored bucket col)
# ===========================================================
with tab_dash:
    if num_resolved == 0:
        st.info("No resolved games yet — charts will appear once results come in.")
        if num_pending > 0:
            st.subheader("📋 Pending Games")
            st.dataframe(
                pending[["date", "underdog", "dog_odds_best", "favorite", "bucket", "dog_best_book"]],
                use_container_width=True, hide_index=True,
            )
    else:
        rs = resolved.sort_values("date").copy()
        rs["cum_profit"] = rs["profit"].cumsum()
        rs["bet_number"] = range(1, len(rs) + 1)

        # Cumulative P/L
        st.subheader("📈 Cumulative Profit/Loss")
        fig_pl = go.Figure()
        fig_pl.add_trace(go.Scatter(
            x=rs["bet_number"], y=rs["cum_profit"],
            mode="lines+markers",
            line=dict(color="#2196F3", width=2),
            marker=dict(
                size=8,
                color=rs["dog_won"].map({True: "#4CAF50", False: "#f44336"}),
            ),
            hovertext=rs.apply(
                lambda r: (
                    f"{r['underdog']} (+{r['dog_odds_best']:.0f})<br>"
                    f"{'WIN' if r['dog_won'] else 'Loss'}: ${r['profit']:+.2f}<br>"
                    f"Cumulative: ${r['cum_profit']:+.2f}"
                ), axis=1,
            ),
            hoverinfo="text",
        ))
        fig_pl.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig_pl.update_layout(
            xaxis_title="Bet #", yaxis_title="Cumulative P/L ($)",
            height=400, margin=dict(l=40, r=20, t=20, b=40),
        )
        st.plotly_chart(fig_pl, use_container_width=True)

        # Performance by bucket (uses stored bucket col — reflects live assignments)
        col_left, col_right = st.columns(2)
        with col_left:
            st.subheader("🪣 Performance by Bucket (new structure)")
            bkt_data = []
            for b in BUCKET_ORDER:
                sub = resolved[resolved["new_bucket"] == b]
                if sub.empty:
                    continue
                g  = len(sub)
                bw = int(sub["dog_won"].sum())
                bwr = bw / g
                avg_o = sub["dog_odds_best"].mean()
                be  = break_even_rate(avg_o) or 0
                bpl = float(sub["profit"].sum())
                label = b + (" 👁" if b in TRACK_ONLY else "")
                bkt_data.append({
                    "Bucket": label,
                    "Games": g, "W": bw, "L": g - bw,
                    "Win%": bwr, "Break-Even": be,
                    "Edge": bwr - be,
                    "P/L": bpl, "ROI": bpl / (g * 100) * 100,
                })

            if bkt_data:
                bdf = pd.DataFrame(bkt_data)
                fig_b = go.Figure()
                fig_b.add_trace(go.Bar(x=bdf["Bucket"], y=bdf["Win%"],
                    name="Actual Win%", marker_color="#2196F3"))
                fig_b.add_trace(go.Bar(x=bdf["Bucket"], y=bdf["Break-Even"],
                    name="Break-Even", marker_color="#FF9800", opacity=0.7))
                fig_b.update_layout(
                    barmode="group", yaxis_tickformat=".0%",
                    height=350, margin=dict(l=40, r=20, t=20, b=40),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02),
                )
                st.plotly_chart(fig_b, use_container_width=True)

                disp = bdf.copy()
                for col, fmt in [("Win%", "{:.1%}"), ("Break-Even", "{:.1%}"),
                                  ("Edge", "{:+.1%}"), ("P/L", "${:+,.2f}"),
                                  ("ROI", "{:+.1f}%")]:
                    disp[col] = disp[col].map(fmt.format)
                st.dataframe(disp, use_container_width=True, hide_index=True)

        with col_right:
            st.subheader("🏠 Home vs Away Underdogs")
            ha_data = []
            for label, is_home in [("Home Dog", True), ("Away Dog", False)]:
                sub = resolved[resolved["home_is_dog"] == is_home]
                if sub.empty:
                    continue
                g = len(sub)
                hw = int(sub["dog_won"].sum())
                ha_data.append({
                    "Type": label, "Games": g,
                    "W": hw, "L": g - hw,
                    "Win%": hw / g, "P/L": float(sub["profit"].sum()),
                })
            if ha_data:
                hadf = pd.DataFrame(ha_data)
                fig_ha = go.Figure()
                fig_ha.add_trace(go.Bar(
                    x=hadf["Type"], y=hadf["Win%"],
                    marker_color=["#4CAF50", "#2196F3"],
                    text=hadf["Win%"].map(lambda x: f"{x:.1%}"),
                    textposition="auto",
                ))
                fig_ha.update_layout(
                    yaxis_tickformat=".0%", height=350,
                    margin=dict(l=40, r=20, t=20, b=40),
                )
                st.plotly_chart(fig_ha, use_container_width=True)
                disp_ha = hadf.copy()
                disp_ha["Win%"] = disp_ha["Win%"].map("{:.1%}".format)
                disp_ha["P/L"]  = disp_ha["P/L"].map("${:+,.2f}".format)
                st.dataframe(disp_ha, use_container_width=True, hide_index=True)

        # Best book + Recent results
        st.markdown("---")
        col_book, col_recent = st.columns(2)
        with col_book:
            st.subheader("🏆 Best Sportsbook for Underdog Prices")
            if "dog_best_book" in df.columns:
                bc = df["dog_best_book"].value_counts().reset_index()
                bc.columns = ["Sportsbook", "Times Best"]
                fig_bk = px.bar(bc.head(8), x="Times Best", y="Sportsbook",
                    orientation="h", color_discrete_sequence=["#4CAF50"])
                fig_bk.update_layout(height=350, margin=dict(l=40,r=20,t=20,b=40),
                    yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig_bk, use_container_width=True)

        with col_recent:
            st.subheader("📋 Recent Results")
            recent = rs.tail(10).iloc[::-1].copy()
            recent["date"] = recent["date"].dt.strftime("%m/%d")
            recent = recent[["date","underdog","dog_odds_best","new_bucket","dog_won","profit"]]
            recent.columns = ["Date","Underdog","Odds","Bucket","Won?","P/L"]
            recent["Odds"] = recent["Odds"].map(lambda x: f"+{x:.0f}")
            recent["Won?"] = recent["Won?"].map({True: "✅", False: "❌"})
            recent["P/L"]  = recent["P/L"].map(lambda x: f"${x:+,.2f}")
            st.dataframe(recent, use_container_width=True, hide_index=True)

        if num_pending > 0:
            st.markdown("---")
            st.subheader(f"⏳ Pending Games ({num_pending})")
            pp = pending[["date","underdog","dog_odds_best","favorite","bucket","dog_best_book"]].copy()
            pp.columns = ["Date","Underdog","Odds","Favorite","Bucket","Best Book"]
            pp["Odds"] = pp["Odds"].map(lambda x: f"+{x:.0f}" if pd.notna(x) else "")
            st.dataframe(pp, use_container_width=True, hide_index=True)


# ===========================================================
# TAB 2 — Unit Sizing Simulator  (uses new bucket structure)
# ===========================================================
with tab_sim:
    st.header("⚖️ Unit Sizing Simulator")
    st.markdown(
        "Replay resolved bets using **new bucket assignments** and custom unit sizes. "
        "Buckets marked 👁 are track-only (default $0). "
        "Adjust sliders to test sizing strategies."
    )

    if num_resolved == 0:
        st.info("No resolved games yet.")
    else:
        active_new = [b for b in BUCKET_ORDER if b in resolved["new_bucket"].values]

        inp_col, _, res_col = st.columns([1, 0.1, 2])

        with inp_col:
            st.subheader("Settings")
            base_unit = st.number_input(
                "Base Unit ($)", min_value=1, max_value=10000, value=100, step=10,
                help="1 unit = this dollar amount.",
            )
            st.markdown("**Multiplier per Bucket**")
            st.caption("0 = no wager  •  1.0 = 1 unit  •  1.5 = 1.5 units")

            multipliers = {}
            for b in BUCKET_ORDER:
                default = DEFAULT_MULTIPLIERS.get(b, 1.0)
                label   = BUCKET_LABELS.get(b, b)
                if b in active_new:
                    multipliers[b] = st.slider(
                        label, min_value=0.0, max_value=3.0,
                        value=float(default), step=0.25, key=f"sim_{b}",
                    )
                else:
                    multipliers[b] = default
                    st.caption(f"{label}: no data yet")

        # Recalculate
        sim = resolved.copy()
        sim["unit_size"]   = sim["new_bucket"].map(multipliers).fillna(0.0) * base_unit
        sim["sim_profit"]  = sim.apply(lambda r: recalc_profit(r, multipliers, base_unit), axis=1)

        orig_wagered = num_resolved * 100
        sim_wagered  = float(sim["unit_size"].sum())
        orig_pl      = float(resolved["profit"].sum())
        sim_pl       = float(sim["sim_profit"].sum())
        orig_roi     = orig_pl / orig_wagered * 100 if orig_wagered else 0
        sim_roi      = sim_pl  / sim_wagered  * 100 if sim_wagered  else 0

        with res_col:
            st.subheader("Overall Impact")
            m1, m2, m3 = st.columns(3)
            m1.metric("Flat $100 P/L",  f"${orig_pl:+,.2f}")
            m2.metric("Custom P/L",     f"${sim_pl:+,.2f}",      delta=f"${sim_pl - orig_pl:+,.2f}")
            m3.metric("Total Wagered",  f"${sim_wagered:,.0f}",  delta=f"${sim_wagered - orig_wagered:+,.0f}")
            r1, r2, r3 = st.columns(3)
            r1.metric("Flat ROI",    f"{orig_roi:+.1f}%")
            r2.metric("Custom ROI",  f"{sim_roi:+.1f}%",  delta=f"{sim_roi - orig_roi:+.1f}%")
            r3.metric("Avg Unit $",  f"${sim_wagered / num_resolved:,.0f}" if num_resolved else "—")

        st.markdown("---")

        # Per-bucket breakdown
        st.subheader("By-Bucket Breakdown")
        comp = []
        for b in BUCKET_ORDER:
            sub_o = resolved[resolved["new_bucket"] == b]
            sub_s = sim[sim["new_bucket"] == b]
            if sub_o.empty:
                continue
            g       = len(sub_o)
            bw      = int(sub_o["dog_won"].sum())
            orig_bpl = float(sub_o["profit"].sum())
            sim_bpl  = float(sub_s["sim_profit"].sum())
            orig_bw  = g * 100
            sim_bw   = float(sub_s["unit_size"].sum())
            unit_amt = base_unit * multipliers.get(b, 0.0)
            comp.append({
                "Bucket":     BUCKET_LABELS.get(b, b),
                "Games":      g,
                "W-L":        f"{bw}-{g-bw}",
                "Unit $":     f"${unit_amt:.0f}",
                "Flat P/L":   f"${orig_bpl:+,.2f}",
                "Custom P/L": f"${sim_bpl:+,.2f}",
                "Flat ROI":   f"{orig_bpl/orig_bw*100:+.1f}%",
                "Custom ROI": f"{sim_bpl/sim_bw*100:+.1f}%" if sim_bw else "—",
                "Net Δ":      f"${sim_bpl - orig_bpl:+,.2f}",
            })
        if comp:
            st.dataframe(pd.DataFrame(comp), use_container_width=True, hide_index=True)

        # Cumulative comparison chart
        st.subheader("📈 Cumulative P/L: Flat vs. Custom")
        ss = sim.sort_values("date").reset_index(drop=True)
        ss["cum_flat"]   = ss["profit"].cumsum()
        ss["cum_custom"] = ss["sim_profit"].cumsum()
        ss["bet_num"]    = range(1, len(ss) + 1)

        fig_c = go.Figure()
        fig_c.add_trace(go.Scatter(
            x=ss["bet_num"], y=ss["cum_flat"],
            mode="lines", name="Flat $100",
            line=dict(color="#9E9E9E", width=2, dash="dash"),
        ))
        fig_c.add_trace(go.Scatter(
            x=ss["bet_num"], y=ss["cum_custom"],
            mode="lines", name="Custom Sizing",
            line=dict(color="#2196F3", width=2.5),
            fill="tonexty", fillcolor="rgba(33,150,243,0.07)",
        ))
        fig_c.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.4)
        fig_c.update_layout(
            xaxis_title="Bet #", yaxis_title="Cumulative P/L ($)",
            height=420, margin=dict(l=40, r=20, t=20, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig_c, use_container_width=True)

        with st.expander("Game-by-game detail"):
            det = sim.sort_values("date")[
                ["date","underdog","dog_odds_best","new_bucket","dog_won",
                 "profit","unit_size","sim_profit"]
            ].copy()
            det["date"]       = det["date"].dt.strftime("%m/%d")
            det["dog_won"]    = det["dog_won"].map({True: "✅", False: "❌"})
            det["dog_odds_best"] = det["dog_odds_best"].map(lambda x: f"+{x:.0f}")
            det["profit"]     = det["profit"].map(lambda x: f"${x:+,.2f}")
            det["sim_profit"] = det["sim_profit"].map(lambda x: f"${x:+,.2f}")
            det["unit_size"]  = det["unit_size"].map(lambda x: f"${x:.0f}")
            det.columns = ["Date","Underdog","Odds","Bucket","Won?",
                           "Flat P/L","Unit $","Custom P/L"]
            st.dataframe(det, use_container_width=True, hide_index=True)


# ===========================================================
# TAB 3 — Sub-Range Analysis
# ===========================================================
with tab_analysis:
    st.header("🔬 Sub-Range Analysis")
    st.markdown(
        "Performance by exact 5-unit odds bands — updated live from the sheet. "
        "Use **Time Period** to slice by recent weeks. "
        "Green = positive edge, red = negative."
    )

    if num_resolved == 0:
        st.info("No resolved games yet.")
    else:
        # Controls
        ctrl_left, ctrl_right = st.columns([1, 2])
        with ctrl_left:
            period = st.selectbox(
                "Time Period",
                ["All Time", "Last 30 Days", "Last 14 Days", "Last 7 Days"],
                index=0,
            )
        with ctrl_right:
            step = st.radio(
                "Band Width",
                [5, 10],
                index=0,
                horizontal=True,
                help="Width of each odds band in the table and chart.",
            )

        # Filter by period
        adf = resolved.copy()
        if period != "All Time":
            n_days = int(period.split()[1])
            cutoff = pd.Timestamp.now() - pd.Timedelta(days=n_days)
            adf = adf[adf["date"] >= cutoff]

        if adf.empty:
            st.info("No resolved games in the selected time period.")
        else:
            rdf = subrange_stats(adf, step=step)

            if rdf.empty:
                st.info("Not enough data to compute sub-range stats.")
            else:
                # --- ROI bar chart ---
                colors = ["#4CAF50" if r > 0 else "#f44336" for r in rdf["ROI"]]
                fig_roi = go.Figure()
                fig_roi.add_trace(go.Bar(
                    x=rdf["Range"],
                    y=rdf["ROI"],
                    marker_color=colors,
                    text=rdf.apply(lambda r: f"{r['W']}-{r['L']}", axis=1),
                    textposition="outside",
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        "ROI: %{y:.1f}%<br>"
                        "Record: %{text}<extra></extra>"
                    ),
                ))
                fig_roi.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
                fig_roi.update_layout(
                    title=f"ROI by {step}-Unit Odds Band  ({period})",
                    xaxis_title="Odds Range",
                    yaxis_title="ROI (%)",
                    height=440,
                    margin=dict(l=40, r=20, t=50, b=40),
                )
                st.plotly_chart(fig_roi, use_container_width=True)

                # --- Win% vs Break-Even chart ---
                fig_wr = go.Figure()
                fig_wr.add_trace(go.Bar(
                    x=rdf["Range"], y=rdf["Win%"],
                    name="Actual Win%", marker_color="#2196F3",
                ))
                fig_wr.add_trace(go.Scatter(
                    x=rdf["Range"], y=rdf["Break-Even"],
                    name="Break-Even needed", mode="lines+markers",
                    line=dict(color="#FF9800", width=2, dash="dot"),
                    marker=dict(size=6),
                ))
                fig_wr.update_layout(
                    title=f"Win% vs Break-Even  ({period})",
                    xaxis_title="Odds Range",
                    yaxis_title="Win Rate",
                    yaxis_tickformat=".0%",
                    height=380,
                    margin=dict(l=40, r=20, t=50, b=40),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02),
                )
                st.plotly_chart(fig_wr, use_container_width=True)

                # --- Summary table ---
                st.subheader("Detailed Table")
                disp = rdf.drop(columns=["_lo"]).copy()
                disp["Win%"]       = disp["Win%"].map("{:.1%}".format)
                disp["Break-Even"] = disp["Break-Even"].map("{:.1%}".format)
                disp["Edge"]       = disp["Edge"].map("{:+.1%}".format)
                disp["P/L"]        = disp["P/L"].map("${:+,.2f}".format)
                disp["ROI"]        = disp["ROI"].map("{:+.1f}%".format)
                st.dataframe(disp, use_container_width=True, hide_index=True)

                # --- Cumulative P/L by range (top vs bottom performers) ---
                st.markdown("---")
                st.subheader("📅 Cumulative P/L — Top vs Bottom Ranges")
                st.caption(
                    "Select two ranges to compare how they've trended over time. "
                    "Useful for seeing whether a bad range is improving."
                )

                range_options = rdf["Range"].tolist()
                if len(range_options) >= 2:
                    c_a, c_b = st.columns(2)
                    with c_a:
                        range_a = st.selectbox("Range A", range_options,
                            index=0, key="range_a")
                    with c_b:
                        range_b = st.selectbox("Range B", range_options,
                            index=min(1, len(range_options)-1), key="range_b")

                    def cum_for_range(r_label, step_val, df_in):
                        lo = int(r_label.split("+")[1].split("–")[0])
                        hi = lo + step_val - 1
                        sub = df_in[
                            (df_in["dog_odds_best"] >= lo) &
                            (df_in["dog_odds_best"] <= hi)
                        ].sort_values("date").copy()
                        if sub.empty:
                            return pd.DataFrame()
                        sub["cum_pl"] = sub["profit"].cumsum()
                        sub["bet_n"]  = range(1, len(sub) + 1)
                        return sub

                    sa = cum_for_range(range_a, step, adf)
                    sb = cum_for_range(range_b, step, adf)

                    fig_cmp = go.Figure()
                    if not sa.empty:
                        fig_cmp.add_trace(go.Scatter(
                            x=sa["bet_n"], y=sa["cum_pl"],
                            mode="lines+markers", name=range_a,
                            line=dict(color="#4CAF50", width=2),
                        ))
                    if not sb.empty:
                        fig_cmp.add_trace(go.Scatter(
                            x=sb["bet_n"], y=sb["cum_pl"],
                            mode="lines+markers", name=range_b,
                            line=dict(color="#f44336", width=2),
                        ))
                    fig_cmp.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.4)
                    fig_cmp.update_layout(
                        xaxis_title="Bet # within range",
                        yaxis_title="Cumulative P/L ($)",
                        height=380,
                        margin=dict(l=40, r=20, t=20, b=40),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02),
                    )
                    st.plotly_chart(fig_cmp, use_container_width=True)


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.caption(
    f"📊 Tracking since {df['date'].min().strftime('%Y-%m-%d') if pd.notna(df['date'].min()) else 'N/A'} "
    f"• {total_games} total games • Data from The Odds API"
)
