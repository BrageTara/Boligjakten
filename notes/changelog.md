# Changelog

Log of completed work, in reverse chronological order.

---

## 2026-05-09

**Added interactive map page (/kart)**
- New `/kart` page with Leaflet (OpenStreetMap tiles) showing all active listings as clustered markers
- Coordinates extracted from Finn's embedded `mapUrl` (≈10 cm precision); new schema columns `lat`/`lon` on `annonser` + `solgte`
- 5-step green→red colour scale based on the dataset's P10/P30/P50/P70/P90 of `kvm_pris` so cheap listings stand out
- Clicking a marker opens a popup with adresse, område, pris, kr/m², BRA, rom, flagg-badges, and a "Se detaljer →" link
- Sidebar reuses the same filter form as the listings page (shared `parse_filters_from_form` helper); changes refetch markers via `POST /kart/markers` (JSON)
- Backfill script `tools/backfill_coords.py` populates coords for existing rows, resumable, polite (0.5 s/req)
- Files: `app.py`, `db.py`, `templates/kart.html`, `templates/base.html`, `static/map.js`, `static/style.css`, `scraper.py`, `finn_tracker_db.py`, `tools/backfill_coords.py`, tests

**Added "Lav kr/m²" flag for listings below their area's Q1**
- New `update_lav_kvm_flag(conn)` runs after `update_omrade_stats` — flags every active listing whose `kvm_pris` is strictly below the area's `alle_q1`, removes the flag when it no longer qualifies
- Cyan diamond badge (💎 Lav kr/m²) on listing cards; sidebar checkbox under Flagg lets you filter to just these
- 276 of 1439 active listings flagged on the current dataset (~19%)

**Split 18 postnummer out of generic "Trondheim" into specific areas**
- 9 mapped from address evidence: 7020→Hallset, 7026→Stavset, 7032→Nardo, 7038→Fossegrenda, 7040→Lade, 7047→Brundalen, 7052→Tyholt, 7067→Lademoen, 7068→Møllenberg
- 9 mapped from local knowledge: 7029→Romolslia, 7035→Sørlig Nardo, 7036→Risvollan, 7039→Bratsberg, 7046→Strindheim, 7050→Moholt, 7066→Lilleby, 7069→Brøset, 7071→Ugla
- DB: 554 rader relabelet, `omrade_stats` regenerert (52→59 områder), "Lav kr/m²"-flagget oppfrisket
- Aktive annonser med omrade='Trondheim' falt fra 418 til 0

**Fixed postnummer parsing — eliminated 100 garbage "Ukjent (...)" rows**
- Loose fallback regexes in `scraper.py` were picking up year numbers (2020, 2024) and unrelated 4-digit values (1000, 5001, 8281) from listing text
- Replaced with stricter logic: DOM label first, then "<pnr> <known city>" pattern, then JSON `postCode` fields constrained to Trondheim region (70xx or 7540–7549)
- Added 7061 → "Leangen" to `POSTNUMMER` (Travbanevegen / Leangen Byhagen / Tunet — were showing as Ukjent)
- Cleaned up DB: relabeled 26 rows with postnummer 7061 to omrade='Leangen'; NULL'd omrade+postnummer for the remaining 78 garbage rows so they get re-scraped correctly

**Histogram cleanup: labels above bars + dropped nybygg from chart**
- Reserved a 56px label band above the bars (via `padding-top` on `.histogram-bars`); labels (Snitt, Median, Q1, Denne) sit in this band so they no longer collide with tall bars
- Nybygg aktiv/solgt segments and legend items removed from the histogram per request; max-bar-height now scales to the brukt total only, and the brukt/nybygg legend toggle is gone (lines always reflect "alle"/brukt)
- Tooltip simplified to just brukt aktiv + brukt solgt

**Histogram now shows the current listing's kr/m² as a vertical line**
- On the detail page, a solid red line marks where the listing sits in its area's distribution, alongside the dotted Snitt/Median/Q1 lines
- Solid (vs dotted) and slightly higher z-index so the listing's own value stands out from aggregate stats
- Falls back gracefully when `kvm_pris` is missing or out of range

