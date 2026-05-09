---
status: Done
priority: Medium
feature: [Database, Website]
created: 2026-04-22
---

# Hendelser 6: Add get_events() to db.py

New function: SELECT * FROM hendelser WHERE finnkode = ? ORDER BY dato. Returns parsed events with JSON detaljer. Replaces get_price_history().
