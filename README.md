# HCT Publication Search Engine — Run Guide

## 0. Before anything else — verify the site structure

The exact HTML class names on Pure Portal can change between when this
code was written and when you run it. **Run this first:**

```bash
python diagnostic.py
```

Read the output. It tells you:
- Whether robots.txt allows crawling these pages (it should)
- Which CSS selector actually matched real content
- A raw HTML sample of one researcher card and one publication card

**If `crawler.py` later returns 0 results:** open `diagnostic.py`'s output,
find the real class names printed there, and update the `PERSON_CARD_SELECTORS`
/ `PUB_CARD_SELECTORS` lists near the top of `crawler.py` to match. This is
normal, expected maintenance for any web crawler — mention it in your
report as evidence you understand crawler fragility, which is itself a
good critical-analysis point for the 70%+ band.

## 1. Where to run this

**Recommended: Google Colab** for steps 2–4 (crawling/indexing) — free,
no setup, and matches the notebook style expected in your appendix.

```python
# In a Colab cell:
!pip install requests beautifulsoup4 nltk flask scikit-learn schedule -q
```
Then upload these .py files to the Colab session (or mount Google Drive),
and run them either via `!python crawler.py` or by pasting the functions
into cells (closer to how your sample project's notebooks are structured).

**Recommended: Replit** for step 5 (the Flask web app) — gives you an
instant public URL, ideal for your video demo and for showing a genuine
"web-based UI" (required for 70%+).

If your college network blocks scraping, try running steps 2–4 from
Colab specifically (different IP range than campus WiFi) rather than
your laptop.

## 2. Install dependencies (if running locally instead of Colab)

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet'); nltk.download('averaged_perceptron_tagger')"
```

## 3. Run the crawler

```bash
python crawler.py
```

This creates `database.db` (SQLite) with a `publications` table. Re-running
it later only adds NEW publications (duplicates on `pub_link` are skipped)
— this is what makes weekly re-crawling safe and incremental.

## 4. Build the inverted index

```bash
python indexer.py
```

This reads `database.db`, preprocesses every title+author through
`preprocess.py`, and writes `index.json` — your hand-built inverted index.

You can sanity-check it quickly:
```bash
python search_engine.py
# then type a query like: mental wellbeing
```

## 5. Run the web app

```bash
python app.py
```
Open `http://127.0.0.1:5000` locally, or use Replit's provided public URL
if running there (make sure `app.run(host="0.0.0.0", ...)` stays as-is).

## 6. (Optional but recommended for marks) Run the scheduler

```bash
python scheduler.py
```
This re-crawls and rebuilds the index automatically on a weekly cadence.
For your demo video, temporarily uncomment the 2-minute interval line
inside `scheduler.py` so the marker can actually see it fire, then put
the real weekly schedule back before submitting your code appendix.

## File-by-file summary (for your report's Introduction section)

| File | Learning outcome it demonstrates |
|---|---|
| `diagnostic.py` | Understanding of crawler fragility / verification practice |
| `crawler.py` | LO3 — web crawler implementation, politeness (robots.txt) |
| `preprocess.py` | LO1/LO2 — shared preprocessing pipeline |
| `indexer.py` | LO2 — hand-built inverted index construction |
| `search_engine.py` | LO3 — query processor + TF-IDF ranked retrieval |
| `app.py` + `templates/index.html` | LO5 — minimum viable vertical search engine, web UI |
| `scheduler.py` | Automatic weekly re-crawl requirement |

## Common issues

- **0 researchers found**: selectors are stale — check `diagnostic.py` output.
- **403 Forbidden**: your IP may be temporarily rate-limited; increase
  `CRAWL_DELAY` in `crawler.py` and try again after a few minutes.
- **NLTK LookupError**: re-run the `nltk.download(...)` line from step 2.
- **Flask "address already in use"**: another process is on port 5000 —
  change `port=5000` in `app.py` to e.g. `port=5001`.
