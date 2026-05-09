---
status: Done
priority: High
feature: [Website]
created: 2026-05-09
---

# Kart 5: Add get_listings_with_coords(filters) to db.py

Mirror `get_listings()` but:
- Add `AND lat IS NOT NULL AND lon IS NOT NULL` to the base query
- SELECT only the slim columns the map needs:
  `finnkode, adresse, omrade, lat, lon, prisantydning, totalpris, kvm_pris, bra, rom, flagg`
- Apply the same filter contract (status, er_nybygg, omrade, prisantydning_*, totalpris_*, felleskost_maks, bra_*, rom, flagg, kun_nye, sok)
- Return a list of dicts

Keeping the column set narrow keeps the JSON payload small for 1000+ markers.
