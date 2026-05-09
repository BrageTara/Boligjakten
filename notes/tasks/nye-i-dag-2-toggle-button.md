---
status: Done
priority: High
feature: [Filters]
created: 2026-05-09
---

# Nye i dag 2: Add toggle button "Vis kun nye i dag" to sidebar

Place at the top of the filter form. Use the same pattern as the Nybygg toggle:
- Hidden input named `kun_nye` toggled between absent and value="1"
- Button gets `.active` class when on
- Read in /annonser route, pass to db layer
- Update `resetFilters()` to clear it
