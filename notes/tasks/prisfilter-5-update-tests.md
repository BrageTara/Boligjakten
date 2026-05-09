---
status: Done
priority: Medium
feature: [Filters]
created: 2026-05-09
---

# Prisfilter 5: Update tests for renamed price filters

In `tests/test_db.py`, the test `test_get_listings_filter_by_pris` uses the old key `pris_maks`. Update it to use `prisantydning_maks`. Add at least one test for `totalpris_maks` to cover the new code path (seed listing 333 has `totalpris=3850000` while `prisantydning=2650000`, so this is the discriminating case).
