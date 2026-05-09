---
status: Done
priority: High
feature: [Scraper]
created: 2026-05-09
---

# Kart 2: Extract lat/lon in scraper.parse_listing()

Regex `lat=(-?\d+\.\d+)&lon=(-?\d+\.\d+)` against the listing HTML; store as floats in `data["lat"]` / `data["lon"]`. Both default to `None` when the regex does not match (e.g. tomtekjøp / hidden-address listings).
