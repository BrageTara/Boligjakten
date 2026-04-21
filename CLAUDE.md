# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Boligjakten** — daily scraper and local website for tracking the apartment market in Trondheim. Data is fetched from Finn.no using Playwright and stored in SQLite. The website is built with Flask + HTMX.

## Running the code

```bash
# Scrape all apartments and save to SQLite (primary version)
python finn_tracker_db.py

# Scrape and save to Excel (fallback version)
python finn_tracker.py

# Start the website
python app.py
```

Install all dependencies with:
```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## Architecture

**Two parallel scraper versions:**
- `finn_tracker_db.py` — primary version, saves to `finn_tracker.db` (SQLite)
- `finn_tracker.py` — fallback version, saves to `finn_tracker.xlsx` (Excel)
- `scraper.py` — shared scraping logic imported by `finn_tracker_db.py`

**Website (under development):**
- `app.py` — Flask server
- `templates/` — Jinja2 templates (base.html, index.html, detalj.html)
- `static/style.css` — CSS

**Database (`finn_tracker.db`):**
- `annonser` — one row per apartment, upserted on each run
- `prishistorikk` — one row per run per apartment (price log)
- `solgte` — listings that disappear from search are copied here with reason (Solgt/Trukket/Ukjent)

## Key implementation details

**Scraping:**
- Playwright runs headless with Chromium. The cookie dialog on Finn.no is accepted automatically via `accept_cookies()`.
- Search URL and `POSTNUMMER` lookup table are defined in `scraper.py`.
- Listings are flagged automatically based on: price reduction, 14+ days on Finn, 2+ viewings, high shared debt (≥30% of total price).
- The scraper commits after each listing (`conn.commit()`) — data is not lost on crash.

**Website:**
- Filtering uses HTMX: filters POST to `/annonser` and return only the list HTML, replacing the current list.
- New listings (seen today) are highlighted with a green background.
- Detail page at `/annonse/<finnkode>` shows all fields + price history.

---

## How we work

### Language
- All code, variable names, comments, and pseudocode must be in **English**.
- Norwegian is only used in user-facing UI text (labels, headings, button text).

### Pseudocode
- Every non-trivial function must have a pseudocode comment block above it explaining what it does in plain English, step by step.
- Example:
  ```python
  # PSEUDOCODE:
  # 1. Load all active listings from the database
  # 2. For each filter provided, narrow down the result set
  # 3. Sort by the requested field (default: newest first)
  # 4. Return the filtered and sorted list
  def get_listings(filters, sort):
      ...
  ```

### Brainstorming before new features
- Before writing any code for a new feature, Claude and the user must brainstorm, discuss and design the feature together.
- Claude must NOT start writing code until the design is agreed upon.
- Once the design is agreed, Claude writes a **to-do list** of every task needed to implement the feature and adds it to the user's Notion workspace before any code is written.

### Verification before done
- Claude must always run the code and confirm it works before reporting a task as complete.
- Claude must show the actual output or test result — not just claim it works.

### Commits
- The user always approves commits manually. Claude must never commit without explicit instruction.
- Claude may prepare the commit message and stage files, but must stop and ask before running `git commit`.

### File size and splitting
- When a file grows large, Claude must flag it and suggest how to split it — the user decides whether to proceed.
- General guidelines:
  - Files over ~300 lines: Claude suggests splitting and explains where the natural boundaries are.
  - Split by responsibility: one file = one clear purpose (e.g. database access, scraping, routes).
  - The user has limited experience with this — Claude must explain the trade-offs clearly before any split is made.

### Notion workspace
- **Finn Tracker:** https://www.notion.so/349fea4d0c678174bb82ee157e7005ce
- **Tasks database:** https://www.notion.so/93e6071eea9b4e3ba3e8476798469a04
- **Design Specs:** https://www.notion.so/349fea4d0c67810a816fe5b1d729e4de
- **Changelog:** https://www.notion.so/349fea4d0c67813eba9accb1819def8f

When a feature is designed and approved, add all implementation tasks to the Tasks database before writing any code. Set Status to "To Do" and assign the correct Feature tag.

### Workflow reference
- Design specs are saved in `docs/superpowers/specs/`.
- The Excel version (`finn_tracker.py`) must not be deleted — it is an intentional fallback.
- Do not add maps, mobile optimization or user authentication without discussion — these are explicitly out of scope for now.
