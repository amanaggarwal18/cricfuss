import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="CricFuss | Player Stats", layout="wide", page_icon="🏏")

FORMATS = ["Test", "ODI", "T20I", "IPL"]
FORMAT_COLORS = {"Test": "#636EFA", "ODI": "#EF553B", "T20I": "#00CC96", "IPL": "#AB63FA"}

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=30, b=20, l=10, r=10),
    xaxis=dict(showgrid=False),
    yaxis=dict(gridcolor="rgba(200,200,200,0.15)"),
    font=dict(family="Arial"),
)

st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; }
[data-testid="stMetricLabel"] { font-size: 0.8rem; color: #888; }
.section-label { font-size: 0.75rem; font-weight: 600; color: #888;
                 text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
</style>
""", unsafe_allow_html=True)

# ─── Data layer ───────────────────────────────────────────────────────────────
@st.cache_data
def load_player_list() -> pd.DataFrame:
    with sqlite3.connect("cricket.db") as conn:
        return pd.read_sql_query(
            "SELECT player_id, player_name, player_country, player_role FROM players_stats", conn
        )

@st.cache_data
def load_player(player_id: str) -> pd.Series:
    with sqlite3.connect("cricket.db") as conn:
        df = pd.read_sql_query(
            "SELECT * FROM players_stats WHERE player_id=?", conn, params=(player_id,)
        )
    return df.iloc[0]

# ─── Helpers ──────────────────────────────────────────────────────────────────
def _num(val, cast=float):
    try:
        return cast(float(str(val).replace("*", ""))) if val not in (None, "", "N/A", "-") else cast(0)
    except (ValueError, TypeError):
        return cast(0)

def build_batting_df(player: pd.Series, formats: list) -> pd.DataFrame:
    rows = []
    for fmt in formats:
        f = fmt.lower()
        rows.append({
            "Format": fmt,
            "Matches": _num(player.get(f"batting_{f}_matches"), int),
            "Runs": _num(player.get(f"batting_{f}_total_runs"), int),
            "Average": _num(player.get(f"batting_{f}_average")),
            "Strike Rate": _num(player.get(f"batting_{f}_strike_rate")),
            "Highest Score": player.get(f"batting_{f}_highest_score") or "-",
            "50s": _num(player.get(f"batting_{f}_50s"), int),
            "100s": _num(player.get(f"batting_{f}_100s"), int),
        })
    return pd.DataFrame(rows)

def build_bowling_df(player: pd.Series, formats: list) -> pd.DataFrame:
    rows = []
    for fmt in formats:
        f = fmt.lower()
        rows.append({
            "Format": fmt,
            "Matches": _num(player.get(f"bowling_{f}_matches"), int),
            "Wickets": _num(player.get(f"bowling_{f}_wickets"), int),
            "Average": _num(player.get(f"bowling_{f}_average")),
            "Economy": _num(player.get(f"bowling_{f}_econ")),
            "Strike Rate": _num(player.get(f"bowling_{f}_strike_rate")),
            "Best Inning": player.get(f"bowling_{f}_best_bowling_inning") or "-",
            "5W": _num(player.get(f"bowling_{f}_five_wickets"), int),
        })
    return pd.DataFrame(rows)

def normalize_for_radar(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    out = df[cols].copy().astype(float)
    for c in cols:
        mx = out[c].max()
        out[c] = out[c] / mx if mx > 0 else 0.0
    return out

def radar_chart(df: pd.DataFrame, normed: pd.DataFrame, categories: list, display_cats: list) -> go.Figure:
    fig = go.Figure()
    theta = display_cats + [display_cats[0]]
    for i, row in df.iterrows():
        r_vals = [normed.loc[i, c] for c in categories] + [normed.loc[i, categories[0]]]
        fig.add_trace(go.Scatterpolar(
            r=r_vals, theta=theta, fill="toself",
            name=row["Format"],
            line_color=FORMAT_COLORS.get(row["Format"], "#888"),
            opacity=0.75,
        ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=False, range=[0, 1])),
        showlegend=True, height=300,
        margin=dict(t=20, b=10, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=-0.15),
    )
    return fig

def bar_chart(df: pd.DataFrame, y: str, text_fmt: str = "%d", title: str = "") -> go.Figure:
    fig = px.bar(df, x="Format", y=y, text=y, color="Format",
                 color_discrete_map=FORMAT_COLORS, title=title)
    fig.update_traces(texttemplate=text_fmt, textposition="outside", marker_line_width=0, opacity=0.9)
    fig.update_layout(showlegend=False, **CHART_LAYOUT)
    return fig

def grouped_bar(df1, df2, y, name1, name2) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df1["Format"], y=df1[y], name=name1,
                         marker_color="#636EFA", text=df1[y], textposition="outside"))
    fig.add_trace(go.Bar(x=df2["Format"], y=df2[y], name=name2,
                         marker_color="#EF553B", text=df2[y], textposition="outside"))
    fig.update_layout(barmode="group", **CHART_LAYOUT)
    return fig

# ─── Sidebar ──────────────────────────────────────────────────────────────────
players_df = load_player_list()

with st.sidebar:
    st.markdown("## 🏏 CricFuss")
    st.divider()

    player_choice = st.selectbox("Select Player", players_df["player_name"])

    selected_formats = st.multiselect("Formats", FORMATS, default=FORMATS)

    st.divider()
    compare_mode = st.toggle("Compare two players")
    if compare_mode:
        others = players_df.loc[players_df["player_name"] != player_choice, "player_name"]
        player_choice_2 = st.selectbox("Compare with", others)
    else:
        player_choice_2 = None

    st.divider()
    st.caption("Data via CricAPI")

if not selected_formats:
    st.warning("Select at least one format to continue.")
    st.stop()

# ─── Load player data ─────────────────────────────────────────────────────────
pid = players_df.loc[players_df["player_name"] == player_choice, "player_id"].iloc[0]
player = load_player(pid)

player2 = None
if compare_mode and player_choice_2:
    pid2 = players_df.loc[players_df["player_name"] == player_choice_2, "player_id"].iloc[0]
    player2 = load_player(pid2)

# ─── Profile header ───────────────────────────────────────────────────────────
col_img, col_bio, col_highlights = st.columns([1, 2, 2])

with col_img:
    st.image(player["player_image"], use_container_width=True)

with col_bio:
    st.markdown(f"### {player['player_name']}")
    bio_fields = [
        ("🗓️ DOB", "player_dateofbirth"),
        ("🌍 Country", "player_country"),
        ("👤 Role", "player_role"),
        ("🏏 Batting", "player_battingstyle"),
        ("🎯 Bowling", "player_bowlingstyle"),
        ("📍 Born in", "player_placeofbirth"),
    ]
    for label, key in bio_fields:
        val = player.get(key) or "N/A"
        st.markdown(f"**{label}:** {val}")

with col_highlights:
    st.markdown('<p class="section-label">Career Highlights (all formats)</p>', unsafe_allow_html=True)
    total_runs = sum(_num(player.get(f"batting_{f.lower()}_total_runs"), int) for f in FORMATS)
    total_wkts = sum(_num(player.get(f"bowling_{f.lower()}_wickets"), int) for f in FORMATS)
    total_100s = sum(_num(player.get(f"batting_{f.lower()}_100s"), int) for f in FORMATS)
    total_5w   = sum(_num(player.get(f"bowling_{f.lower()}_five_wickets"), int) for f in FORMATS)

    m1, m2 = st.columns(2)
    m1.metric("Total Runs", f"{total_runs:,}")
    m2.metric("Total Wickets", f"{total_wkts:,}")
    m3, m4 = st.columns(2)
    m3.metric("Centuries", total_100s)
    m4.metric("5-Wicket Hauls", total_5w)

    if compare_mode and player2 is not None:
        st.divider()
        st.markdown(f'<p class="section-label">{player_choice_2} highlights</p>', unsafe_allow_html=True)
        r2 = sum(_num(player2.get(f"batting_{f.lower()}_total_runs"), int) for f in FORMATS)
        w2 = sum(_num(player2.get(f"bowling_{f.lower()}_wickets"), int) for f in FORMATS)
        c2 = sum(_num(player2.get(f"batting_{f.lower()}_100s"), int) for f in FORMATS)
        n1, n2 = st.columns(2)
        n1.metric("Total Runs", f"{r2:,}", delta=f"{r2 - total_runs:+,}", delta_color="normal")
        n2.metric("Total Wickets", f"{w2:,}", delta=f"{w2 - total_wkts:+,}", delta_color="normal")
        n3, n4 = st.columns(2)
        n3.metric("Centuries", c2, delta=c2 - total_100s, delta_color="normal")
        n4.metric("5-Wicket Hauls", sum(_num(player2.get(f"bowling_{f.lower()}_five_wickets"), int) for f in FORMATS))

st.divider()

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📊 Batting", "🎯 Bowling"])

# ── Batting tab ───────────────────────────────────────────────────────────────
with tab1:
    df_bat = build_batting_df(player, selected_formats)
    df_bat2 = build_batting_df(player2, selected_formats) if player2 is not None else None

    left, right = st.columns([3, 2])

    with left:
        max_runs = int(df_bat["Runs"].max()) if df_bat["Runs"].max() > 0 else 1000
        st.dataframe(
            df_bat,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Format":       st.column_config.TextColumn("🏟️ Format"),
                "Matches":      st.column_config.NumberColumn("M", format="%d"),
                "Runs":         st.column_config.ProgressColumn("🏏 Runs", format="%d", min_value=0, max_value=max_runs + 500),
                "Average":      st.column_config.NumberColumn("📊 Avg", format="%.2f"),
                "Strike Rate":  st.column_config.NumberColumn("⚡ SR", format="%.2f"),
                "Highest Score":st.column_config.TextColumn("🔥 HS"),
                "50s":          st.column_config.NumberColumn("🥈 50s", format="%d"),
                "100s":         st.column_config.NumberColumn("💯 100s", format="%d"),
            },
        )

    with right:
        bat_cats = ["Runs", "Average", "Strike Rate", "50s", "100s"]
        normed = normalize_for_radar(df_bat, bat_cats)
        st.plotly_chart(
            radar_chart(df_bat, normed, bat_cats, bat_cats),
            use_container_width=True,
        )

    st.markdown("#### Runs & Average by Format")
    c1, c2 = st.columns(2)
    with c1:
        if compare_mode and df_bat2 is not None:
            st.plotly_chart(grouped_bar(df_bat, df_bat2, "Runs", player_choice, player_choice_2), use_container_width=True)
        else:
            st.plotly_chart(bar_chart(df_bat, "Runs", title="Runs by Format"), use_container_width=True)
    with c2:
        if compare_mode and df_bat2 is not None:
            st.plotly_chart(grouped_bar(df_bat, df_bat2, "Average", player_choice, player_choice_2), use_container_width=True)
        else:
            st.plotly_chart(bar_chart(df_bat, "Average", text_fmt="%.1f", title="Average by Format"), use_container_width=True)

# ── Bowling tab ───────────────────────────────────────────────────────────────
with tab2:
    df_bowl = build_bowling_df(player, selected_formats)
    df_bowl2 = build_bowling_df(player2, selected_formats) if player2 is not None else None

    left, right = st.columns([3, 2])

    with left:
        max_wkts = int(df_bowl["Wickets"].max()) if df_bowl["Wickets"].max() > 0 else 100
        st.dataframe(
            df_bowl,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Format":      st.column_config.TextColumn("🏟️ Format"),
                "Matches":     st.column_config.NumberColumn("M", format="%d"),
                "Wickets":     st.column_config.ProgressColumn("🎯 Wickets", format="%d", min_value=0, max_value=max_wkts + 50),
                "Average":     st.column_config.NumberColumn("📊 Avg", format="%.2f"),
                "Economy":     st.column_config.NumberColumn("💰 Econ", format="%.2f"),
                "Strike Rate": st.column_config.NumberColumn("⚡ SR", format="%.2f"),
                "Best Inning": st.column_config.TextColumn("🔥 Best"),
                "5W":          st.column_config.NumberColumn("⭐ 5W", format="%d"),
            },
        )

    with right:
        # Economy: lower = better, so invert for radar
        radar_df = df_bowl.copy()
        radar_df["Econ (inv)"] = radar_df["Economy"].apply(lambda x: 1 / x if x > 0 else 0.0)
        bowl_cats = ["Wickets", "5W", "Econ (inv)"]
        display = ["Wickets", "5-Wkts", "Economy"]
        normed_b = normalize_for_radar(radar_df, bowl_cats)
        st.plotly_chart(
            radar_chart(df_bowl, normed_b, bowl_cats, display),
            use_container_width=True,
        )

    st.markdown("#### Wickets & Economy by Format")
    c1, c2 = st.columns(2)
    with c1:
        if compare_mode and df_bowl2 is not None:
            st.plotly_chart(grouped_bar(df_bowl, df_bowl2, "Wickets", player_choice, player_choice_2), use_container_width=True)
        else:
            st.plotly_chart(bar_chart(df_bowl, "Wickets", title="Wickets by Format"), use_container_width=True)
    with c2:
        # Economy vs Strike Rate scatter
        valid = df_bowl[(df_bowl["Economy"] > 0) | (df_bowl["Strike Rate"] > 0)]
        if not valid.empty:
            fig_sc = px.scatter(
                valid, x="Economy", y="Strike Rate", text="Format", color="Format",
                color_discrete_map=FORMAT_COLORS, title="Economy vs Strike Rate",
                size_max=18,
            )
            fig_sc.update_traces(textposition="top center", marker=dict(size=14, opacity=0.85))
            fig_sc.update_layout(
                showlegend=False,
                xaxis_title="Economy Rate",
                yaxis_title="Strike Rate",
                xaxis=dict(showgrid=True, gridcolor="rgba(200,200,200,0.15)"),
                **{k: v for k, v in CHART_LAYOUT.items() if k not in ("xaxis", "yaxis")},
            )
            st.plotly_chart(fig_sc, use_container_width=True)
        else:
            st.info("No bowling data available for scatter chart.")