---
status: Done
priority: Medium
feature: [Website]
created: 2026-05-09
---

# Kart 11: Marker click popup with key info

Bind a Leaflet popup to each marker. Content:
- Adresse (bold)
- Område
- Prisantydning + totalpris (formatted)
- BRA + rom
- kr/m²
- Flagg-badges (re-use the same chip styling as listing cards)
- "Se detaljer →" link to `/annonse/<finnkode>`

Reuse the `format_kr` filter where possible by formatting server-side or replicating it small in JS.
