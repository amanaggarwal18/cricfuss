import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px

# DB function
def get_data(query, params=()):
    conn = sqlite3.connect("cricket.db")
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

st.set_page_config(page_title="Cricket Player Stats", layout="wide")

st.title("🏏 Cricket Player Stats Explorer")

# Sidebar filters
players = get_data("SELECT player_id, player_name FROM players_stats")
player_choice = st.sidebar.selectbox("Select Player", players["player_name"])
player_id = players.loc[players["player_name"] == player_choice, "player_id"].iloc[0]

# Fetch selected player details
player = get_data("SELECT * FROM players_stats WHERE player_id=?", (player_id,))
player = player.iloc[0]

# Profile card
col1, col2 = st.columns([1, 2])
with col1:
    st.image(player["player_image"], caption=player["player_name"], width=200)
with col2:
    st.subheader(player["player_name"])
    st.write(f"**DOB:** {player['player_dateofbirth']}")
    st.write(f"**Role:** {player['player_role']}")
    st.write(f"**Batting Style:** {player['player_battingstyle']}")
    st.write(f"**Bowling Style:** {player['player_bowlingstyle']}")
    st.write(f"**Place of Birth:** {player['player_placeofbirth']}")
    st.write(f"**Country:** {player['player_country']}")

# Tabs for stats
tab1, tab2 = st.tabs(["📊 Batting Stats", "🎯 Bowling Stats"])

# ---------- Batting Stats ----------
with tab1:
    st.markdown("### Batting Summary")

    formats = ["Test", "ODI", "T20I", "IPL"]
    batting_data = []
    for fmt in formats:
        runs = player[f"batting_{fmt.lower()}_total_runs"]
        avg = player[f"batting_{fmt.lower()}_average"]
        sr = player[f"batting_{fmt.lower()}_strike_rate"]
        hs = player[f"batting_{fmt.lower()}_highest_score"]
        batting_data.append([fmt, runs, avg, sr, hs])
    df_bat = pd.DataFrame(batting_data, columns=["Format", "Runs", "Average", "Strike Rate", "Highest Score"])
    st.dataframe(df_bat, use_container_width=True)

    # Chart
    fig = px.bar(df_bat, x="Format", y="Runs", text="Runs", title="Runs by Format")
    st.plotly_chart(fig, use_container_width=True)

# ---------- Bowling Stats ----------
with tab2:
    st.markdown("### Bowling Summary")

    formats = ["Test", "ODI", "T20I", "IPL"]
    bowling_data = []
    for fmt in formats:
        wkts = player[f"bowling_{fmt.lower()}_wickets"]
        avg = player[f"bowling_{fmt.lower()}_average"]
        econ = player[f"bowling_{fmt.lower()}_econ"]
        sr = player[f"bowling_{fmt.lower()}_strike_rate"]
        best = player[f"bowling_{fmt.lower()}_best_bowling_inning"]
        bowling_data.append([fmt, wkts, avg, econ, sr, best])
    df_bowl = pd.DataFrame(bowling_data, columns=["Format", "Wickets", "Average", "Econ", "Strike Rate", "Best Inning"])
    st.dataframe(df_bowl, use_container_width=True)

    # Chart
    fig2 = px.bar(df_bowl, x="Format", y="Wickets", text="Wickets", title="Wickets by Format")
    st.plotly_chart(fig2, use_container_width=True)
