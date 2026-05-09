---
status: Done
priority: High
feature: [Scraper]
created: 2026-05-09
---

# Kart 3: Wire lat/lon through UPSERT

In `finn_tracker_db.py` `process_listings()`:
- Add `lat`, `lon` to the INSERT column list and `:lat`, `:lon` to the VALUES
- Add `lat = excluded.lat`, `lon = excluded.lon` to the `ON CONFLICT DO UPDATE SET`
- Pass `data.get("lat")`, `data.get("lon")` into the param dict

Apply the same change to the `solgte` insert path.
