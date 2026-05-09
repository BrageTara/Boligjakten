---
status: Idea
priority: Medium
created: 2026-04-22
---

# Flip score — text analysis + price/property signals

Score-based system to detect likely flip/renovation objects.

## Components

1. **Text analysis** of Finn ad title + description: keywords like *oppussing, renovering, selges som den er, slitt, potensial, TG3, råte, fukt* etc. (requires scraping ad description text, which we don't store today)
2. **Price signals:** kr/m² below 70% of area average, takst minus prisantydning gap >200k
3. **Property data:** byggeår before 1980, energimerking F/G (requires scraping these fields)

## Scoring

- ≥50p = sannsynlig oppussingsobjekt (red)
- ≥30p = mulig (yellow)
- <30p = trolig innflyttingsklar (green)

## Prerequisites

Need to scrape and store ad description text, byggeår, energimerking, and takst — none of these are captured today.
