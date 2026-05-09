---
status: Done
priority: High
feature: [Infrastructure]
created: 2026-05-09
---

# Kart 4: Write tools/backfill_coords.py

One-shot script that:
1. Selects `finnkode, url` from `annonser` where `lat IS NULL` (or `solgte` if applicable)
2. For each row, GETs the URL, regex-extracts `lat`/`lon` from the HTML
3. Writes them back via `UPDATE annonser SET lat=?, lon=? WHERE finnkode=?`
4. Sleeps 0.5 s between requests
5. Prints progress every 50 rows; resumable (just re-run)

Should be safe to ctrl-C and restart. Hits the same `User-Agent` the scraper uses to avoid being throttled.
