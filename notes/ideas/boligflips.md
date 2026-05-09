---
status: Idea
priority: Medium
created: 2026-04-22
---

# Detect boligflips (same apartment listed twice within one year)

A boligflip is when the same apartment is sold and relisted within a year. Challenge: many apartments share the same address (sameie/borettslag), so we need the apartment number (e.g. H0301) to distinguish units. The scraper currently only stores the street address, not the unit number.

## Two parts

1. Scrape and store apartment number from Finn listing page
2. Detection logic that matches same address + unit relisted within 12 months of being sold
