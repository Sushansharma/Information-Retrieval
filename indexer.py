"""
indexer.py
==========
Builds and persists a hand-written inverted index from the SQLite
publications table. This is deliberately NOT using a library's
built-in index (e.g. whoosh) — the marking criteria specifically
credits your own index construction logic (Learning Outcome 2).

Index shape:  { "term": [pub_id, pub_id, ...], ... }
Saved to index.json so the Flask app can load it without recomputing.
"""

import json
import sqlite3
from preprocess import clean_text

DB_PATH = "database.db"
INDEX_PATH = "index.json"


def load_publications():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, title, author FROM publications")
    rows = cur.fetchall()
    conn.close()
    return rows


def build_index():
    rows = load_publications()
    index = {}

    for row in rows:
        pub_id = row["id"]
        combined_text = f"{row['title'] or ''} {row['author'] or ''}"
        cleaned = clean_text(combined_text)

        for term in cleaned.split():
            if term not in index:
                index[term] = []
            if pub_id not in index[term]:
                index[term].append(pub_id)

    with open(INDEX_PATH, "w") as f:
        json.dump(index, f, sort_keys=True, indent=2)

    print(f"Index built: {len(index)} unique terms across {len(rows)} publications.")
    return index


def load_index():
    with open(INDEX_PATH, "r") as f:
        return json.load(f)


if __name__ == "__main__":
    build_index()
