import json
import logging
import sqlite3

# --- Config ---
INPUT_FILE = "all_animes.json"
DB_FILE = "animes.db"

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("sql_import.log", encoding="utf-8", mode="w"),
              logging.StreamHandler()]
)

def create_tables(conn):
    """Create tables for animes and episodes."""
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS animes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            link TEXT,
            thumbnail TEXT,
            description TEXT,
            genre TEXT,
            rating TEXT,
            views TEXT,
            quality TEXT,
            vote TEXT,
            time TEXT,
            date TEXT,
            episode_count INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anime_id INTEGER,
            ep_number INTEGER,
            mirrors TEXT,
            FOREIGN KEY(anime_id) REFERENCES animes(id)
        )
    """)
    conn.commit()

def main():
    # Load merged JSON
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            all_animes = json.load(f)
    except Exception as e:
        logging.error(f"Failed to load {INPUT_FILE}: {e}")
        return

    logging.info(f"Loaded {len(all_animes)} animes from {INPUT_FILE}.")

    conn = sqlite3.connect(DB_FILE)
    create_tables(conn)
    c = conn.cursor()

    for anime in all_animes:
        try:
            episode_count = len(anime.get("episodes", []))

            # Insert anime
            c.execute("""
                INSERT INTO animes (title, link, thumbnail, description, genre, rating, views, quality, vote, time, date, episode_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                anime.get("title"),
                anime.get("link"),
                anime.get("thumbnail"),
                anime.get("description"),
                anime.get("genre"),
                anime.get("rating"),
                anime.get("views"),
                anime.get("quality"),
                anime.get("vote"),
                anime.get("time"),
                anime.get("date"),
                episode_count
            ))
            anime_id = c.lastrowid

            # Insert episodes
            for ep_idx, ep in enumerate(anime.get("episodes", []), 1):
                mirrors_json = json.dumps(ep.get("mirrors", {}), ensure_ascii=False)
                c.execute("""
                    INSERT INTO episodes (anime_id, ep_number, mirrors)
                    VALUES (?, ?, ?)
                """, (anime_id, ep_idx, mirrors_json))

            logging.info(f"Inserted {anime.get('title', 'UNKNOWN')} with {episode_count} episodes.")

        except Exception as e:
            logging.error(f"Failed to insert anime {anime.get('title', 'UNKNOWN')}: {e}")

    conn.commit()
    conn.close()
    logging.info(f"Successfully saved all data into {DB_FILE}.")

if __name__ == "__main__":
    main()
