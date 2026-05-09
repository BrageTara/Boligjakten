---
status: Done
priority: Medium
feature: [Website]
created: 2026-05-09
---

# Kart 10: Wire sidebar filters to refresh markers

Listen for `change` and `input` events on the filter form (debounce ~400 ms on input). On fire:
- Serialize the form (`new FormData(form)`)
- POST to `/kart/markers`
- Clear the marker layer and rebuild from the response

Same UX as the listings sidebar: filter changes re-query the server.
