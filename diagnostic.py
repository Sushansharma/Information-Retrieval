"""
DIAGNOSTIC SCRIPT — RUN THIS FIRST, BEFORE crawler.py
=======================================================
Purpose: The Pure Portal's HTML structure changes over time. This script
fetches the real, live pages and prints out what it finds, so you can
confirm (or fix) the CSS selectors used in crawler.py before trusting them.

Run this in Google Colab (it has open internet access, unlike some
sandboxed/institutional environments). If it fails with a 403, see the
"IF THIS FAILS" note at the bottom of this file.
"""

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36 CourseworkResearchBot/1.0"
}

ORG_PERSONS_URL = "https://pureportal.coventry.ac.uk/en/organisations/centre-for-healthcare-and-community-transformation/persons/"
ORG_PUBS_URL = "https://pureportal.coventry.ac.uk/en/organisations/centre-for-healthcare-and-community-transformation/publications/"


def check_robots():
    print("=" * 70)
    print("1. ROBOTS.TXT CHECK")
    print("=" * 70)
    r = requests.get("https://pureportal.coventry.ac.uk/robots.txt", headers=HEADERS)
    print(r.text[:1500])
    print()


def inspect_persons_page():
    print("=" * 70)
    print("2. PERSONS LISTING PAGE STRUCTURE")
    print("=" * 70)
    r = requests.get(ORG_PERSONS_URL, headers=HEADERS)
    print(f"Status: {r.status_code}, length: {len(r.text)}")
    if r.status_code != 200:
        print("!! Did not get a 200 OK. Cannot proceed with this URL as-is.")
        return

    soup = BeautifulSoup(r.text, "html.parser")

    # Try several plausible containers used by different Pure portal themes
    candidates = [
        ("li.grid-result-item", soup.select("li.grid-result-item")),
        ("li[class*=result]", soup.select("li[class*=result]")),
        ("div.result-container", soup.select("div.result-container")),
        ("ul.grid-results > li", soup.select("ul.grid-results > li")),
    ]
    for label, found in candidates:
        print(f"Selector '{label}': found {len(found)} elements")

    # Show one raw result block so you can eyeball real class names
    best = max(candidates, key=lambda c: len(c[1]))
    if best[1]:
        print("\n--- Sample raw HTML of one person card (first 1200 chars) ---")
        print(str(best[1][0])[:1200])
    else:
        print("\n!! No candidate selector matched anything.")
        print("Paste the page's raw HTML (View Source) into a file and inspect manually.")
    print()


def inspect_publications_page():
    print("=" * 70)
    print("3. PUBLICATIONS LISTING PAGE STRUCTURE")
    print("=" * 70)
    r = requests.get(ORG_PUBS_URL, headers=HEADERS)
    print(f"Status: {r.status_code}, length: {len(r.text)}")
    if r.status_code != 200:
        print("!! Did not get a 200 OK.")
        return

    soup = BeautifulSoup(r.text, "html.parser")

    candidates = [
        ("li.list-result-item", soup.select("li.list-result-item")),
        ("li[class*=result]", soup.select("li[class*=result]")),
        ("div.result-container", soup.select("div.result-container")),
    ]
    for label, found in candidates:
        print(f"Selector '{label}': found {len(found)} elements")

    best = max(candidates, key=lambda c: len(c[1]))
    if best[1]:
        print("\n--- Sample raw HTML of one publication card (first 1500 chars) ---")
        print(str(best[1][0])[:1500])

        # try to find title/author/date/link inside it
        card = best[1][0]
        print("\n--- Attempted field extraction on this sample ---")
        h3 = card.find("h3")
        print("h3 tag found:", h3.get_text(strip=True) if h3 else None)
        a_tags = card.find_all("a")
        print(f"Found {len(a_tags)} <a> tags. hrefs:")
        for a in a_tags[:5]:
            print("   ", a.get("href"))
        spans = card.find_all("span")
        print(f"Found {len(spans)} <span> tags. First few texts:")
        for s in spans[:6]:
            print("   ", repr(s.get_text(strip=True)))
    else:
        print("\n!! No candidate selector matched anything.")
    print()


if __name__ == "__main__":
    check_robots()
    inspect_persons_page()
    inspect_publications_page()

# IF THIS FAILS WITH A 403 / BLOCKED:
# - Try running it from Google Colab instead of your local machine
#   (some university/home networks are geo- or IP-blocked).
# - Add a longer delay and re-check robots.txt for a Crawl-delay directive.
# - As an absolute last resort, tell your module leader the site is blocking
#   automated access and ask for guidance — do not silently switch to
#   scraping a different site without saying so in your report.
