---
status: Done
priority: High
feature: [Filters]
created: 2026-05-09
---

# Prisfilter 2: Update /annonser route to read new filter fields

In `app.py`, in the `/annonser` POST handler:

- Read `prisantydning_min`, `prisantydning_maks`, `totalpris_min`, `totalpris_maks` from `request.form`
- Strip spaces (thousand separators) from the value before passing to the DB layer
- Drop the old `pris_min` / `pris_maks` keys
