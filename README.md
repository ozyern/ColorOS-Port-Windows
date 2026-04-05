# ColorOS-Port-Windows

Windows-first UI wrapper for ColorOS/OxygenOS porting workflows.

This repository starts with a desktop-friendly web UI that launches your existing `port.sh` pipeline from Windows (Git Bash), shows live logs, supports dry-run previews, and lets you stop running jobs.

## What You Get

- Flask backend job runner API
- Modern responsive frontend (no terminal-only workflow)
- Live log streaming and status tracking
- Dry run mode to verify command construction
- One-click launcher for Windows (`start_ui.bat`)

## Current Scope (MVP)

- Uses your existing script flow instead of replacing it.
- Executes `bash <script> <baserom> <portrom> [portrom2] [portparts]`.
- Best run path on Windows is Git for Windows (Git Bash) + Python 3.

## Project Layout

```
ColorOS-Port-Windows/
	app.py
	requirements.txt
	start_ui.bat
	templates/
		index.html
	static/
		css/styles.css
		js/app.js
```

## Quick Start (Windows 10/11)

1. Install Python 3.10+.
2. Install Git for Windows (includes `bash`).
3. Clone this repo.
4. Double-click `start_ui.bat`.
5. Open `http://127.0.0.1:7878`.

`start_ui.bat` creates `.venv`, installs requirements, and launches the server.

## Manual Start

```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## UI Fields

- Base ROM zip/url: required
- Port ROM zip/url: required
- Second source ROM: optional
- Second source partitions: optional
- Workspace path: folder where your script/files exist
- Script path: script to execute (default: `port.sh`)
- Bash command/path: command to run bash (default: `bash`)

## Notes

- If your script or tools are not in this repo yet, set the workspace/script paths to where they are.
- Dry run does not execute anything; it only validates and previews the command.
- Live logs show stdout/stderr merged from the running process.

## Next Steps

- Add file pickers for ROM paths
- Add preset device profiles
- Add per-step progress model
- Add native PowerShell runner path (reduce shell friction on Windows)
- Add packaged desktop app build
