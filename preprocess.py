"""
preprocess.py
=============
Single source of truth for text preprocessing. Imported by BOTH the
indexer (when processing crawled data) and the search engine (when
processing user queries), so both sides are guaranteed to be cleaned
identically — this is an explicit marking requirement.
"""

import string
import nltk
from nltk import pos_tag
from nltk.corpus import wordnet, stopwords
from nltk.stem import WordNetLemmatizer

# Run once. Safe to call repeatedly (no-ops if already downloaded).
for pkg in ["punkt", "punkt_tab", "stopwords", "wordnet",
            "averaged_perceptron_tagger", "averaged_perceptron_tagger_eng"]:
    try:
        nltk.download(pkg, quiet=True)
    except Exception:
        pass

STOP_WORDS = set(stopwords.words("english"))
LEMMATIZER = WordNetLemmatizer()


def _wordnet_pos(tag_letter):
    """Map NLTK POS tag's first letter to a WordNet POS constant."""
    mapping = {
        "V": wordnet.VERB,
        "R": wordnet.ADV,
        "N": wordnet.NOUN,
        "J": wordnet.ADJ,
    }
    return mapping.get(tag_letter, wordnet.NOUN)


def clean_text(text: str) -> str:
    """
    Lowercase -> strip punctuation -> tokenize -> remove stopwords
    -> POS-aware lemmatize -> rejoin into a single space-separated string.
    """
    if not text:
        return ""

    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))

    tokens = nltk.word_tokenize(text)
    tokens = [t for t in tokens if t not in STOP_WORDS and t.strip()]

    cleaned = []
    for tok in tokens:
        try:
            tag = pos_tag([tok])[0][1][0].upper()
            lemma = LEMMATIZER.lemmatize(tok, _wordnet_pos(tag))
        except Exception:
            lemma = LEMMATIZER.lemmatize(tok)
        cleaned.append(lemma)

    return " ".join(cleaned)


if __name__ == "__main__":
    sample = "Running quickly, the researchers analysed multiple datasets!"
    print("Original: ", sample)
    print("Cleaned:  ", clean_text(sample))
