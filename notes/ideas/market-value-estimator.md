---
status: Idea
priority: Low
created: 2026-04-22
---

# Market value estimator — ML/statistical model like Solgt.no

Build a model that estimates apartment market value based on condition of rooms (bath, kitchen, etc.), location, size, building year, and other features. Similar to how Solgt.no works.

## Requires

1. Large dataset of sold apartments with actual sale prices (need to scrape sold prices, possibly from Finn sold listings or other sources)
2. Condition data per room (TG scores from tilstandsrapport, or scraped description keywords)
3. Enough data points per area to train meaningful models

## Approach options

Simple regression model first (statsmodels/scikit-learn), then explore gradient boosting (XGBoost) or similar.

This is a long-term idea — needs months of data collection first.
