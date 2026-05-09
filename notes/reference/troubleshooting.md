# Troubleshooting

Known issues and fixes. Add new entries here whenever something breaks and gets fixed.

## Norwegian characters mangled in `scraper.log`

**Symptom:** Log shows `s�keside`, `omr�de`, etc. instead of `søkeside`, `område`.

**Cause:** When `python script.py >> file.log` runs in CMD, Windows defaults to `cp1252` encoding for redirected stdout. Norwegian characters either crash the script (`UnicodeEncodeError`) or end up garbled.

**Fix:** Add `set PYTHONIOENCODING=utf-8` to the `.bat` before invoking python. This forces Python to use UTF-8 for all output streams regardless of redirection.

```bat
@echo off
cd /d "C:\path\to\project"
set PYTHONIOENCODING=utf-8
python finn_tracker_db.py >> scraper.log 2>&1
```

## Norwegian characters look mangled when using `Get-Content` (but file is fine)

**Symptom:** `Get-Content scraper.log -Wait -Tail 20` displays mojibake even though the log file itself is correct UTF-8.

**Cause:** Windows PowerShell 5.1 defaults `Get-Content` to the system codepage (cp1252), not UTF-8.

**Fix:** Add `-Encoding UTF8`:
```powershell
Get-Content scraper.log -Wait -Tail 20 -Encoding UTF8
```

PowerShell 7+ defaults to UTF-8 and doesn't have this issue.

## PowerShell prompts `Path[0]:` when running `Get-Content`

**Symptom:** Running `Get-Content -Wait -Tail 20` (no filename) hangs at a `Path[0]:` prompt.

**Cause:** `Get-Content` requires a path. When omitted, PowerShell goes into interactive mode and prompts for it.

**Fix:** Press Ctrl+C, then provide the filename:
```powershell
Get-Content scraper.log -Wait -Tail 20 -Encoding UTF8
```

## `.bat` file won't execute in PowerShell

**Symptom:** Typing `"._run_scraper.bat"` (with quotes) just echoes the filename and does nothing.

**Cause:** Quoted string by itself = string literal, not a command. Also `.\` (with backslash) is required to run from current folder.

**Fix:**
```powershell
.\_run_scraper.bat
```
or with the call operator:
```powershell
& ".\_run_scraper.bat"
```

## Scheduled task fails with `LastResult: 1`

**Symptoms:** Task Scheduler shows the task ran but exit code was 1, no output anywhere.

**Common causes:**
1. **Action points at a `.py` file directly** with no `python.exe` interpreter. Fix: point at `_run_scraper.bat` instead.
2. **Wrong working directory.** Fix: either set `Start in` to the project folder, or use a `.bat` that does `cd /d` itself (current setup).
3. **Python not on PATH for the scheduled task user.** Fix: use full path to `python.exe` in the `.bat`.

## Scraper crashes with Playwright `Browser.close: Connection closed`

**Symptom:** Scraper finishes processing listings, then crashes during browser cleanup with: `Exception: Browser.close: Connection closed while reading from the driver`.

**Status:** Not yet fixed. Suspected cause: race condition between the `finally` block closing the browser and Playwright's internal teardown. Worth investigating but doesn't lose data — listings are committed individually as they're scraped.
