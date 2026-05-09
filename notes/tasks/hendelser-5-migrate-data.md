---
status: Done
priority: High
feature: [Database]
created: 2026-04-22
---

# Hendelser 5: Migrate prishistorikk data to hendelser

One-time migration in init_db(): scan prishistorikk per finnkode, first row → publisert, price changes → prisendring, discard duplicates. Also create solgt/trukket/ukjent events from solgte table.
