"""
scheduler.py
============
Satisfies the brief's requirement that the crawler "may be scheduled to
look for new information, say, once per week... and update the index
with the new data" automatically.

Two ways to demonstrate this in your report/video — you don't need to
literally leave this running for seven days during marking:

OPTION A (shown here): a lightweight in-process scheduler using the
`schedule` library. Good for a live demo — you can lower WEEKLY_DAY /
interval temporarily to show it firing within your demo video.

OPTION B (more "production-realistic", mention in your report):
an OS-level cron job / Windows Task Scheduler entry that runs
`python crawler.py && python indexer.py` weekly. Take a screenshot
of the cron entry for your appendix if you go this route instead.
"""

import time
import schedule
from crawler import crawl
from indexer import build_index


def run_weekly_job():
    print("=" * 60)
    print("Scheduled crawl starting...")
    new_count = crawl()
    build_index()
    print(f"Scheduled crawl finished. {new_count} new publication(s) added, index rebuilt.")
    print("=" * 60)


# Runs every Monday at 03:00 in production.
schedule.every().monday.at("03:00").do(run_weekly_job)

# ---- FOR DEMO PURPOSES ONLY: uncomment to trigger every 2 minutes ----
# schedule.every(2).minutes.do(run_weekly_job)

if __name__ == "__main__":
    print("Scheduler started. Waiting for the next scheduled run...")
    print("(Ctrl+C to stop)")
    run_weekly_job()  # run once immediately so you have data to demo
    while True:
        schedule.run_pending()
        time.sleep(30)
