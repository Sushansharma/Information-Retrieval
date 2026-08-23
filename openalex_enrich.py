"""
openalex_enrich.py
===================
Uses the OpenAlex API (https://openalex.org) to bulk-fetch publications
for a SPECIFIC LIST of researchers you have manually confirmed belong to
the Centre for Healthcare and Community Transformation.

WHY THIS IS SCOPED CORRECTLY (READ BEFORE USING):
OpenAlex only tracks institution-level affiliation (e.g. "Coventry
University"), NOT sub-department. Filtering by institution alone would
pull in publications from EVERY Coventry department, breaking the
brief's requirement for a department-specific vertical search engine.

So this script does NOT filter by institution alone. It filters by
AUTHOR NAME (people you identified by hand from the real department
page) AND checks their listed institution is Coventry, combining both
so the department-scoping decision stays with you, the human, exactly
as it would if you'd copied each entry by hand — this just automates
the tedious "look up all of this person's papers" step.

WORKFLOW:
1. Manually browse the department's persons list in a normal browser
   (Cloudflare allows real browsers): visit
   https://pureportal.coventry.ac.uk/en/organisations/centre-for-healthcare-and-community-transformation/persons/
   and note down researcher names — this is a one-time manual step,
   same as collecting names for the seed script, just no publication
   details needed, only names.
2. Add those names to RESEARCHER_NAMES below.
3. Run: python openalex_enrich.py
4. This queries OpenAlex per name, inserts matches into database.db
   (same schema as crawler.py / seed_manual_data.py).
5. Then continue as normal: python indexer.py, python app.py

IMPORTANT FOR YOUR REPORT: document this clearly as a supplementary
enrichment step alongside the primary crawler (which is blocked by
Cloudflare — see diagnostic.py output) and the manually-verified seed
data. Being explicit about *why* you scoped it this way (author-level,
not institution-level) is itself a good critical-analysis point.
"""

import time
import sqlite3
import requests

DB_PATH = "database.db"
INSTITUTION_NAME = "Coventry University"

HEADERS = {
    "User-Agent": "mailto:student-coursework@example.com "
                   "(ST7071CEM Information Retrieval coursework project)"
}
# OpenAlex explicitly asks polite users to include a contact email in the
# User-Agent or via the `mailto` query param — it's free and raises your
# rate-limit priority. Replace with your real college email if you like.

# --------------------------------------------------------------------
# ADD RESEARCHER NAMES YOU MANUALLY CONFIRMED FROM THE PERSONS PAGE
# --------------------------------------------------------------------
RESEARCHER_NAMES = [
    # "David McWilliams",
    # "Petra Wark",
    # "Nikki Holliday",
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


def find_institution_id(name: str):
    r = requests.get(
        "https://api.openalex.org/institutions",
        params={"search": name, "per-page": 1},
        headers=HEADERS,
        timeout=15,
    )
    r.raise_for_status()
    results = r.json().get("results", [])
    if not results:
        raise RuntimeError(f"No institution found for '{name}'")
    inst = results[0]
    print(f"Resolved institution: {inst['display_name']} -> {inst['id']}")
    return inst["id"]


def find_author_id(author_name: str, institution_id: str):
    """Find an author by name, cross-checked against Coventry affiliation."""
    r = requests.get(
        "https://api.openalex.org/authors",
        params={"search": author_name, "per-page": 5},
        headers=HEADERS,
        timeout=15,
    )
    r.raise_for_status()
    candidates = r.json().get("results", [])

    for c in candidates:
        affiliations = c.get("affiliations", [])
        for aff in affiliations:
            inst = aff.get("institution", {})
            if inst.get("id") == institution_id:
                return c["id"], c["display_name"]

    # fall back: last known institution field
    for c in candidates:
        last_inst = (c.get("last_known_institutions") or [{}])
        if last_inst and last_inst[0].get("id") == institution_id:
            return c["id"], c["display_name"]

    return None, None


def fetch_works_for_author(author_id: str, limit: int = 25):
    r = requests.get(
        "https://api.openalex.org/works",
        params={
            "filter": f"authorships.author.id:{author_id}",
            "per-page": limit,
            "sort": "publication_date:desc",
        },
        headers=HEADERS,
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("results", [])


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
        return False


def enrich():
    if not RESEARCHER_NAMES:
        print("RESEARCHER_NAMES is empty — add names collected from the "
              "persons page first.")
        return

    conn = init_db()
    inst_id = find_institution_id(INSTITUTION_NAME)

    total_new = 0
    for name in RESEARCHER_NAMES:
        print(f"\nSearching OpenAlex for: {name}")
        author_id, matched_name = find_author_id(name, inst_id)

        if not author_id:
            print(f"  No confident Coventry-affiliated match for '{name}' — skipped.")
            continue

        print(f"  Matched: {matched_name} ({author_id})")
        works = fetch_works_for_author(author_id)
        print(f"  Found {len(works)} publication(s)")

        # Pure Portal doesn't give us an OpenAlex profile link, so we
        # construct a best-effort search link back to Pure Portal instead
        # of fabricating a fake URL.
        profile_link = (
            "https://pureportal.coventry.ac.uk/en/persons/?search="
            + matched_name.replace(" ", "+")
        )

        for w in works:
            title = w.get("display_name") or w.get("title")
            year = str(w.get("publication_year") or "")
            pub_link = w.get("id")  # OpenAlex work URL — real, clickable
            if title and pub_link:
                if save_publication(conn, title, matched_name, year, pub_link, profile_link):
                    total_new += 1

        time.sleep(0.5)  # still be polite, even though OpenAlex allows more

    conn.close()
    print(f"\nDone. {total_new} new publication(s) added via OpenAlex.")
    print("Next: run `python indexer.py`, then `python app.py`.")


if __name__ == "__main__":
    enrich()
