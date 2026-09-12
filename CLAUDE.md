# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Early scaffolding. The module tree exists under [src/](src/) as **stubs** (docstrings + signatures + `TODO`s referencing spec sections); most collectors/report/mailer functions raise `NotImplementedError` and are the actual work ahead. The design spec ([docs/monitor_pc_spec.md](docs/monitor_pc_spec.md)) is the source of truth — read it before implementing. Section 11 is a ready-to-paste build prompt; section 12 lists decisions already locked in (don't relitigate them).

Already implemented (safe foundations): [src/config.py](src/config.py) (config.ini loader), [src/utils/timeutil.py](src/utils/timeutil.py) (UTC/Lima + FILETIME/Chrome-time conversions), [src/state.py](src/state.py) (SQLite schema), the `$I` header parser in [src/collectors/recycle_bin.py](src/collectors/recycle_bin.py), [src/categories.py](src/categories.py) (risk categories + pill/row styles + `render_pill`), **`DomainCategorizer.categorize()`** in [src/collectors/domain_categories.py](src/collectors/domain_categories.py) (fully working: hostlists + suffix rules + keyword fallback), and [src/report/correlate.py](src/report/correlate.py) (download↔deletion matching), the **processes collector** [src/collectors/processes.py](src/collectors/processes.py) (time-per-app, tested via [tools/test_processes.py](tools/test_processes.py)), the **browser-history reader** [src/collectors/browser_history.py](src/collectors/browser_history.py) (visits + downloads from Chrome/Edge/Opera GX), SID→profile resolution [src/winprofile.py](src/winprofile.py), and HTML render helpers (`page`/`render_table`/`render_row`) in [src/report/html_report.py](src/report/html_report.py). Two real-data test tools: [tools/test_report.py](tools/test_report.py) (real browsing → HTML report) and [tools/test_processes.py](tools/test_processes.py). Run [tools/preview_report.py](tools/preview_report.py) for a sample report with fictitious data.

Still stub (`NotImplementedError`): recycle-bin watchers (parser done), Excel export, `mailer.send_report`, `html_report.build_report` (per-date email assembly), and the `monitor_pc.run` main loop.

