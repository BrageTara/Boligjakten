---
status: Done
priority: High
feature: [Website]
created: 2026-05-09
---

# Kart 9: Render markers with kr/m² colour scale

On page load, fetch `POST /kart/markers` with empty form data. For the response:
- Compute the global P10/P30/P50/P70/P90 of `kvm_pris` from the dataset (one pass)
- For each listing with valid lat/lon, create a Leaflet circleMarker:
  - Colour = bucket(kvm_pris, p10, p30, p50, p70, p90) → 5-step green→red ramp
  - Listings with null `kvm_pris` get neutral grey
- Add to the marker layer

Keep the colour-scale function small and pure — `markerColor(kvm, percentiles)` returns a CSS colour string.
