"""
seed_manual_data.py
====================
FALLBACK DATA SOURCE — used when automated crawling is blocked by
Cloudflare's bot-detection (see diagnostic.py output + report appendix
for evidence of the block: robots.txt permits crawling, but Cloudflare's
JS-challenge fingerprinting rejects headless browsers regardless).

This inserts REAL, MANUALLY VERIFIED publication data (copied by hand
from the live Pure Portal page by a human, who Cloudflare does not
block) into the exact same SQLite schema crawler.py writes to. Every
downstream component (indexer.py, search_engine.py, app.py) runs
IDENTICALLY regardless of whether data arrived via crawler.py or this
script — this only replaces the data-acquisition step, not the IR
pipeline being assessed.

HOW TO USE:
1. Visit https://pureportal.coventry.ac.uk/en/organisations/centre-for-healthcare-and-community-transformation/publications/
   in a normal browser (not headless — Cloudflare allows real browsers).
2. For each publication, copy: title, author, year, publication link,
   and the author's profile link (click their name).
3. Add each one as a tuple in the PUBLICATIONS list below.
4. Run: python seed_manual_data.py
5. Then continue as normal: python indexer.py, python app.py
"""

import sqlite3

DB_PATH = "database.db"

# --------------------------------------------------------------------
# ADD YOUR MANUALLY COLLECTED PUBLICATIONS HERE
# Format: (title, author, year, pub_link, profile_link)
# --------------------------------------------------------------------
PUBLICATIONS = [
    # Example row — replace with real data you copy from the live site:
    # (
    #     "A Cross-Sectional Study of Postgraduate Wellbeing",
    #     "Bisal, N.",
    #     "2026",
    #     "https://pureportal.coventry.ac.uk/en/publications/a-cross-sectional-study",
    #     "https://pureportal.coventry.ac.uk/en/persons/nabil-bisal",
    # ),
]


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


def seed():
    if not PUBLICATIONS:
        print("PUBLICATIONS list is empty — add your collected data first.")
        return

    conn = init_db()
    cur = conn.cursor()
    inserted = 0
    skipped = 0

    for title, author, year, pub_link, profile_link in PUBLICATIONS:
        try:
            cur.execute("""
                INSERT INTO publications (title, author, year, pub_link, profile_link)
                VALUES (?, ?, ?, ?, ?)
            """, (title, author, year, pub_link, profile_link))
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1  # duplicate pub_link, already seeded

    conn.commit()
    conn.close()
    print(f"Seeded {inserted} publication(s), skipped {skipped} duplicate(s).")
    print("Next: run `python indexer.py`, then `python app.py`.")


if __name__ == "__main__":
    seed()
