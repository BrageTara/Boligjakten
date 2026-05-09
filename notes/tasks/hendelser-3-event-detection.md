---
status: Done
priority: High
feature: [Scraper]
created: 2026-04-22
---

# Hendelser 3: Add event detection to upsert_listing()

Detect and log: publisert (new listing or re-appeared), prisendring (price differs from latest known), visning (new viewing date). Compare against latest hendelser row, not daily snapshot.