## Commands

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1   # setup
pip install -r requirements.txt
Copy-Item config.example.ini config.ini              # then edit SMTP creds (never commit config.ini)
python -m src.monitor_pc                              # run in foreground for testing
```

Run modules/tests from the project root so `from src....` imports resolve. No test suite or linter is configured yet.

The spec is written in Spanish, and all user-facing output (email report, badges, column headers) must be in Spanish for an **America/Lima** audience. Keep code identifiers/comments in whatever style the existing code uses once code exists.

## What this project is

A Python background agent for **Windows 10/11** that runs as a **parental-control monitor** on a minor's standard (non-admin) user account, installed from an admin account. It records the day's activity and emails **one consolidated daily report** (HTML body, optional `.xlsx` attachment). This is legitimate parental supervision of a family-owned device — the spec (§9) requires the repo stay **private** and never contain real credentials or captured data.

## Architecture (intended)

Single background process (run headless via `pythonw.exe`) with independent collection modules feeding a shared local state store, drained once per day into a report + email. Planned layout per spec §9: `src/` (code), `docs/` (spec + decisions), `config.example.ini` (template, no secrets), plus an install `.ps1`.

Collection modules (spec §3):
- **Processes** — *implemented* in [src/collectors/processes.py](src/collectors/processes.py). `psutil` poll; open/close events → **total time per app** via **interval union** (Chrome with 10 processes open 2h counts 2h, not 20h — see `accumulate_time_per_app`). To separate real apps from the ~hundreds of background/system processes, it filters to PIDs owning a **visible titled top-level window** (`visible_window_pids()` via `ctypes`/user32, no extra dep; accumulated over the session so tray-minimized apps keep counting), plus an ignore-list and optional target-user filter. Test locally with no install/SMTP: `python tools/test_processes.py` (instant snapshot of open apps) or `--watch N` (live open/close tracking). Exe→friendly names in `FRIENDLY_NAMES`.
- **Browser history + categorization** — Chrome, Edge, **Opera GX** (the child's browsers), Opera and Brave are *all Chromium*: same `History` SQLite schema (`urls`/`visits`/`downloads`), only the path differs. [src/collectors/browser_history.py](src/collectors/browser_history.py) → `find_history_files(env)` enumerates installed browsers **and all profiles** (`Default`, `Profile N`); `BrowserHistoryCollector.collect_all(since_utc)` is *implemented* — copies the locked `History` (+`-wal`/`-shm`) to a temp dir, reads `urls`/`visits` and `downloads`, categorizes domains, flags suspicious downloads (`.apk`/`.exe`/`.zip` from non-`normal` origin), writes to state. Opera/Opera GX live under **`%APPDATA%` (Roaming)**, not Local, and without a `User Data` level. Test with real data: `python tools/test_report.py [--days N]` (reads your own history → real HTML report; console shows only counts). **Path resolution runs as SYSTEM, so it cannot use the process's own env vars** — [src/winprofile.py](src/winprofile.py) resolves the child's `%LOCALAPPDATA%`/`%APPDATA%`/`$Recycle.Bin` from their **SID** via the registry `ProfileList`. Install step [tools/detect_browsers.py](tools/detect_browsers.py) (`--sid`) lists what will be monitored; the installer calls it after the admin picks the account. Firefox (`places.sqlite`) optional. Categorize each domain into one of four risk categories using **public reference hostlists** (e.g. StevenBlack/OISD) plus keyword heuristics as fallback — **no hand-curated domain list**. Categories + their pill/row colors live in [src/categories.py](src/categories.py) (the single source of truth, shared by web domains *and* the app/process table): `adulto` (🔞 red), `juegos` (🎮 orange), `normal` (• gray), `desconocido` (🔍 violet). **Unmatched → `desconocido`, not `normal`**: anything not confirmed by a reference list is flagged for review rather than assumed safe. This replaces the spec's original `dudoso/otros`. `normal` requires a match against [data/known_sites.txt](data/known_sites.txt) — **the one hand-curated list in the project** (the user's explicit decision, only for the normal-vs-desconocido split; adult/games still use public lists). It's a plain allowlist: one domain per line, a leading dot `.edu.pe` = suffix rule matching any subdomain. Grow it as legit domains show up as `desconocido` in reports.
- **Downloads** — read the `downloads` table inside the same `History` DB (not a separate file); flag `.apk`/`.exe`/`.zip` from untrusted domains. `watchdog` on `Descargas`/`Escritorio`/`Documentos` as a secondary source.
- **Recycle bin — deletions** — `watchdog` on `C:\$Recycle.Bin\<SID>\`; on each new `$I*` file, parse its binary header for original path, size, and deletion time (FILETIME). This captures files deleted from **any path** (not just Downloads) — it's how Windows records every send-to-recycle-bin. At report time, [src/report/correlate.py](src/report/correlate.py) joins each deletion to the day's `downloads` by basename, so the report can say e.g. "tarea.pdf: downloaded 18:10, deleted 18:20 (10 min later)" — evidence the user deleted their own file rather than someone else. Rendered as its own **"Papelera — archivos eliminados"** table, distinct from the empty event below.
- **Recycle bin — empty event** — detected separately: several `$I`/`$R` pairs disappearing together in a short window (heuristic in spec §3.5). This module specifically needs `watchdog`, not polling, for accuracy. Rendered as a separate **"Papelera — vaciada"** table.

Report/delivery (spec §5–§7):
- One HTML table per module. **Every** categorized row carries a rounded **"pill" badge** (all four categories, `normal` and `desconocido` included), rendered via `render_pill()` from [src/categories.py](src/categories.py) — badge the item, don't just highlight the row. Rows also get a soft category-colored background (`row_background()`); `normal` is the only category with no highlight. Two event flags reuse the same pill system: `sospechoso` (suspicious `.apk`/`.exe`/`.zip` download) and `papelera_vaciada`. Pill styles are **inline** (email clients strip `<style>`).
- Optional `.xlsx` via `openpyxl`, one sheet per module.
- **One email/day** via user-configured generic SMTP (config file, never hardcoded). If the PC was off for days, combine pending days into **a single email with per-date sections**. No immediate alerts for now — but keep the code organized so an immediate-alert mode can be added later without a redesign.

## Non-obvious technical decisions (read before touching the relevant module)

- **Locked history DB**: the browser `History` file is locked while the browser runs → **copy it to a temp file first**, then open with `sqlite3`. Applies to both history and downloads reads.
- **Timezone**: store *all* timestamps in **UTC** internally; convert to `ZoneInfo("America/Lima")` (fixed UTC-5, no DST) only when rendering the report. Use stdlib `zoneinfo`.
- **Crash resilience**: persist the day's captured events to a **local SQLite/JSON state file** so the report can be rebuilt if the process restarts mid-day. The ~30-min loop checks whether it's time to send/consolidate.
- **Per-user paths**: the monitored user's `%LOCALAPPDATA%`/`%APPDATA%`/`$Recycle.Bin\<SID>` must be resolved from the *chosen minor's* SID (registry `ProfileList` → `ProfileImagePath`), because the process runs as SYSTEM, not the logged-in user — its own env vars point at SYSTEM's profile. Implemented in [src/winprofile.py](src/winprofile.py) (`resolve_user_paths(sid)`), used by `monitor_pc.resolve_user_paths()` and by browser/recycle collectors. Test-mode tools fall back to the current user's `os.environ`.
- **Install as SYSTEM** (spec §8): the Scheduled Task triggers *at the minor's logon* but *runs as* `SYSTEM` with a neutral task name so the standard account can't easily see or stop it. The install `.ps1` must enumerate local users (`Get-LocalUser`) so the admin picks the minor's account. Identical procedure on Win10/11.

## Tooling (planned stack, spec §10)

`psutil` (processes), stdlib `sqlite3` (browser DBs), `watchdog` (file/recycle-bin monitoring), `openpyxl` (Excel), stdlib `smtplib`+`email` (mail), stdlib `zoneinfo` (timezone). The `$I` recycle-bin parser is custom (documented binary format, no library). Package headless with `pythonw.exe` or PyInstaller.

## Repo hygiene (spec §9 — enforce in `.gitignore`)

Never commit: real `config.ini`, `*.log`, generated reports, or any local `.db`/`.sqlite` state. Only `config.example.ini` (template without secrets) belongs in the repo.
