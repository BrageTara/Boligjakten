---
status: Idea
priority: Medium
created: 2026-04-22
---

# Fetch actual sale prices from Kartverket API

When Kartverket API access is granted, look up the actual sale price (tinglyst pris) for sold apartments. Store as `solgt_pris` in the `solgte` table.

## Enables

1. Compare asking price vs actual sale price (over/under)
2. Calculate price per m² based on real transaction data
3. Feed accurate sale prices into the ML value estimator

Waiting on API access approval from Kartverket.
