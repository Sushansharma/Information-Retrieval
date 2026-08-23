"""
search_engine.py
=================
Query processor + ranked retrieval.

Two-stage approach:
  1. Use the hand-built inverted index to quickly find CANDIDATE
     documents (any doc containing at least one query term) —
     this is the classic Boolean/inverted-index step.
  2. Rank those candidates by TF-IDF cosine similarity, which gives
     genuine relevance ranking rather than just "how many terms
     overlapped" — this demonstrates the IR ranking theory (module
     learning outcome 1) beyond a plain boolean union/intersection.
"""

import sqlite3
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from preprocess import clean_text
from indexer import load_index, DB_PATH


def load_all_publications():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, title, author, year, pub_link, profile_link FROM publications")
    rows = {row["id"]: dict(row) for row in cur.fetchall()}
    conn.close()
    return rows


def candidate_ids_from_index(query_terms, index):
    """Union of all doc ids containing ANY query term — the recall-favouring step."""
    candidates = set()
    for term in query_terms:
        if term in index:
            candidates.update(index[term])
    return candidates


def search(query: str, top_k: int = 20):
    if not query or not query.strip():
        return []

    processed_query = clean_text(query)
    query_terms = processed_query.split()
    if not query_terms:
        return []

    index = load_index()
    all_pubs = load_all_publications()

    candidate_ids = candidate_ids_from_index(query_terms, index)
    if not candidate_ids:
        return []

    candidate_docs = [all_pubs[cid] for cid in candidate_ids if cid in all_pubs]
    if not candidate_docs:
        return []

    # Build TF-IDF space over candidates + the query, rank by cosine similarity
    corpus_texts = [
        clean_text(f"{d['title'] or ''} {d['author'] or ''}") for d in candidate_docs
    ]
    corpus_texts.append(processed_query)  # query is the last "document"

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(corpus_texts)

    query_vector = tfidf_matrix[-1]
    doc_vectors = tfidf_matrix[:-1]

    scores = cosine_similarity(query_vector, doc_vectors).flatten()

    ranked = sorted(zip(candidate_docs, scores), key=lambda x: x[1], reverse=True)
    ranked = [(doc, score) for doc, score in ranked if score > 0]

    results = []
    for doc, score in ranked[:top_k]:
        results.append({
            "title": doc["title"],
            "author": doc["author"],
            "year": doc["year"],
            "pub_link": doc["pub_link"],
            "profile_link": doc["profile_link"],
            "score": round(float(score), 4),
        })
    return results


if __name__ == "__main__":
    q = input("Enter your search query: ")
    for r in search(q):
        print(f"[{r['score']}] {r['title']} — {r['author']} ({r['year']})")
        print(f"    {r['pub_link']}")
