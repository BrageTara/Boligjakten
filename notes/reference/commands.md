# Commands

Quick reference for terminal commands used in this project. PowerShell unless noted.

## Running the scraper

**Manually (in foreground):**
```powershell
python finn_tracker_db.py
```

**Via the .bat wrapper (logs to `scraper.log`):**
```powershell
.\_run_scraper.bat
```

**Watch the live log (in a second terminal):**
```powershell
Get-Content scraper.log -Wait -Tail 20 -Encoding UTF8
```

The `-Encoding UTF8` flag is required to display Norwegian characters correctly in Windows PowerShell 5.1.

## Status checks

**Did the scraper run today?**
```powershell
python check_status.py
```

**Is python currently running?**
```powershell
Get-Process python -ErrorAction SilentlyContinue
```

**Kill all stale python processes:**
```powershell
Get-Process python | Stop-Process -Force
```

## Website

```powershell
python app.py
```

Then open http://127.0.0.1:5000

## Scheduled task (Windows)

**Inspect the task:**
```powershell
Get-ScheduledTask -TaskName "<task name>" | Format-List
Get-ScheduledTaskInfo -TaskName "<task name>"
```

**Trigger it manually (without waiting for schedule):**
```powershell
Start-ScheduledTask -TaskName "<task name>"
```

**Delete a task:**
```powershell
Unregister-ScheduledTask -TaskName "<task name>" -Confirm:$false
```

## Git

```bash
git status
git log --oneline -10
git diff
```
