---
status: Done
priority: High
feature: [Website]
created: 2026-05-09
---

# Kart 7: Build templates/kart.html

Extends `base.html`. Layout:
- `.layout` shell (matches `index.html`)
- Sidebar reuses the filter form (copy from index.html, but no `hx-*` — JS handles fetching)
- Main column: `<div id="map"></div>` filling the available height

Pull Leaflet CSS + JS + markercluster from unpkg CDN in the `head` block. Import `static/map.js` at the bottom.
