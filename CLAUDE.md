# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Early scaffolding. The module tree exists under [src/](src/) as **stubs** (docstrings + signatures + `TODO`s referencing spec sections); most collectors/report/mailer functions raise `NotImplementedError` and are the actual work ahead. The design spec ([docs/monitor_pc_spec.md](docs/monitor_pc_spec.md)) is the source of truth — read it before implementing. Section 11 is a ready-to-paste build prompt; section 12 lists decisions already locked in (don't relitigate them).

Already implemented (safe foundations): [src/config.py](src/config.py) (config.ini loader), [src/utils/timeutil.py](src/utils/timeutil.py) (UTC/Lima + FILETIME/Chrome-time conversions), [src/state.py](src/state.py) (SQLite schema), the `$I` header parser in [src/collectors/recycle_bin.py](src/collectors/recycle_bin.py), [src/categories.py](src/categories.py) (risk categories + pill/row styles + `render_pill`), **`DomainCategorizer.categorize()`** in [src/collectors/domain_categories.py](src/collectors/domain_categories.py) (fully working: hostlists + suffix rules + keyword fallback), and [src/report/correlate.py](src/report/correlate.py) (download↔deletion matching). Run [tools/preview_report.py](tools/preview_report.py) to render a sample report (it categorizes domains live via the real categorizer) and eyeball the badges.

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
- **Processes** — `psutil` poll; pair open/close events to compute **total accumulated time per app** for the day (not just a raw event list).
- **Browser history + categorization** — read Chromium `History` SQLite (Chrome/Edge share the schema at `%LOCALAPPDATA%\...\User Data\Default\History`; Firefox `places.sqlite` if easy). Categorize each domain into one of four risk categories using **public reference hostlists** (e.g. StevenBlack/OISD) plus keyword heuristics as fallback — **no hand-curated domain list**. Categories + their pill/row colors live in [src/categories.py](src/categories.py) (the single source of truth, shared by web domains *and* the app/process table): `adulto` (🔞 red), `juegos` (🎮 orange), `normal` (• gray), `desconocido` (🔍 violet). **Unmatched → `desconocido`, not `normal`**: anything not confirmed by a reference list is flagged for review rather than assumed safe. This replaces the spec's original `dudoso/otros`. `normal` requires a match against [data/known_sites.txt](data/known_sites.txt) — **the one hand-curated list in the project** (the user's explicit decision, only for the normal-vs-desconocido split; adult/games still use public lists). It's a plain allowlist: one domain per line, a leading dot `.edu.pe` = suffix rule matching any subdomain. Grow it as legit domains show up as `desconocido` in reports.
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
- **Per-user paths**: the monitored user's `%LOCALAPPDATA%` and `$Recycle.Bin\<SID>` must be resolved from the *chosen minor's* SID, because the process may run under a different execution context (SYSTEM) than the logged-in user.
- **Install as SYSTEM** (spec §8): the Scheduled Task triggers *at the minor's logon* but *runs as* `SYSTEM` with a neutral task name so the standard account can't easily see or stop it. The install `.ps1` must enumerate local users (`Get-LocalUser`) so the admin picks the minor's account. Identical procedure on Win10/11.

## Tooling (planned stack, spec §10)

`psutil` (processes), stdlib `sqlite3` (browser DBs), `watchdog` (file/recycle-bin monitoring), `openpyxl` (Excel), stdlib `smtplib`+`email` (mail), stdlib `zoneinfo` (timezone). The `$I` recycle-bin parser is custom (documented binary format, no library). Package headless with `pythonw.exe` or PyInstaller.

## Repo hygiene (spec §9 — enforce in `.gitignore`)

Never commit: real `config.ini`, `*.log`, generated reports, or any local `.db`/`.sqlite` state. Only `config.example.ini` (template without secrets) belongs in the repo.
