import os
import json
import logging
import requests
from lxml import html
from tqdm import tqdm

# --- Config ---
BASE_URL = "https://wibu47.com"
ANIME_DIR = "animes"
STATE_FILE = "state_phase2.json"

os.makedirs(ANIME_DIR, exist_ok=True)

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("scraper_phase2.log", encoding="utf-8", mode="w"),
        logging.StreamHandler()
    ]
)

# --- State ---
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"anime_idx": 0, "episode_idx": 0}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

# --- Utils ---
def extract_mirrors(tree):
    scripts = tree.xpath('//script')
    pattern = r'var\s+(\w+)\s*=\s*"((?:https?://)[^"]+)"'
    import re
    result = {}
    for script in scripts:
        script_text = script.text or ""
        for var, url in re.findall(pattern, script_text):
            result[var] = url
    return result

def get_entry_point(info_page):
    panel = info_page.find_class("InfoList")[0]
    return panel.xpath('//li[@class="AAIco-adjust latest_eps"]/a[@href]/@href')

def get_chapter_links(watch_page):
    panel = watch_page.find_class("list-episode tab-pane ABList")[0]
    links = panel.xpath('.//li/a[@href]')
    return [(a.text.strip() if a.text else '', BASE_URL + a.get('href')) for a in links]

def get_valid_watch_link(links):
    for link in links:
        if link and link[-1] != '/':
            return link
    return None

# --- Main Phase 2 ---
def main():
    state = load_state()
    anime_files = sorted(os.listdir(ANIME_DIR))

    for anime_idx in range(state["anime_idx"], len(anime_files)):
        filename = anime_files[anime_idx]
        filepath = os.path.join(ANIME_DIR, filename)

        with open(filepath, "r", encoding="utf-8") as f:
            anime = json.load(f)

        # skip already processed animes
        if "episodes" in anime and anime["episodes"]:
            logging.info(f"Skipping already scraped anime: {anime['title']}")
            continue

        link = anime.get("link")
        if not link:
            logging.warning(f"No link for anime {anime.get('title', 'UNKNOWN')}")
            continue

        logging.info(f"Scraping episodes for anime: {anime['title']}")

        try:
            anime_page = html.fromstring(requests.get(link).text)
            entry_points = get_entry_point(anime_page)
            entry_point = get_valid_watch_link(entry_points)
            if not entry_point:
                logging.warning(f"No entry point for {anime['title']}")
                continue

            entry_html = requests.get(BASE_URL + entry_point).text
            entry_page = html.fromstring(entry_html)
            chapter_links = get_chapter_links(entry_page)

            episodes = []
            for ep_idx in tqdm(range(state["episode_idx"], len(chapter_links)),
                               desc=f"Episodes {anime['title']}", unit="ep"):
                ep_num, watch_link = chapter_links[ep_idx]
                episode = {"ep": ep_num, "mirrors": {}}

                try:
                    watch_page = html.fromstring(requests.get(watch_link).text)
                    mirrors = extract_mirrors(watch_page)
                    episode["mirrors"] = mirrors
                    logging.info(f"Saved episode {ep_num} of {anime['title']}")
                except Exception as e:
                    logging.error(f"Episode {ep_num} failed for {anime['title']}: {e}")

                episodes.append(episode)

                # update state after each episode
                state["anime_idx"] = anime_idx
                state["episode_idx"] = ep_idx + 1
                save_state(state)

            anime["episodes"] = episodes

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(anime, f, ensure_ascii=False, indent=2)

            # reset episode index after finishing one anime
            state["anime_idx"] = anime_idx + 1
            state["episode_idx"] = 0
            save_state(state)

        except Exception as e:
            logging.error(f"Failed to scrape anime {anime['title']}: {e}")
            continue

if __name__ == "__main__":
    main()