**Added hover tooltip for histogram bars**
- Hovering a bar highlights it (slight brightness boost) and shows a tooltip with the price range, total count, and per-segment breakdown (brukt aktiv/solgt + nybygg aktiv/solgt)
- Tooltip auto-flips left near the right edge so it doesn't clip

**Added lower quartile (Q1) line to kr/m² histogram**
- Cyan dotted line at the 25th-percentile of kr/m² values, alongside Snitt and Median
- Stored as `brukt_q1`, `ny_q1`, `alle_q1` in `histogram_json`; reused by the brukt/nybygg legend toggle so it updates with the active segment
- Label is stacked below Snitt and Median to avoid overlap when values are close

**Moved histogram x-axis labels into their own row below the bars**
- Previously labels lived inside the same flex column as the bar, causing visual overlap with the bars at the bottom of the chart
- Split into a dedicated `.hist-axis` row with absolutely-positioned ticks; bars are now visually clean

**Histogram polish: round x-axis labels and stacked Snitt/Median labels**
- Labels now appear at multiples of 20k (20k, 40k, 60k, …) instead of every Nth bin
- Median line label now sits below the Snitt label so the two no longer overlap when avg and median are close

**Histograms now share a common x-axis across all areas**
- Computed once globally (after per-area outlier removal) so every area renders on the same kr/m² scale (currently 12k–156k)
- Areas with narrower data show empty trailing/leading bins, but distributions are now directly comparable across areas at a glance

**Made histogram bars more readable**
- Bars too thin and labels overlapping after the dense-bins fix on areas with wide ranges (Trondheim had 64 bins)
- Added a 98th-percentile per-area cap that drops the long thin tail of sparse outlier clusters (Trondheim trimmed 64→52 bins, Elgeseter 71→45)
- Increased histogram height 100→140px
- Labels now show only every Nth bin (~10 labels regardless of bin count) so they don't overlap

**Fixed dotted snitt/median lines being placed wrong on histogram**
Two bugs combined:
- `build_bins()` emitted only bins with data, leaving gaps in the price axis. The line position formula assumes a linear/dense axis, so lines landed in the wrong bin
- `.hist-col` had `min-width: 28px`, so wide histograms (e.g. Trondheim with 51 bins) overflowed the container; lines were positioned by container percentage but bars extended beyond it
Fixes: emit dense bins (zero-fill gaps); switch `.hist-col` to `flex: 1 1 0; min-width: 0` so bars share width equally without overflowing

**Fixed outliers skewing avg/median in kr/m² histogram**
- Outlier cap (200k kr/m²) was applied only inside `build_bins()`, so corrupt rows still skewed `alle_avg`, `brukt_avg`, `ny_avg`, and the top-level `snitt_kvm_pris`/`max_kvm_pris`
- Several areas had stored avgs in the billions/trillions (e.g. Nedre Elvehavn 746B kr/m²; corrected to 82 557)
- Cap moved up-front so all downstream stats use the same filtered list; regression test added; existing DB recomputed via `update_omrade_stats`

**Added free-text search field at top of sidebar**
- Matches case-insensitively across `adresse`, `finnkode`, and `omrade`
- Pasting a finn.no URL extracts the finnkode (`finnkode=NNN`) so the URL itself doesn't have to match literally
- Combines with all other filters

**Added felleskost maks-filter to sidebar**
- Single max-only field (kr/mnd) under the Totalpris row
- Listings with NULL felleskost are excluded when filter is set — can't make claims about unknowns
- Reuses thousand-separator JS

**Added "Vis kun nye i dag" toggle in sidebar**
- Full-width green toggle button at the top of the filter form
- Filter key `kun_nye` in `db.get_listings()` adds `forste_sett = today` clause
- Combines with all other filters; reset clears it

**Fixed "NY" badge / "nye i dag" using wrong column**
- `is_new` flag and `get_stats().nye_i_dag` used `siste_sett` (last seen, updates every scraper run) so most listings were tagged NY
- Switched both to `forste_sett` (first seen). Count dropped from ~1100 to 63 today

