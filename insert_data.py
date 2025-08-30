import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

# --------------------------------------------------
# Config
# --------------------------------------------------
JSON_PATH = Path("players_data.json")
DB_PATH = Path("cricket.db")
TABLE_NAME = "players_stats"

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

# --------------------------------------------------
# Mappings
# --------------------------------------------------
STAT_MAPPING = {
    "50": "50s", "100": "100s", "200": "200s",
    "50s": "50s", "100s": "100s", "200s": "200s",
    "6s": "6s", "4s": "4s",
    "10w": "ten_wickets", "5w": "five_wickets",
    "bbi": "best_bowling_inning", "bbm": "best_bowling_match",
    "sr": "strike_rate", "avg": "average", "hs": "highest_score",
    "m": "matches", "inn": "innings", "no": "not_outs",
    "wkts": "wickets", "eco": "economy", "b": "balls",
    "bf": "balls_faced", "runs": "total_runs"
}

MATCHTYPE_MAPPING = {
    "odi": "odi", "test": "test", "t20": "t20i", "t20i": "t20i", "ipl": "ipl"
}

PLAYER_FIELDS = [
    ("id", "player_id"),
    ("name", "player_name"),
    ("dateOfBirth", "player_dateofbirth"),
    ("role", "player_role"),
    ("battingStyle", "player_battingstyle"),
    ("bowlingStyle", "player_bowlingstyle"),
    ("placeOfBirth", "player_placeofbirth"),
    ("country", "player_country"),
    ("playerImg", "player_image"),
]

# --------------------------------------------------
# Data Processing
# --------------------------------------------------
def load_json(path: Path) -> List[Dict[str, Any]]:
    """Load JSON file."""
    if not path.exists():
        logging.error(f"JSON file not found: {path}")
        return []
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_players(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize raw JSON player data into flat dicts."""
    all_players: List[Dict[str, Any]] = []

    for player in data:
        pdata = player.get("data", {})

        # Core fields
        player_data = {alias: pdata.get(field) for field, alias in PLAYER_FIELDS}

        # Stats
        for stats in pdata.get("stats", []):
            role = stats.get("fn", "").strip().lower()
            matchtype = MATCHTYPE_MAPPING.get(stats.get("matchtype", "").strip().lower())
            stat = STAT_MAPPING.get(stats.get("stat", "").strip().lower())
            value = stats.get("value")

            if role and matchtype and stat:
                col = f"{role}_{matchtype}_{stat}"
                player_data[col] = value

        all_players.append(player_data)

    return all_players


# --------------------------------------------------
# Database Functions
# --------------------------------------------------
def infer_sql_type(value: Any) -> str:
    """Infer SQLite column type from a Python value."""
    if isinstance(value, int):
        return "INTEGER"
    elif isinstance(value, float):
        return "REAL"
    return "TEXT"


def create_table(cursor: sqlite3.Cursor, table: str, sample_row: Dict[str, Any]) -> None:
    """Create table dynamically from sample row."""
    col_defs = [
        f'"{col}" {infer_sql_type(val)}' for col, val in sample_row.items()
    ]
    create_sql = f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(col_defs)});'
    cursor.execute(create_sql)


def insert_rows(conn: sqlite3.Connection, table: str, rows: List[Dict[str, Any]]) -> None:
    """Insert rows into SQLite table."""
    if not rows:
        logging.warning("No rows to insert.")
        return

    columns = list(rows[0].keys())
    placeholders = ", ".join(["?"] * len(columns))
    quoted_cols = ", ".join([f'"{c}"' for c in columns])

    insert_sql = f'INSERT INTO "{table}" ({quoted_cols}) VALUES ({placeholders});'
    values = [[row.get(col) for col in columns] for row in rows]

    cursor = conn.cursor()
    create_table(cursor, table, rows[0])
    cursor.executemany(insert_sql, values)
    conn.commit()

    logging.info(f"Inserted {len(rows)} rows into {DB_PATH} -> table {table}.")


# --------------------------------------------------
# Main Workflow
# --------------------------------------------------
def main():
    raw_data = load_json(JSON_PATH)
    players = normalize_players(raw_data)

    if not players:
        logging.warning("No player data found.")
        return

    with sqlite3.connect(DB_PATH) as conn:
        insert_rows(conn, TABLE_NAME, players)


if __name__ == "__main__":
    main()
