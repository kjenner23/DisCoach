# scrape_many.py
# PingSkills: find blog post links -> fetch page -> write ChatGPT-ready blocks.

import time, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import date

# === SITE SETTINGS ===
INDEX_URL      = "https://www.pingskills.com/blog"
POST_LINKS_CSS = "div.regular-blogs a[href^='/blog/']"  # anchors inside the blog grid
ALLOWED_PATH_PREFIX = "/blog/"                           # keep only real blog posts

# Article page selectors
TITLE_CSS = "h1.text-center, h1"
# Key change: target the content block(s) under the title, not the nav container
BODY_CSS  = "div.container .mb-3, article, main"

# Politeness + limits
PAUSE_SECONDS = 1.2
MAX_LINKS = None                  # set None when you're happy with results
OUTPUT_PATH = "batch_for_gpt.txt"

BLOCKED_DOMAINS = {
    "youtube.com", "www.youtube.com", "youtu.be",
    "twitter.com", "x.com",
    "facebook.com", "www.facebook.com",
    "instagram.com", "www.instagram.com"
}

def get_soup(url: str) -> BeautifulSoup:
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    s = BeautifulSoup(r.text, "html.parser")
    # 1) Remove boilerplate so we don't accidentally read nav/footer text
    for junk in s.select("nav, header, footer, script, style, form, aside"):
        junk.decompose()
    return s

def is_blocked(url: str) -> bool:
    host = urlparse(url).hostname or ""
    if host in BLOCKED_DOMAINS: return True
    if "youtube.com" in host or "youtu.be" in host: return True
    return False

def is_allowed_domain(url: str, allowed_domain: str) -> bool:
    host = urlparse(url).hostname or ""
    return host == allowed_domain

def get_links(index_url: str, selector: str):
    allowed_domain = urlparse(index_url).hostname
    soup = get_soup(index_url)
    raw = [a.get("href") for a in soup.select(selector) if a.get("href")]

    links, seen = [], set()
    for href in raw:
        abs_url = urljoin(index_url, href)

        if is_blocked(abs_url):
            continue
        if not is_allowed_domain(abs_url, allowed_domain):
            continue
        path = urlparse(abs_url).path or ""
        if not path.startswith(ALLOWED_PATH_PREFIX):
            continue

        if abs_url not in seen:
            seen.add(abs_url)
            links.append(abs_url)

    if MAX_LINKS:
        links = links[:MAX_LINKS]
    return links

def extract_article(url: str):
    s = get_soup(url)

    # Title
    t = s.select_one(TITLE_CSS)
    title = t.get_text(strip=True) if t else ""

    # Body (prefer the content block(s) within the same container as the title)
    body_text = ""
    if t:
        # find the nearest container that holds the title
        container = t.find_parent("div", class_="container")
        if container:
            blocks = container.select("div.mb-3")
            if blocks:
                body_text = "\n".join(b.get_text("\n", strip=True) for b in blocks).strip()

    # Fallback if needed
    if not body_text:
        b = s.select_one(BODY_CSS)
        body_text = b.get_text("\n", strip=True) if b else ""

    return {"source_url": url, "title": title, "text": body_text}

def main():
    links = get_links(INDEX_URL, POST_LINKS_CSS)
    print(f"Found {len(links)} candidate links. Writing {OUTPUT_PATH} ...")

    today = date.today().isoformat()
    count_written = 0

    with open(OUTPUT_PATH, "w", encoding="utf-8") as out:
        for i, url in enumerate(links, 1):
            try:
                art = extract_article(url)
                body = art["text"].strip()
                if not body:
                    print(f"{i:03d}/{len(links)}  SKIP (no body)  {url}")
                    time.sleep(PAUSE_SECONDS)
                    continue

                out.write("===ARTICLE===\n")
                out.write(f"source_url: {art['source_url']}\n")
                out.write(f"title: {art['title'] or 'Unknown'}\n")
                out.write(f"date_accessed: {today}\n")
                out.write("TEXT:\n")
                out.write(f"{body}\n\n")

                print(f"{i:03d}/{len(links)}  OK  {art['title'][:70]}")
                count_written += 1
            except Exception as e:
                print(f"{i:03d}/{len(links)}  ERROR  {url}  -> {e}")
            time.sleep(PAUSE_SECONDS)

    print(f"\nWrote {count_written} articles to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
