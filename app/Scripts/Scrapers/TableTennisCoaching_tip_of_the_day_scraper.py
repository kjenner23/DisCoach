# Scrape_TipofTheDay.py
# TableTennisCoaching.com — Tip Of The Week archive
# Iterate ?page=0..N, extract each post (title + full body) from the index pages,
# and write ChatGPT-ready blocks with source_url set to the /node/#### link.

import time
import sys
from datetime import date
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

# ========= CONFIG =========
BASE_INDEX = "http://www.tabletenniscoaching.com/TipOfTheWeek?page={n}"

# Politeness / HTTP
PAUSE_SECONDS = 0.8
TIMEOUT = 20
UA = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Output
OUTPUT_PATH = "ttc_tip_of_the_week_for_gpt.txt"

# Limits (for quick tests)
MAX_PAGES = None   # e.g., 3 for smoke tests; None = crawl until empty page
DEBUG = False

ALLOWED = {"tabletenniscoaching.com", "www.tabletenniscoaching.com"}


# ========= HELPERS =========
def is_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in ALLOWED or host == ""  # allow relative


def get_soup(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=UA, timeout=TIMEOUT, allow_redirects=True)
    r.raise_for_status()
    s = BeautifulSoup(r.text, "html.parser")
    # Trim obvious chrome
    for junk in s.select("nav, footer, script, style, form, aside"):
        junk.decompose()
    return s


def textify(el: Tag) -> str:
    """Flatten nested tags/spans to clean text with line breaks preserved."""
    return el.get_text("\n", strip=True)


def collect_posts_from_index(page_n: int):
    """
    Return a list of dicts: {title, node_url, body_text} found on page_n.
    Uses only the index page, which contains full article text.
    """
    url = BASE_INDEX.format(n=page_n)
    soup = get_soup(url)

    rows = soup.select("div.view-content div.views-row")
    posts = []
    for row in rows:
        # Title + canonical link (/node/####)
        a = row.select_one("div.views-field.views-field-title h1.field-content a[href]")
        if not a:
            # occasional variant: try h2
            a = row.select_one("div.views-field.views-field-title h2.field-content a[href]")
        if not a:
            if DEBUG:
                print(f"[DEBUG] No title link on page {page_n}")
            continue

        node_href = a["href"].strip()
        node_url = urljoin(url, node_href)
        if not is_allowed(node_url):
            continue

        title = a.get_text(strip=True)

        # Full body lives in views-field-body > div.field-content
        body_container = row.select_one("div.views-field.views-field-body div.field-content")
        if not body_container:
            # Fallbacks for legacy posts
            body_container = row.select_one("div.views-field.views-field-body")
        if not body_container:
            # Last-ditch: try a generic content block within the row
            body_container = row

        body_text = textify(body_container).strip()
        if not body_text:
            if DEBUG:
                print(f"[DEBUG] Empty body on {node_url}")
            continue

        posts.append({
            "title": title,
            "node_url": node_url,
            "body_text": body_text
        })

    return posts


# ========= MAIN =========
def main():
    today = date.today().isoformat()
    seen_urls = set()
    written = 0
    page_n = 0

    with open(OUTPUT_PATH, "w", encoding="utf-8") as out:
        while True:
            if isinstance(MAX_PAGES, int) and page_n >= MAX_PAGES:
                break

            index_url = BASE_INDEX.format(n=page_n)
            try:
                posts = collect_posts_from_index(page_n)
            except Exception as e:
                print(f"[ERROR] index page {page_n} ({index_url}) -> {e}")
                break

            if not posts:
                # Clean stop: no posts found on this page number
                if DEBUG:
                    print(f"[DEBUG] No posts on page {page_n}; stopping.")
                break

            for i, p in enumerate(posts, 1):
                if p["node_url"] in seen_urls:
                    if DEBUG:
                        print(f"[DEBUG] Duplicate URL (skipping): {p['node_url']}")
                    continue
                seen_urls.add(p["node_url"])

                try:
                    body = (p["body_text"] or "").strip()
                    if not body:
                        print(f"{page_n:03d}:{i:02d}  SKIP (no body)  {p['node_url']}")
                        continue

                    out.write("===ARTICLE===\n")
                    out.write(f"source_url: {p['node_url']}\n")
                    out.write(f"title: {p['title'] or 'Unknown'}\n")
                    out.write(f"date_accessed: {today}\n")
                    out.write("TEXT:\n")
                    out.write(body + "\n\n")

                    print(f"{page_n:03d}:{i:02d}  OK  {p['title'][:80]}")
                    written += 1
                except Exception as e:
                    print(f"{page_n:03d}:{i:02d}  ERROR  {p['node_url']} -> {e}")
                time.sleep(PAUSE_SECONDS)

            page_n += 1
            time.sleep(PAUSE_SECONDS)

    print(f"\nWrote {written} articles to {OUTPUT_PATH}")


if __name__ == "__main__":
    # Optional: `python3 Scrape_TipofTheDay.py --debug`
    if len(sys.argv) > 1 and sys.argv[1] == "--debug":
        DEBUG = True
    main()
