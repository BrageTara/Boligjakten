---
status: Idea
priority: Medium
created: 2026-04-22
---

# Flag potential flip objects (underpriced for their area)

Add a new flag for listings where kr/m² is in the lower quartile (bottom 25%) for their area. We already have `omrade_stats` with kr/m² data per area, and the flagging system in `upsert_listing()`.

This would help spot apartments that might be flip opportunities — priced low relative to the neighbourhood. Could combine with other signals later (age of building, condition keywords in ad text, etc).
