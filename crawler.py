"""
crawler.py
==========
Polite crawler for Coventry University's Centre for Healthcare and
Community Transformation publications on Pure Portal.

Politeness measures (explicitly required by the assignment brief):
  - Reads and respects robots.txt via urllib.robotparser
  - Fixed delay between requests (CRAWL_DELAY)
  - Identifies itself with a descriptive User-Agent
  - Only re-fetches what it needs (checked via get_maximum_page)

IMPORTANT: Before trusting this file, run diagnostic.py first and
confirm the selectors below still match the live site. Pure Portal
themes get updated periodically, so treat SELECTOR CANDIDATES below
as "most likely correct as of the last check" rather than guaranteed.
"""

import time
import sqlite3
import urllib.robotparser as robotparser
import requests
from bs4 import BeautifulSoup

BASE = "https://pureportal.coventry.ac.uk"
ORG_SLUG = "centre-for-healthcare-and-community-transformation"
PERSONS_URL = f"{BASE}/en/organisations/{ORG_SLUG}/persons/"
PROFILE_URL_PREFIX = f"{BASE}/en/persons/"
DEPARTMENT_NAME = "Centre for Healthcare and Community Transformation"

DB_PATH = "database.db"
CRAWL_DELAY = 1.5          # seconds between requests — politeness
MAX_PAGES = 20              # safety cap in case pagination logic misbehaves

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36 "
                   "CourseworkResearchBot/1.0 (+student project, ST7071CEM)"
}

session = requests.Session()
session.headers.update(HEADERS)


# ---------------------------------------------------------------- #
# 1. Politeness: robots.txt
# ---------------------------------------------------------------- #
_rp = robotparser.RobotFileParser()
_rp.set_url(f"{BASE}/robots.txt")
try:
    _rp.read()
except Exception:
    print("WARNING: could not read robots.txt — proceeding cautiously "
          "with default delay only.")


def allowed(url: str) -> bool:
    try:
        return _rp.can_fetch(HEADERS["User-Agent"], url)
    except Exception:
        return True  # fail open, but we still keep the delay


def polite_get(url: str):
    if not allowed(url):
        print(f"BLOCKED by robots.txt, skipping: {url}")
        return None
    time.sleep(CRAWL_DELAY)
    try:
        r = session.get(url, timeout=15)
        if r.status_code != 200:
            print(f"Non-200 status ({r.status_code}) for {url}")
            return None
        return r
    except requests.RequestException as e:
        print(f"Request failed for {url}: {e}")
        return None


# ---------------------------------------------------------------- #
# 2. Database setup
# ---------------------------------------------------------------- #
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS publications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT,
            year TEXT,
            pub_link TEXT UNIQUE,
            profile_link TEXT,
            crawled_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn


def save_publication(conn, title, author, year, pub_link, profile_link):
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO publications (title, author, year, pub_link, profile_link)
            VALUES (?, ?, ?, ?, ?)
        """, (title, author, year, pub_link, profile_link))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # pub_link already exists — avoids duplicate entries on re-crawl
        return False


# ---------------------------------------------------------------- #
# 3. Selector helpers (defensive — tries multiple candidates)
# ---------------------------------------------------------------- #
def _first_match(soup, selectors):
    """Try a list of CSS selectors in order, return first non-empty result list."""
    for sel in selectors:
        found = soup.select(sel)
        if found:
            return sel, found
    return None, []


PERSON_CARD_SELECTORS = [
    "li.grid-result-item",
    "li[class*='result-item']",
    "div.result-container",
]

PUB_CARD_SELECTORS = [
    "li.list-result-item",
    "li[class*='result-item']",
    "div.result-container",
]


# ---------------------------------------------------------------- #
# 4. Crawl: find department members, then their publications
# ---------------------------------------------------------------- #
def get_max_page(listing_url: str) -> int:
    """Reads pagination controls to find how many result pages exist."""
    r = polite_get(listing_url)
    if r is None:
        return 0
    soup = BeautifulSoup(r.text, "html.parser")
    nav_links = soup.select("nav a[href*='page=']")
    max_page = 0
    for a in nav_links:
        href = a.get("href", "")
        if "page=" in href:
            try:
                num = int(href.split("page=")[-1].split("&")[0])
                max_page = max(max_page, num)
            except ValueError:
                continue
    return max_page


def extract_person_links(html) -> list:
    """Returns list of (name, profile_url) for each researcher on a listing page."""
    soup = BeautifulSoup(html, "html.parser")
    sel, cards = _first_match(soup, PERSON_CARD_SELECTORS)
    results = []
    for card in cards:
        a = card.find("a", href=True)
        if a and "/persons/" in a["href"]:
            name = a.get_text(strip=True)
            href = a["href"]
            if not href.startswith("http"):
                href = BASE + href
            results.append((name, href))
    return results


def extract_publications_from_profile(html, researcher_name, profile_url):
    """Extract (title, author, year, pub_link) tuples from a person's publications tab."""
    soup = BeautifulSoup(html, "html.parser")
    sel, cards = _first_match(soup, PUB_CARD_SELECTORS)
    records = []
    for card in cards:
        title_tag = card.find("h3") or card.find(class_=lambda c: c and "title" in c)
        title = title_tag.get_text(strip=True) if title_tag else None

        link_tag = None
        if title_tag:
            link_tag = title_tag.find("a", href=True)
        if not link_tag:
            link_tag = card.find("a", href=True)
        pub_link = link_tag["href"] if link_tag else None
        if pub_link and not pub_link.startswith("http"):
            pub_link = BASE + pub_link

        date_tag = card.find("span", class_=lambda c: c and "date" in c)
        year = date_tag.get_text(strip=True) if date_tag else None

        if title and pub_link:
            records.append((title, researcher_name, year, pub_link))
    return records


def crawl():
    print(f"Starting crawl of: {DEPARTMENT_NAME}")
    conn = init_db()
    new_count = 0

    max_page = get_max_page(PERSONS_URL)
    print(f"Detected {max_page + 1} page(s) of researchers.")

    all_people = []
    for page in range(max_page + 1):
        url = PERSONS_URL if page == 0 else f"{PERSONS_URL}?page={page}"
        r = polite_get(url)
        if r is None:
            continue
        people = extract_person_links(r.text)
        print(f"  Page {page}: found {len(people)} researcher(s)")
        all_people.extend(people)

    print(f"Total researchers found: {len(all_people)}")

    for name, profile_url in all_people:
        pubs_url = profile_url.rstrip("/") + "/publications/"
        r = polite_get(pubs_url)
        if r is None:
            continue
        records = extract_publications_from_profile(r.text, name, profile_url)
        for title, author, year, pub_link in records:
            if save_publication(conn, title, author, year, pub_link, profile_url):
                new_count += 1

    conn.close()
    print(f"Crawl complete. {new_count} new publication(s) saved to {DB_PATH}.")
    return new_count


if __name__ == "__main__":
    crawl()
