# Boligjakten — Home

Personal vault for the Boligjakten project. Project management lives here (tasks, ideas, changelog) — code lives at the project root.

## Quick links

- [[scratchpad]] — quick capture / temporary notes
- [[reference/commands]] — useful terminal commands
- [[reference/troubleshooting]] — known issues and fixes
- [[changelog]] — what's been done and when

## Active tasks

```dataview
TABLE
  status AS "Status",
  priority AS "Priority",
  feature AS "Feature"
FROM "notes/tasks"
WHERE status != "Done"
SORT priority ASC, file.name ASC
```

## Ideas — by priority

```dataview
TABLE
  priority AS "Priority",
  status AS "Status"
FROM "notes/ideas"
SORT priority ASC, file.name ASC
```

## Done — recent

```dataview
TABLE
  feature AS "Feature",
  created AS "Created"
FROM "notes/tasks"
WHERE status = "Done"
SORT created DESC
LIMIT 10
```

## Daily logs

Today: [[daily/2026-04-27]]

## Project files (already in this repo)

- `CLAUDE.md` — project instructions for Claude Code
- `docs/superpowers/specs/` — design specs
- `docs/superpowers/plans/` — implementation plans

## Vault conventions

- **Tasks** → `notes/tasks/` — one .md per task with frontmatter (status, priority, feature)
- **Ideas** → `notes/ideas/` — one .md per idea with frontmatter (status, priority)
- **Changelog** → `notes/changelog.md` — single append-only file, reverse-chronological
- **Daily logs** → `notes/daily/` named `YYYY-MM-DD.md`
- **Reference** → `notes/reference/` — stable cheatsheets, not work-in-progress
- **Scratchpad** → `notes/scratchpad.md` — fair game to wipe whenever

## Frontmatter cheatsheet

**Tasks:**
```yaml
---
status: To Do        # Backlog | To Do | In Progress | Done | Blocked
priority: High       # High | Medium | Low
feature: [Scraper]   # Scraper | Database | Website | Filters | Detail Page | Infrastructure
created: 2026-04-27
---
```

**Ideas:**
```yaml
---
status: Idea         # Idea | Planned | Done
priority: Medium     # High | Medium | Low
created: 2026-04-27
---
```

## Required Obsidian plugins

- **Dataview** — powers the live tables above. Install via Settings → Community Plugins → Browse → "Dataview" → Enable.

Without Dataview, the queries above render as code blocks instead of tables. Files still work as plain markdown either way.
