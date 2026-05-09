---
status: Done
priority: High
feature: [Filters]
created: 2026-05-09
---

# Prisfilter 3: Replace single Pris filter with two rows in index.html

In `templates/index.html`, replace the current single "Pris (kr)" filter group with two labelled rows:

- Prisantydning: Min – Maks
- Totalpris: Min – Maks

Inputs must be `type="text" inputmode="numeric"` (so spaces from thousand separators don't break HTML5 number validation). Field names: `prisantydning_min`, `prisantydning_maks`, `totalpris_min`, `totalpris_maks`.
