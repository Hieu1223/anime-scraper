import json
from lxml import html
import re
import requests


def get_page_link(page: int):
    return f"https://wibu47.com/the-loai/anime?page={page}"


def extract_mirrors(tree):
    scripts = tree.xpath('//script')
    pattern = r'var\s+(\w+)\s*=\s*"((?:https?://)[^"]+)"'
    result = {}
    for script in scripts:
        script_text = script.text or ""
        for var, url in re.findall(pattern, script_text):
            result[var] = url
    return result


base_url = "https://wibu47.com"


def parse_anime_article(article):
    data = {}

    link = article.xpath('.//a/@href')
    data['link'] = base_url + link[0] if link else None

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


def get_entry_point(info_page):
    panel = info_page.find_class("InfoList")[0]
    first_link = panel.xpath('//li[@class="AAIco-adjust latest_eps"]/a[@href]/@href')
    return first_link


def get_chapter_links(watch_page):
    panel = watch_page.find_class("list-episode tab-pane ABList")[0]
    links = panel.xpath('.//li/a[@href]')
    return [(a.text.strip() if a.text else '', base_url + a.get('href')) for a in links]


def get_watch_link(film_detail_url: str, chapter):
    return film_detail_url.replace("phim", "xem-phim") + str(chapter)


def get_valid_watch_link(links):
    for link in links:
        if link[-1] != '/':
            return link
    return None


def main():
    MAX_PAGE = 193
    exception = []
    episode_get_exception = []
    movies = []
    too_long_skip = []

    for page_num in range(MAX_PAGE):
        print(f"Processing page {page_num + 1}/{MAX_PAGE}")

        page = get_page_link(page_num)
        page = requests.get(page).text
        page = html.fromstring(page)
        animes = get_animes_in_page(page)

        for idx, anime in enumerate(animes):
            print(f"Anime {idx + 1}/{len(animes)} on page {page_num + 1}")
            info = parse_anime_article(anime)
            link = info['link']
            try:
                anime_page = requests.get(link).text
                anime_page = html.fromstring(anime_page)
                entry_points = get_entry_point(anime_page)
                entry_point = get_valid_watch_link(entry_points)
                if entry_point is None:
                    exception.append({"error": "no entry_point", "link": link})
                    continue

                entry_point = base_url + entry_point
                entry_point = requests.get(entry_point).text
                entry_point = html.fromstring(entry_point)
                chapter_links = get_chapter_links(entry_point)
                episodes = []

                for episode_num, watch_link in chapter_links:
                    episode = {}
                    print(f"Episode link: {watch_link}")
                    try:
                        watch_page = html.fromstring(requests.get(watch_link).text)
                        mirrors = extract_mirrors(watch_page)
                        episode["ep"] = episode_num
                        episode["mirrors"] = mirrors
                        episodes.append(episode)
                    except Exception as e:
                        print(f"Episode {episode_num} failed: {e}")
                        episode_get_exception.append(
                            {"error": str(e), "anime": link, "episode": episode_num}
                        )

                info['episodes'] = episodes
                movies.append(info)

                with open("movies.json", "w", encoding="utf-8") as f:
                    json.dump(movies, f, ensure_ascii=False, indent=2)

            except Exception as e:
                print(f"Anime failed: {e}")
                exception.append({"error": str(e), "link": link})


if __name__ == "__main__":
    main()
