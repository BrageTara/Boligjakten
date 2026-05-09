"""
Backfill lat/lon for existing listings.

PSEUDOCODE:
1. Find all rows in `annonser` and `solgte` where lat IS NULL but a URL exists.
2. For each, GET the listing page, regex-extract `lat=…&lon=…` from the embedded mapUrl.
3. Write coords back. Sleep 0.5 s between requests so we stay polite.
4. Resumable: re-running just continues with the still-missing rows.
"""
import os
import re
import sys
import time
import sqlite3

import requests


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "finn_tracker.db")
DELAY_SEC = 0.5
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
# Two formats appear depending on whether the page is server-rendered or JS-rendered:
#   1. mapUrl="...lat=63.4394&lon=10.4464..." — JS-rendered (Playwright sees this)
#   2. mapUrl encoded as "lat=63.4394&lon=10.4464" in the embedded JSON string
#   3. The cleanest form lives in the same JSON: "lat",63.4394,"lng",10.4464
COORD_RE_URL = re.compile(r"lat=(-?\d+\.\d+)(?:&|\\u0026)lon=(-?\d+\.\d+)")
COORD_RE_JSON = re.compile(r'"lat"\s*,\s*(-?\d+\.\d+)\s*,\s*"lng"\s*,\s*(-?\d+\.\d+)')


def fetch_coords(url):
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
    if r.status_code != 200:
        return None
    for pat in (COORD_RE_JSON, COORD_RE_URL):
        m = pat.search(r.text)
        if m:
            return float(m.group(1)), float(m.group(2))
    return None


def backfill_table(conn, table):
    cur = conn.cursor()
    rows = cur.execute(
        f"SELECT finnkode, url FROM {table} WHERE lat IS NULL AND url IS NOT NULL"
    ).fetchall()
    print(f"\n[{table}] {len(rows)} rader trenger koordinater")
    if not rows:
        return

    updated, missing, errors = 0, 0, 0
    for i, (finnkode, url) in enumerate(rows, start=1):
        try:
            coords = fetch_coords(url)
        except Exception as e:
            errors += 1
            print(f"  [{i}/{len(rows)}] {finnkode}: feil ({e})")
            time.sleep(DELAY_SEC)
            continue

        if coords:
            lat, lon = coords
            cur.execute(
                f"UPDATE {table} SET lat = ?, lon = ? WHERE finnkode = ?",
                (lat, lon, finnkode),
            )
            updated += 1
        else:
            missing += 1

        if i % 50 == 0:
            conn.commit()
            print(
                f"  [{i}/{len(rows)}] commit — oppdatert={updated}, "
                f"manglet={missing}, feil={errors}"
            )
        time.sleep(DELAY_SEC)

    conn.commit()
    print(
        f"[{table}] ferdig: oppdatert={updated}, manglet={missing}, feil={errors}"
    )


def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        backfill_table(conn, "annonser")
        backfill_table(conn, "solgte")
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
