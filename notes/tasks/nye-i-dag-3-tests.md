---
status: Done
priority: Medium
feature: [Filters]
created: 2026-05-09
---

# Nye i dag 3: Test the kun_nye filter

Add a test to `tests/test_db.py` that seeds a listing with `forste_sett = today` and verifies it's the only one returned when `kun_nye=1` is passed.
