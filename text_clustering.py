"""
text_clustering.py
====================
Task 2: Document Clustering.

1. Loads news_df.csv (from bbc_collect.py or manually filled).
2. Preprocesses text (reusing preprocess.py, same module Task 1 uses).
3. Vectorizes with TF-IDF, reduces dimensionality with Truncated SVD
   (LSA), then L2-normalizes the reduced vectors.
4. Clusters into 3 groups using K-means.
5. Evaluates how well the 3 clusters line up with the real
   Economics/Entertainment/Politics labels (Adjusted Rand Index).
6. Lets you classify a brand new document into one of the clusters.

WHY NORMALIZE AFTER SVD:
K-means uses Euclidean distance between points. Raw SVD/LSA output
vectors can have very different lengths (magnitudes) even when they
point in a similar "topic direction" — and Euclidean distance is
sensitive to length, not just direction. L2-normalizing each vector to
unit length means Euclidean distance between them becomes proportional
to cosine similarity, which is the more meaningful measure for text:
two documents "about the same topic" should be close regardless of
how long or short they are. This is standard practice for LSA-based
text clustering (sometimes called "spherical k-means" when combined
this way).

A NOTE ON REAL-WORLD DATA:
Short, real news headlines/summaries are lexically sparse — two
articles about the same topic often share very few exact words
("housing prices fall" vs "mortgage rates rise" are both economics,
with zero words in common). This means TF-IDF-based clustering on
real short text will realistically NOT achieve perfect separation the
way clean, controlled test data does — some misclassification is
expected and worth discussing honestly in your report as a real
limitation of lexical (word-overlap-based) methods, rather than a
sign that the implementation is broken.

Run: python text_clustering.py
"""

import sys
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score

from preprocess import clean_text

DATA_PATH = "news_df.csv"
N_CLUSTERS = 3
SVD_COMPONENTS = 30  # kept small deliberately — real short news blurbs have
                      # limited vocabulary; too many components reintroduces
                      # noise rather than removing it (tested empirically)


def load_data():
    df = pd.read_csv(DATA_PATH)
    df = df.dropna(subset=["Text", "Class"])
    print(f"Loaded {len(df)} documents.")
    print(df["Class"].value_counts())
    return df


def preprocess_dataframe(df):
    print("Preprocessing text (lowercase, remove punctuation, "
          "remove stopwords, lemmatize)...")
    df["clean_text"] = df["Text"].apply(clean_text)
    return df


def build_and_fit(df):
    vectorizer = TfidfVectorizer(
        max_features=5000,
        stop_words="english",
        ngram_range=(1, 2),   # capture phrases like "prime minister", "interest rates"
        min_df=2,             # ignore words appearing in only 1 document (noise)
        max_df=0.5,           # ignore words in >50% of documents — strips
                               # generic journalism language ("said",
                               # "according to") shared across ALL news
                               # regardless of topic
    )
    X = vectorizer.fit_transform(df["clean_text"])

    n_components = min(SVD_COMPONENTS, X.shape[1] - 1, X.shape[0] - 1)
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    X_reduced = svd.fit_transform(X)
    X_reduced = normalize(X_reduced)  # L2-normalize -> Euclidean ~ cosine

    kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=25)
    cluster_labels = kmeans.fit_predict(X_reduced)

    df["cluster"] = cluster_labels
    return vectorizer, svd, kmeans, X_reduced, df


def evaluate(df, X, cluster_labels):
    ari = adjusted_rand_score(df["Class"], cluster_labels)
    sil = silhouette_score(X, cluster_labels)
    print(f"\nAdjusted Rand Index (agreement with true labels): {ari:.3f}")
    print(f"Silhouette Score (cluster separation quality):     {sil:.3f}")

    print("\nCross-tab: which real category ended up in which cluster")
    print(pd.crosstab(df["Class"], df["cluster"]))

    cluster_to_label = (
        df.groupby("cluster")["Class"]
        .agg(lambda x: x.value_counts().idxmax())
        .to_dict()
    )
    print("\nInferred cluster meaning (majority vote):")
    for cluster_id, label in cluster_to_label.items():
        print(f"  Cluster {cluster_id} -> mostly '{label}'")

    return cluster_to_label


def classify_new_document(text, vectorizer, svd, kmeans, cluster_to_label):
    cleaned = clean_text(text)
    vec = vectorizer.transform([cleaned])
    vec_reduced = svd.transform(vec)
    vec_reduced = normalize(vec_reduced)
    cluster_id = kmeans.predict(vec_reduced)[0]
    predicted_label = cluster_to_label.get(cluster_id, f"cluster {cluster_id}")
    return cluster_id, predicted_label


def main():
    df = load_data()
    df = preprocess_dataframe(df)
    vectorizer, svd, kmeans, X, df = build_and_fit(df)
    cluster_to_label = evaluate(df, X, df["cluster"])

    print("\n" + "=" * 60)
    print("Try classifying a new document (Ctrl+C to stop)")
    print("=" * 60)
    while True:
        try:
            text = input("\nEnter a sentence or short document: ").strip()
            if not text:
                continue
            cluster_id, predicted_label = classify_new_document(
                text, vectorizer, svd, kmeans, cluster_to_label
            )
            print(f"-> Predicted category: {predicted_label} (cluster {cluster_id})")
        except (KeyboardInterrupt, EOFError):
            print("\nDone.")
            sys.exit(0)


if __name__ == "__main__":
    main()
