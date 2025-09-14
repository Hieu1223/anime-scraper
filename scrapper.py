import os
import json
import logging
import requests
from lxml import html
from tqdm import tqdm

# --- Config ---
BASE_URL = "https://wibu47.com"
STATE_FILE = "state.json"
INDEX_FILE = "animes.json"
ANIME_DIR = "animes"
MAX_PAGE = 193

os.makedirs(ANIME_DIR, exist_ok=True)

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("scraper.log", encoding="utf-8", mode="w"),
        logging.StreamHandler()
    ]
)

# --- State ---
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"page": 0, "anime_idx": 0, "anime_id": 0}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

# --- Anime Index ---
def load_index():
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_index(index):
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

# --- Utils ---
def get_page_link(page: int):
    return f"{BASE_URL}/the-loai/anime?page={page}"

def parse_anime_article(article):
    data = {}
    link = article.xpath('.//a/@href')
    data['link'] = BASE_URL + link[0] if link else None
    img = article.xpath('.//img[contains(@class,"wp-post-image")]/@src')
    data['thumbnail'] = img[0] if img else None
    episode = article.xpath('.//span[@class="mli-eps"]/text()')
    data['episode'] = episode[0].strip() if episode else None
    rating = article.xpath('.//div[contains(@class,"anime-avg-user-rating")]/text()')
    data['rating'] = rating[0].strip() if rating else None
    title = article.xpath('.//h2[@class="Title"]/text()')
    data['title'] = title[0].strip() if title else None
    views = article.xpath('.//span[@class="Year"]/text()')
    data['views'] = views[0].replace('Lượt xem:', '').strip() if views else None
    info = article.xpath('.//p[@class="Info"]')
    if info:
        info = info[0]
        q = info.xpath('.//span[@class="Qlty"]/text()')
        v = info.xpath('.//span[contains(@class,"Vote")]/text()')
        t = info.xpath('.//span[contains(@class,"Time")]/text()')
        d = info.xpath('.//span[contains(@class,"Date")]/text()')
        data['quality'] = q[0].strip() if q else None
        data['vote'] = v[0].strip() if v else None
        data['time'] = t[0].strip() if t else None
        data['date'] = d[0].strip() if d else None
    else:
        data['quality'] = data['vote'] = data['time'] = data['date'] = None
    desc = article.xpath('.//div[@class="Description"]/p[1]/text()')
    data['description'] = desc[0].strip() if desc else None
    genre = article.xpath('.//p[contains(@class,"Genre")]/span/text()')
    data['genre'] = genre[0].replace('Thể loại:', '').strip() if genre else None
    return data

def get_animes_in_page(page):
    return page.find_class("TPost C post-943 post type-post status-publish format-standard has-post-thumbnail hentry")

# --- Main ---
def main():
    state = load_state()
    index = load_index()

    for page_num in range(state["page"], MAX_PAGE):
        try:
            page_html = requests.get(get_page_link(page_num)).text
            page = html.fromstring(page_html)
            animes = get_animes_in_page(page)
        except Exception as e:
            logging.error(f"Failed to fetch page {page_num+1}: {e}")
            break

        for idx in tqdm(range(state["anime_idx"], len(animes)), desc=f"Page {page_num+1}", unit="anime"):
            anime = animes[idx]
            info = parse_anime_article(anime)

            if not info.get("title"):
                continue

            # Skip duplicate by checking title in index
            if any(entry["title"] == info["title"] for entry in index.values()):
                logging.info(f"Skipping duplicate: {info['title']}")
            else:
                state["anime_id"] += 1
                anime_id = str(state["anime_id"])
                filename = os.path.join(ANIME_DIR, f"{anime_id}.json")

                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(info, f, ensure_ascii=False, indent=2)

                index[anime_id] = {"title": info["title"], "file": f"{anime_id}.json"}
                save_index(index)
                logging.info(f"Saved [{anime_id}]: {info['title']}")

            # update state after each anime
            state["page"] = page_num
            state["anime_idx"] = idx + 1
            save_state(state)

        # reset anime index, move to next page
        state["anime_idx"] = 0
        state["page"] = page_num + 1
        save_state(state)

if __name__ == "__main__":
    main()
