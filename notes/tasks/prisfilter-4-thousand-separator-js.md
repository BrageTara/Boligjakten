---
status: Done
priority: High
feature: [Filters]
created: 2026-05-09
---

# Prisfilter 4: Live thousand-separator formatting on price inputs

Add a small JS helper in `index.html` that:

- Listens to `input` events on price fields with class `price-input`
- Strips non-digits, formats with non-breaking space as thousand separator (Norwegian convention), and writes back to the field
- Preserves cursor position so editing in the middle still feels natural

Make sure `resetFilters()` clears all four price fields.
