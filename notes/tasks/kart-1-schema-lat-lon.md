---
status: Done
priority: High
feature: [Database]
created: 2026-05-09
---

# Kart 1: Add lat/lon columns to annonser + solgte

In `finn_tracker_db.py` `init_db()`, add `lat REAL` and `lon REAL` to both `annonser` and `solgte` tables.

Make the migration idempotent: query `PRAGMA table_info(<table>)` before adding columns so existing databases upgrade silently when init_db() is run.
