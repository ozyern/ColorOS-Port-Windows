# ColorOS-Port-Windows

Windows-first ColorOS/OxygenOS porting workspace with a built-in UI and bundled porting engine.

This repository includes the web UI and the core shell-based porting pipeline (`port.sh`, helper scripts, tools, and device data) so you can run everything from this one folder.

## What You Get

- Flask backend job runner API
- Modern responsive frontend (no terminal-only workflow)
- Live log streaming and status tracking
- Dry run mode to verify command construction
- One-click launcher for Windows (`start_ui.bat`)
- Bundled porting engine files (`port.sh`, `functions.sh`, `bin/`, `devices/`, `otatools/`)

## Current Scope

- Executes `bash <script> <baserom> <portrom> [portrom2] [portparts]`.
- Defaults target the local `port.sh` in this repo.
- Best run path on Windows is Git for Windows (Git Bash) + Python 3.

## Project Layout

```
ColorOS-Port-Windows/
	app.py
	port.sh
	functions.sh
	setup.sh
	bin/
	devices/
	otatools/
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

- Dry run does not execute anything; it only validates and previews the command.
- Live logs show stdout/stderr merged from the running process.
- Keep `workspace` set to this repo root unless you intentionally run a different script.
- Engine-specific documentation from the original shell project is available in `PORT_ENGINE_README.md`.

## Next Steps

- Add file pickers for ROM paths
- Add preset device profiles
- Add per-step progress model
- Add native PowerShell runner path (reduce shell friction on Windows)
- Add packaged desktop app build
