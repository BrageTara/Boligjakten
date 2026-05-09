---
status: Done
priority: High
feature: [Filters]
created: 2026-05-09
---

# Prisfilter 1: Add separate prisantydning + totalpris filters in db.get_listings()

Replace the existing `pris_min` / `pris_maks` filter (which only matched `prisantydning`) with four new filter keys:

- `prisantydning_min`, `prisantydning_maks` → filter on `prisantydning` column
- `totalpris_min`, `totalpris_maks` → filter on `totalpris` column

All four are independent — user can combine any subset.
