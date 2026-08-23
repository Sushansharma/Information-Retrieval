"""
app.py
======
Flask web front-end. Run with: python app.py
Then open: http://127.0.0.1:5000  (or the Replit-provided public URL)
"""

from flask import Flask, render_template, request
from search_engine import search

app = Flask(__name__)


@app.route("/", methods=["GET"])
def home():
    query = request.args.get("q", "").strip()
    results = search(query) if query else []
    return render_template("index.html", query=query, results=results,
                            result_count=len(results))


if __name__ == "__main__":
    # host="0.0.0.0" is needed for Replit to expose a public URL
    app.run(host="0.0.0.0", port=5000, debug=True)
