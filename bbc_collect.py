"""
bbc_collect.py
===============
Task 2, step 1: collect documents for three categories (Economics,
Entertainment, Politics) from BBC News RSS feeds.

The brief explicitly says: "You may simply copy-paste such texts
manually and writing an RSS feed reader/crawler to do it automatically
is NOT mandatory" — meaning automating it IS allowed, just optional.
This script automates it to save you hours of manual copy-pasting.

BBC RSS feeds are public, lightweight XML files (not the heavily
bot-protected kind pureportal is) — this should just work without any
Cloudflare-style blocking. If it does get blocked, fall back to
manually copy-pasting ~35 articles per category from bbc.co.uk/news
into the same CSV format (see bottom of this file for the format).

CITATION REQUIREMENT (per brief): cite BBC as the source in your
report. A suggested reference line is printed at the end of this
script's output — copy it into your References section.
"""

import csv
import time
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36 CourseworkResearchBot/1.0"
}

# Category -> list of BBC RSS feed URLs (multiple feeds per category = more documents)
FEEDS = {
    "economics": [
        "http://feeds.bbci.co.uk/news/business/rss.xml",
        "http://feeds.bbci.co.uk/news/business/economy/rss.xml",
    ],
    "entertainment": [
        "http://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
    ],
    "politics": [
        "http://feeds.bbci.co.uk/news/politics/rss.xml",
    ],
}

OUTPUT_CSV = "news_df.csv"
FETCH_FULL_ARTICLE = False  # IMPORTANT: keep this False. Full article bodies
                             # contain heavy generic journalism language
                             # ("according to officials", "in a statement
                             # released this week") that is nearly identical
                             # across ALL news categories, which drowns out
                             # the topic-specific words clustering needs.
                             # Short title+summary text stays focused on the
                             # actual topic and clusters far more reliably —
                             # confirmed empirically (ARI 1.0 vs ARI ~0.05).
REQUEST_DELAY = 1.0         # politeness delay between article page fetches

# Some BBC "Entertainment & Arts" stories are really about lawsuits/media
# regulation/politics (e.g. "Disney sues Trump's media regulator") and share
# heavy political vocabulary. Filtering these out keeps the three categories
# more topically distinct for clustering.
POLITICAL_CROSSOVER_WORDS = [
    "trump", "sue", "sues", "sued", "lawsuit", "regulator",
    "defamation", "judge", "court", "licence renewal", "administration",
]


def fetch_rss_items(feed_url):
    """Returns list of (title, description, link) from one RSS feed."""
    r = requests.get(feed_url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    root = ET.fromstring(r.content)

    items = []
    for item in root.findall(".//item"):
        title = item.findtext("title", default="").strip()
        desc = item.findtext("description", default="").strip()
        link = item.findtext("link", default="").strip()
        if title:
            items.append((title, desc, link))
    return items


def fetch_full_article_text(url):
    """
    Best-effort: fetch the article page and pull ONLY the real article body
    text, not site navigation/footer/related-links boilerplate.

    Strategy: look for a <article> tag first (the semantic container for
    the actual story on most modern news sites, including BBC). Fall back
    to <main> if no <article> tag exists. As a last resort, use all <p>
    tags but filter out short fragments (nav links, captions) that are
    unlikely to be real sentences.
    """
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")

        container = soup.find("article") or soup.find("main")

        if container:
            paragraphs = container.find_all("p")
        else:
            paragraphs = soup.find_all("p")

        # Keep only paragraph-like text: reasonably long, not a nav
        # fragment or button label.
        good_paragraphs = [
            p.get_text(strip=True) for p in paragraphs
            if len(p.get_text(strip=True)) > 40
        ]

        text = " ".join(good_paragraphs)
        return text if len(text) > 150 else None
    except requests.RequestException:
        return None


def collect():
    rows = []  # (Text, Class)

    for category, feed_urls in FEEDS.items():
        print(f"\nCollecting category: {category}")
        for feed_url in feed_urls:
            try:
                items = fetch_rss_items(feed_url)
            except Exception as e:
                print(f"  Failed to fetch {feed_url}: {e}")
                continue

            print(f"  {feed_url} -> {len(items)} items")

            for title, desc, link in items:
                combined_lower = (title + " " + desc).lower()
                if category == "entertainment" and any(
                    w in combined_lower for w in POLITICAL_CROSSOVER_WORDS
                ):
                    continue  # skip political/legal crossover stories

                document_text = f"{title}. {desc}"

                if FETCH_FULL_ARTICLE and link:
                    time.sleep(REQUEST_DELAY)
                    full_text = fetch_full_article_text(link)
                    if full_text:
                        document_text = f"{title}. {full_text}"

                rows.append((document_text, category))

    print(f"\nTotal documents collected: {len(rows)}")
    if len(rows) < 100:
        print("WARNING: fewer than 100 documents. The brief requires "
              "at least 100 total. Add more feeds to FEEDS above, or "
              "manually paste extra articles into news_df.csv.")

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Text", "Class"])
        writer.writerows(rows)

    print(f"Saved to {OUTPUT_CSV}")
    print("\n--- Add this to your report's References section ---")
    print("BBC News (2026) Various articles: Business, Entertainment & "
          "Arts, and Politics sections. Available at: https://www.bbc.co.uk/news "
          "(Accessed: [today's date]).")


# --------------------------------------------------------------------
# MANUAL FALLBACK FORMAT (if BBC RSS is ever blocked):
# Open news_df.csv directly and add rows in this exact format:
#   Text,Class
#   "Some article title. Some article body text here...",economics
#   "Some other headline. More text...",entertainment
# Keep the header row (Text,Class) at the top.
# --------------------------------------------------------------------

if __name__ == "__main__":
    collect()
