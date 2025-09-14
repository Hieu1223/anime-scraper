import os
import json
import logging

# --- Config ---
ANIME_DIR = "animes"
OUTPUT_FILE = "all_animes.json"

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("merge_phase3.log", encoding="utf-8", mode="w"),
              logging.StreamHandler()]
)

def fix_episodes(anime):
    """Sort episodes by number and remove invalid entries."""
    if "episodes" not in anime or not anime["episodes"]:
        return []

    ep_dict = {}
    for ep in anime["episodes"]:
        try:
            ep_num = int(ep.get("ep", 0)) if ep.get("ep") else 0
            if ep_num > 0:
                ep_dict[ep_num] = ep
        except:
            continue

    # Sorted list of episodes
    fixed_episodes = [ep_dict[num] for num in sorted(ep_dict)]
    return fixed_episodes

def main():
    merged_data = []

    anime_files = sorted(os.listdir(ANIME_DIR))
    logging.info(f"Found {len(anime_files)} anime files.")

    for filename in anime_files:
        filepath = os.path.join(ANIME_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                anime = json.load(f)

                # Fix episodes list
                anime["episodes"] = fix_episodes(anime)

                # Replace "episode" field with actual count
                anime["episode"] = str(len(anime["episodes"]))

                merged_data.append(anime)
                logging.info(f"Added {anime.get('title', 'UNKNOWN')} with {len(anime['episodes'])} episodes.")
        except Exception as e:
            logging.error(f"Failed to load {filename}: {e}")

    # Save the merged JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2)
    
    logging.info(f"Successfully saved merged data to {OUTPUT_FILE}.")

if __name__ == "__main__":
    main()
