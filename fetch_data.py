import os
import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

import requests
from requests import Session
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

API_KEY: Optional[str] = os.getenv("CRICKETDATA_API_KEY")
if not API_KEY:
    raise ValueError("CRICKETDATA_API_KEY not set in environment or .env file.")

# Base URLs
SEARCH_URL = "https://api.cricapi.com/v1/players"
INFO_URL = "https://api.cricapi.com/v1/players_info"

# Players list
PLAYERS_LIST: List[str] = [
    "Don Bradman", "Sachin Tendulkar", "Garfield Sobers", "Imran Khan", "Ian Botham",
    "Shane Warne", "Viv Richards", "Brian Lara", "Jaques Kallis", "MS Dhoni",
    "Wasim Akram", "Virat Kohli", "James Anderson", "Alastair Cook", "Muttiah Muralitharan",
    "Kumar Sangakkara", "Kapil Dev", "Richard Hadlee", "Adam Gilchrist", "Chris Gayle",
    "Glenn McGrath", "Ricky Ponting", "Steve Waugh", "Rahul Dravid", "Sunil Gavaskar",
    "Shoaib Akhtar", "Curtly Ambrose", "Mahela Jayawardene", "Dale Steyn", "Allan Donald"
]

OUTPUT_FILE = Path("players_data.json")

def make_request(session: Session, url: str, params: Dict[str, Any], retries: int = 3, backoff: int = 2) -> Dict[str, Any]:
    """Generic request with retry and backoff."""
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logging.warning(f"Request failed (attempt {attempt}/{retries}): {e}")
            if attempt < retries:
                time.sleep(backoff ** attempt)
            else:
                raise
    return {}

def get_player_id(session: Session, player_name: str) -> Optional[str]:
    """Fetch player ID by name."""
    data = make_request(session, SEARCH_URL, {"apikey": API_KEY, "search": player_name})
    if data.get("data"):
        return data["data"][0].get("id")
    return None

def get_player_info(session: Session, player_id: str) -> Dict[str, Any]:
    """Fetch full player info."""
    return make_request(session, INFO_URL, {"apikey": API_KEY, "id": player_id})

def main() -> None:
    players_data: List[Dict[str, Any]] = []
    
    with requests.Session() as session:
        for player in PLAYERS_LIST:
            try:
                logging.info(f"Fetching ID for {player}...")
                pid = get_player_id(session, player)
                if pid:
                    logging.info(f" → Found ID: {pid}, fetching stats...")
                    info = get_player_info(session, pid)
                    players_data.append(info)
                else:
                    logging.warning(f" ✗ No ID found for {player}")
            except Exception as e:
                logging.error(f"Error fetching {player}: {e}", exc_info=True)
    
    # Save raw data
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(players_data, f, indent=2, ensure_ascii=False)
    
    logging.info(f"All player data saved to {OUTPUT_FILE.absolute()}")

if __name__ == "__main__":
    main()