**Split price filter into prisantydning + totalpris with thousand separators**
- Sidebar now has two labelled price rows (Prisantydning, Totalpris), each with min/maks
- `db.get_listings()` accepts `prisantydning_min/maks` and `totalpris_min/maks` (replaces old `pris_min/maks`)
- Inputs are `type=text inputmode=numeric`; live JS formats digits with non-breaking thousand separators while preserving cursor position
- `/annonser` route strips spaces before parsing; tests updated and added for the new totalpris path

---

## 2026-04-27

**Migrated project management from Notion to Obsidian**
- Created `notes/tasks/`, `notes/ideas/`, `notes/changelog.md`
- Converted 16 Notion tasks (all Done) and 8 ideas to markdown with frontmatter
- Updated `Home.md` with Dataview queries
- Updated `CLAUDE.md` to reflect new workflow

**Fixed UTF-8 encoding bug in scheduled scraper**
- Created `_run_scraper.bat` wrapper for Windows Task Scheduler
- Added `set PYTHONIOENCODING=utf-8` so redirected output handles Norwegian + zero-width characters
- Wired the `.bat` into Task Scheduler

**Enhanced histogram with average/median reference lines**
- Scraper stores `brukt_avg`, `brukt_median`, `ny_avg`, `ny_median`, `alle_avg`, `alle_median`, `bin_start` in `histogram_json`
- Template renders purple (snitt) and amber (median) vertical dotted lines that toggle with Brukt/Nybygg legend
- Old DB format handled gracefully; lines appear after next scraper run

---

## 2026-04-23

**Added average/median lines to kr/m² histogram**
- Scraper now calculates and stores `brukt_avg`, `brukt_median`, `ny_avg`, `ny_median`, `alle_avg`, `alle_median`
- Template renders purple (snitt) and amber (median) vertical dotted lines that update when Brukt/Nybygg legend is toggled
- Old DB format handled gracefully — histogram still renders correctly without lines until next scraper run

---

## 2026-04-22

**Added hendelser (events) table — replaces prishistorikk**
- New `hendelser` table with columns: finnkode, dato, type, detaljer (JSON)
- Event types: publisert, prisendring, visning, solgt, trukket, ukjent
- `log_event()` helper function replaces `log_price_history()`
- Event detection in `upsert_listing()`: logs publisert (new/re-appeared), prisendring (price changed), visning (new viewing)
- Event logging in `mark_sold()`: logs solgt/trukket/ukjent when listing disappears
- One-time migration converted 1083 existing prishistorikk rows into hendelser events
- Only records changes — no more daily duplicate snapshots

**Timeline on detail page**
- Replaced price history table with chronological timeline
- Colored dots per event type (blue=publisert, orange=prisendring, gray=visning, green=solgt)
- New `get_events()` query in db.py

**Cleanup**
- Removed `log_price_history()` and `get_price_history()`
- Deleted temp screenshots and playwright cache
- Updated .gitignore for db lock files, screenshots, and .playwright-mcp/

**Notion workspace**
- Created Ideas database for feature wishlist (separate from Tasks)
- Added 8 feature ideas: UI redesign, boligflips, flip score, Kartverket API, map view, similar listings, ML model, underpriced flag

---

## 2026-04-21

**Converted scraper to Playwright**
- Replaced requests/BeautifulSoup with Playwright (headless Chromium)
- Now fetches all ~1000 listings instead of ~400
- Handles cookie dialog automatically
- Retries on network errors

**Added SQLite storage**
- Created `finn_tracker_db.py` as primary version
- Extracted shared scraping logic to `scraper.py`
- `finn_tracker.py` (Excel) kept as fallback
- Commits after each listing — no data lost on crash

**Added flags**
- Prisnedsatt, 14+ dager, 2+ visninger, Høy fellesgjeld

**Added backup save**
- If Excel file is locked (open in Excel), saves to timestamped backup file
