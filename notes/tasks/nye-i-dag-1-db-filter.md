---
status: Done
priority: High
feature: [Filters]
created: 2026-05-09
---

# Nye i dag 1: Add `kun_nye` filter to db.get_listings()

When `filters["kun_nye"]` is truthy, append `AND forste_sett = ?` (today) to the query.
