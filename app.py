import sqlite3
from contextlib import closing
from typing import List, Sequence, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
DB_PATH = "cricket.db"
FORMATS: List[str] = ["Test", "ODI", "T20I", "IPL"]

BATTING_STAT_COLS: List[Tuple[str, str]] = [
    ("total_runs", "Runs"),
    ("average", "Average"),
    ("strike_rate", "Strike Rate"),
    ("highest_score", "Highest Score"),
    ("matches", "Matches"),
    ("innings", "Innings"),
    ("not_outs", "Not Outs"),
    ("100s", "100s"),
    ("50s", "50s"),
    ("4s", "4s"),
    ("6s", "6s"),
]

BOWLING_STAT_COLS: List[Tuple[str, str]] = [
    ("wickets", "Wickets"),
    ("average", "Average"),
    ("econ", "Economy"),
    ("strike_rate", "Strike Rate"),
    ("best_bowling_inning", "Best Inning"),
    ("matches", "Matches"),
    ("innings", "Innings"),
    ("five_wickets", "5W"),
    ("ten_wickets", "10W"),
]

FORMAT_COLORS = {
    "Test": "#e74c3c",
    "ODI": "#3498db",
    "T20I": "#2ecc71",
    "IPL": "#f39c12",
}


# ──────────────────────────────────────────────
# Database helpers
# ──────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def query_db(query: str, params: Sequence = ()) -> pd.DataFrame:
    """Run a read-only query and return a DataFrame. Cached for 10 min."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        return pd.read_sql_query(query, conn, params=params)


@st.cache_data(ttl=600, show_spinner=False)
def get_player_list() -> pd.DataFrame:
    """Return (player_id, player_name) sorted alphabetically."""
    return query_db(
        "SELECT player_id, player_name FROM players_stats ORDER BY player_name"
    )


# ──────────────────────────────────────────────
# Stat-extraction helpers
# ──────────────────────────────────────────────
def _safe_val(player: pd.Series, col: str) -> str:
    """Return the column value or '—' if the column is missing / None."""
    val = player.get(col)
    if val is None or (isinstance(val, str) and val.strip() == ""):
        return "—"
    return str(val).strip()


def _to_numeric(val: str) -> float:
    """Best-effort cast to float; return 0.0 on failure."""
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def build_stat_table(
    player: pd.Series,
    role: str,
    stat_cols: List[Tuple[str, str]],
) -> pd.DataFrame:
    """
    Build a per-format stats DataFrame.

    Parameters
    ----------
    player : pd.Series – single-player row from the database.
    role   : 'batting' or 'bowling'.
    stat_cols : list of (db_suffix, display_name) pairs.
    """
    rows = []
    for fmt in FORMATS:
        prefix = f"{role}_{fmt.lower()}_"
        row = {"Format": fmt}
        for db_suffix, display in stat_cols:
            row[display] = _safe_val(player, f"{prefix}{db_suffix}")
        rows.append(row)
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────
# Page configuration & CSS
# ──────────────────────────────────────────────
st.set_page_config(page_title="CricFuss – Player Stats", layout="wide")

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* Global */
html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
.block-container { padding-top: 1.5rem; }

/* Profile Card */
.profile-card {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    border-radius: 18px; padding: 2rem; color: #fff;
    box-shadow: 0 8px 32px rgba(0,0,0,.35);
}
.profile-card h1 { margin: 0 0 .3rem; font-size: 2rem; font-weight: 800; }
.profile-card .role-badge {
    display: inline-block; padding: 4px 14px; border-radius: 20px;
    font-size: .78rem; font-weight: 600; letter-spacing: .5px;
    background: rgba(255,255,255,.15); backdrop-filter: blur(4px);
    margin-bottom: 1rem;
}
.info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 24px; }
.info-item { font-size: .88rem; color: rgba(255,255,255,.85); }
.info-item strong { color: rgba(255,255,255,.55); font-weight: 500; font-size: .78rem;
    text-transform: uppercase; letter-spacing: .5px; display: block; margin-bottom: 1px; }

/* Player image */
.player-img-wrap {
    display: flex; align-items: center; justify-content: center; height: 100%;
}
.player-img-wrap img {
    width: 180px; height: 180px; object-fit: cover;
    border-radius: 50%; border: 4px solid rgba(255,255,255,.25);
    box-shadow: 0 4px 20px rgba(0,0,0,.4);
}

/* KPI metric cards */
.kpi-row { display: flex; gap: 12px; flex-wrap: wrap; margin: 1rem 0 1.2rem; }
.kpi-card {
    flex: 1 1 130px; padding: 16px 18px; border-radius: 14px;
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    border: 1px solid rgba(255,255,255,.08);
    box-shadow: 0 2px 12px rgba(0,0,0,.2); text-align: center; color: #fff;
}
.kpi-card .kpi-val { font-size: 1.6rem; font-weight: 800; }
.kpi-card .kpi-label {
    font-size: .72rem; text-transform: uppercase; letter-spacing: .8px;
    color: rgba(255,255,255,.5); margin-top: 2px;
}

/* Styled table */
.styled-table { width: 100%; border-collapse: separate; border-spacing: 0;
    border-radius: 12px; overflow: hidden; font-size: .88rem;
    box-shadow: 0 2px 12px rgba(0,0,0,.15); margin: .5rem 0 1.2rem; }
.styled-table thead th {
    background: linear-gradient(135deg, #0f0c29, #302b63);
    color: #fff; padding: 12px 14px; font-weight: 600; text-align: center;
    letter-spacing: .3px; font-size: .8rem; text-transform: uppercase;
}
.styled-table tbody td { padding: 10px 14px; text-align: center; border-bottom: 1px solid rgba(0,0,0,.06); }
.styled-table tbody tr:nth-child(even) { background: rgba(0,0,0,.025); }
.styled-table tbody tr:hover { background: rgba(48,43,99,.08); }
.format-badge {
    display: inline-block; padding: 3px 10px; border-radius: 6px;
    font-weight: 600; font-size: .78rem; color: #fff;
}

/* Section header */
.section-hdr {
    font-size: 1.15rem; font-weight: 700; margin: .5rem 0 .2rem;
    padding-bottom: 6px; border-bottom: 3px solid #302b63;
    display: inline-block;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] {
    border-radius: 10px 10px 0 0; padding: 10px 28px;
    font-weight: 600; font-size: .92rem;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(
    "<h2 style='text-align:center;margin-bottom:.2rem'>🏏 CricFuss</h2>"
    "<p style='text-align:center;color:gray;margin-top:0;font-size:.9rem'>"
    "Professional Cricket Player Statistics</p>",
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────
# Sidebar – player selector
# ──────────────────────────────────────────────
players = get_player_list()
if players.empty:
    st.error("No players found in the database.")
    st.stop()

player_choice = st.sidebar.selectbox("Select Player", players["player_name"])
player_id = players.loc[
    players["player_name"] == player_choice, "player_id"
].iloc[0]

# ──────────────────────────────────────────────
# Fetch selected player (cached)
# ──────────────────────────────────────────────
player_df = query_db(
    "SELECT * FROM players_stats WHERE player_id = ?", (player_id,)
)
if player_df.empty:
    st.warning("Player data not found.")
    st.stop()

player = player_df.iloc[0]


# ──────────────────────────────────────────────
# Helper: render an HTML table from a DataFrame
# ──────────────────────────────────────────────
def render_html_table(df: pd.DataFrame) -> str:
    header = "".join(f"<th>{c}</th>" for c in df.columns)
    rows_html = ""
    for _, row in df.iterrows():
        cells = ""
        for col in df.columns:
            val = row[col]
            if col == "Format":
                bg = FORMAT_COLORS.get(val, "#555")
                cells += f'<td><span class="format-badge" style="background:{bg}">{val}</span></td>'
            else:
                cells += f"<td>{val}</td>"
        rows_html += f"<tr>{cells}</tr>"
    return f'<table class="styled-table"><thead><tr>{header}</tr></thead><tbody>{rows_html}</tbody></table>'


def make_chart(df, x, y_col, text_col, title, y_title):
    """Build a polished Plotly bar chart."""
    colors = [FORMAT_COLORS.get(f, "#888") for f in df["Format"]]
    fig = go.Figure(
        go.Bar(
            x=df[x], y=df[y_col], text=df[text_col],
            textposition="outside", marker_color=colors,
            marker_line_width=0, opacity=0.92,
        )
    )
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, family="Inter")),
        yaxis_title=y_title,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=13),
        margin=dict(t=50, b=40, l=50, r=20),
        yaxis=dict(gridcolor="rgba(0,0,0,.07)", zeroline=False),
        xaxis=dict(showgrid=False),
        height=350,
    )
    return fig


# ──────────────────────────────────────────────
# Profile card
# ──────────────────────────────────────────────
img_url = _safe_val(player, "player_image")
img_html = ""
if img_url != "—":
    img_html = f'<div class="player-img-wrap"><img src="{img_url}" alt="player"></div>'

role = _safe_val(player, "player_role")
info_pairs = [
    ("Date of Birth", "player_dateofbirth"),
    ("Batting Style", "player_battingstyle"),
    ("Bowling Style", "player_bowlingstyle"),
    ("Birthplace", "player_placeofbirth"),
    ("Country", "player_country"),
]
info_html = ""
for label, key in info_pairs:
    info_html += f'<div class="info-item"><strong>{label}</strong>{_safe_val(player, key)}</div>'

col_img, col_info = st.columns([1, 3])
with col_img:
    st.markdown(img_html, unsafe_allow_html=True)
with col_info:
    st.markdown(
        f"""<div class="profile-card">
        <h1>{player["player_name"]}</h1>
        <span class="role-badge">{role}</span>
        <div class="info-grid">{info_html}</div>
        </div>""",
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Stats tabs
# ──────────────────────────────────────────────
tab_bat, tab_bowl = st.tabs(["📊 Batting Stats", "🎯 Bowling Stats"])


def _kpi_html(cards: list) -> str:
    inner = ""
    for val, label, accent in cards:
        inner += (
            f'<div class="kpi-card">'
            f'<div class="kpi-val" style="color:{accent}">{val}</div>'
            f'<div class="kpi-label">{label}</div></div>'
        )
    return f'<div class="kpi-row">{inner}</div>'


# ────── Batting ──────
with tab_bat:
    df_bat = build_stat_table(player, "batting", BATTING_STAT_COLS)

    # Aggregate KPIs across all formats
    total_runs = sum(_to_numeric(v) for v in df_bat["Runs"])
    total_matches = sum(_to_numeric(v) for v in df_bat["Matches"])
    best_avg = max((_to_numeric(v) for v in df_bat["Average"]), default=0)
    total_100s = sum(_to_numeric(v) for v in df_bat["100s"])
    #total_50s = sum(_to_numeric(v) for v in df_bat["50s"])

    st.markdown(
        _kpi_html([
            (f"{int(total_runs):,}", "Total Runs", "#f1c40f"),
            (str(int(total_matches)), "Matches", "#3498db"),
            (f"{best_avg:.2f}", "Best Average", "#2ecc71"),
            (str(int(total_100s)), "Centuries", "#e74c3c"),
            # (str(int(total_50s)), "Half-Centuries", "#9b59b6"),
        ]),
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-hdr">Format-wise Breakdown</div>', unsafe_allow_html=True)
    st.markdown(render_html_table(df_bat), unsafe_allow_html=True)

    df_bat["_Runs"] = df_bat["Runs"].apply(_to_numeric)
    st.plotly_chart(
        make_chart(df_bat, "Format", "_Runs", "Runs", "Runs by Format", "Runs"),
        use_container_width=True,
    )

# ────── Bowling ──────
with tab_bowl:
    df_bowl = build_stat_table(player, "bowling", BOWLING_STAT_COLS)

    total_wkts = sum(_to_numeric(v) for v in df_bowl["Wickets"])
    total_m = sum(_to_numeric(v) for v in df_bowl["Matches"])
    best_econ = min((_to_numeric(v) for v in df_bowl["Economy"] if _to_numeric(v) > 0), default=0)
    total_5w = sum(_to_numeric(v) for v in df_bowl["5W"])

    st.markdown(
        _kpi_html([
            (str(int(total_wkts)), "Total Wickets", "#e74c3c"),
            (str(int(total_m)), "Matches", "#3498db"),
            (f"{best_econ:.2f}" if best_econ else "—", "Best Economy", "#2ecc71"),
            (str(int(total_5w)), "5-Wicket Hauls", "#f39c12"),
        ]),
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-hdr">Format-wise Breakdown</div>', unsafe_allow_html=True)
    st.markdown(render_html_table(df_bowl), unsafe_allow_html=True)

    df_bowl["_Wickets"] = df_bowl["Wickets"].apply(_to_numeric)
    st.plotly_chart(
        make_chart(df_bowl, "Format", "_Wickets", "Wickets", "Wickets by Format", "Wickets"),
        use_container_width=True,
    )
