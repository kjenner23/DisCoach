# scrape_ttc_articles.py
# TableTennisCoaching.com:
# Crawl from the "Improving" section down to (but not including) "Playing in Tournaments",
# fetch internal article pages, and write ChatGPT-ready blocks.

import time
import re
import sys
from datetime import date
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag, NavigableString

# ========= CONFIG =========
INDEX_URL   = "http://www.tabletenniscoaching.com/articles"  # no fragment; we handle sections ourselves
START_HEADER = "Improving"
STOP_HEADER  = "Playing in Tournaments"  # stop *before* this header

# Only fetch internal pages for now
ALLOWED_DOMAINS = {"tabletenniscoaching.com", "www.tabletenniscoaching.com"}

# Article page selectors (from your screenshots)
TITLE_CSS = "h1.node__title"
BODY_CONTAINER_CSS = "div.node__content div.field--name-body div.field__items div.field__item"

# Politeness / Output
PAUSE_SECONDS = 1.0
TIMEOUT = 15
MAX_LINKS = None            # set to an int for test runs; None = all
OUTPUT_PATH = "ttc_batch_for_gpt.txt"
SKIPPED_EXTERNALS_PATH = "ttc_skipped_external_links.txt"

# Optional debug
DEBUG = False

UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

BLOCKED_DOMAINS = {
    "youtube.com", "www.youtube.com", "youtu.be",
    "twitter.com", "x.com",
    "facebook.com", "www.facebook.com",
    "instagram.com", "www.instagram.com"
}

# =========================


def get_soup(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=UA, timeout=TIMEOUT, allow_redirects=True)
    r.raise_for_status()
    s = BeautifulSoup(r.text, "html.parser")
    # Keep <header>; on this site, section titles live nearby.
    for junk in s.select("nav, footer, script, style, form, aside"):
        junk.decompose()
    return s


def is_blocked(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(b in host for b in BLOCKED_DOMAINS)


def is_allowed_internal(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in ALLOWED_DOMAINS


def normalize(href: str, base: str) -> str:
    return urljoin(base, href)


def txt(el: Tag) -> str:
    return el.get_text("\n", strip=True)


def find_section_marker(soup: BeautifulSoup, label: str):
    """
    The page uses <p><strong>Section Name</strong></p> as section markers.
    Return the <p> that contains a <strong> whose text equals label (case-insensitive).
    """
    target = (label or "").strip().casefold()
    for strong in soup.select("p > strong"):
        if (strong.get_text(strip=True) or "").casefold() == target:
            p = strong.find_parent("p")
            return p if p else strong
    # Fallback: contains match
    for strong in soup.select("p > strong"):
        txt_str = (strong.get_text(" ", strip=True) or "").casefold()
        if target in txt_str:
            p = strong.find_parent("p")
            return p if p else strong
    # Last resort: regex anywhere, then climb to nearest <p>
    hit = soup.find(string=re.compile(rf"\b{re.escape(label)}\b", flags=re.I))
    if hit:
        p = hit.parent if hasattr(hit, "parent") else None
        if p and p.name != "p":
            p = p.find_parent("p") or p
        return p or hit
    return None


def collect_links_between_headers(index_url: str, start_header: str, stop_header: str):
    soup = get_soup(index_url)

    if DEBUG:
        with open("debug_index.html", "w", encoding="utf-8") as f:
            f.write(str(soup))
        found = [s.get_text(strip=True) for s in soup.select("p > strong")]
        print("DEBUG — <p><strong>…</strong></p> texts:", found[:60])

    start_node = find_section_marker(soup, start_header)
    if not start_node:
        raise RuntimeError(f'Could not find start header: "{start_header}"')

    stop_node = find_section_marker(soup, stop_header)

    # Iterate sibling *elements* after start_node until we hit stop_node (or we detect the stop marker text)
    links, seen = [], set()

    # Step to the first sibling after the start marker
    node = start_node.next_sibling
    while node:
        # Stop if reached the stop <p> marker node
        if stop_node and node is stop_node:
            break

        # We only care about Tag (element) siblings (skip whitespace text nodes)
        if isinstance(node, Tag):
            # If we hit another <p><strong>…</strong></p> that equals STOP_HEADER, break
            if node.name == "p":
                st = node.find("strong")
                if st and (st.get_text(strip=True) or "").casefold() == stop_header.strip().casefold():
                    break

            # Collect anchors
            if node.name in {"ul", "ol", "li", "p", "div"}:
                for a in node.find_all("a", href=True):
                    href = normalize(a["href"], index_url)
                    if href in seen:
                        continue
                    if is_blocked(href):
                        continue
                    seen.add(href)
                    links.append(href)

        node = node.next_sibling

    if isinstance(MAX_LINKS, int):
        links = links[:MAX_LINKS]
    return links


def extract_article(url: str):
    s = get_soup(url)

    # Title
    t = s.select_one(TITLE_CSS)
    title = t.get_text(strip=True) if t else ""

    # Body (gather all blocks in body container)
    blocks = s.select(BODY_CONTAINER_CSS)
    if blocks:
        body_text = "\n\n".join(txt(b) for b in blocks).strip()
    else:
        # fallback to main node content if the layout shifts
        alt = s.select_one("div.node__content") or s.select_one("article, main")
        body_text = txt(alt) if alt else ""

    return {"source_url": url, "title": title, "text": body_text}


def main():
    # 1) Gather links between sections
    all_links = collect_links_between_headers(INDEX_URL, START_HEADER, STOP_HEADER)

    # 2) Partition internal vs external
    internal, external = [], []
    for u in all_links:
        (internal if is_allowed_internal(u) else external).append(u)

    print(f"Discovered {len(all_links)} links between '{START_HEADER}' and before '{STOP_HEADER}'.")
    print(f"- Internal (to fetch): {len(internal)}")
    print(f"- External (skipped for now): {len(external)}")

    today = date.today().isoformat()
    written = 0

    with open(OUTPUT_PATH, "w", encoding="utf-8") as out:
        for i, url in enumerate(internal, 1):
            try:
                art = extract_article(url)
                body = (art["text"] or "").strip()
                if not body:
                    print(f"{i:03d}/{len(internal)}  SKIP (no body)  {url}")
                    time.sleep(PAUSE_SECONDS)
                    continue

                out.write("===ARTICLE===\n")
                out.write(f"source_url: {art['source_url']}\n")
                out.write(f"title: {art['title'] or 'Unknown'}\n")
                out.write(f"date_accessed: {today}\n")
                out.write("TEXT:\n")
                out.write(body + "\n\n")

                print(f"{i:03d}/{len(internal)}  OK  {art['title'][:80]}")
                written += 1
            except Exception as e:
                print(f"{i:03d}/{len(internal)}  ERROR  {url} -> {e}")
            time.sleep(PAUSE_SECONDS)

    if external:
        with open(SKIPPED_EXTERNALS_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(external) + "\n")

    print(f"\nWrote {written} internal articles to {OUTPUT_PATH}")
    if external:
        print(f"Logged {len(external)} external links to {SKIPPED_EXTERNALS_PATH}")


if __name__ == "__main__":
    # Allow quick CLI toggle for debug: `python3 scrape_ttc_articles.py --debug`
    if len(sys.argv) > 1 and sys.argv[1] == "--debug":
        DEBUG = True
    main()
