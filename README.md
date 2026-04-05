# ColorOS-Port-Windows

Windows-first ColorOS/OxygenOS porting workspace with a native desktop app, optional web UI, and a hidden bundled porting engine.

This repository includes the desktop app UI, web UI, and the core shell-based porting pipeline in `.revork_engine/` so Linux-facing internals stay out of the main project surface.

## What You Get

- Native desktop UI runner (`native_app.py`) for daily use
- Flask backend + modern web frontend (optional)
- Live log streaming and status tracking
- Dry run mode to verify command construction
- One-click launcher for Windows (`start_ui.bat`) with `ReVork.exe`
- Hidden bundled engine folder (`.revork_engine/`) containing `port.sh`, `functions.sh`, `bin/`, `devices/`, `otatools/`
- EXE build script (`build_exe.bat`) for desktop packaging

## Current Scope

- Executes `<runner> <script> <baserom> <portrom> [portrom2] [portparts]`.
- Defaults target `.revork_engine/port.sh` through the hidden engine workspace.
- Supports explicit runtime mode:
	- `wsl`: runs through WSL (`wsl bash -lc ...`) for true Linux execution.
	- `bash`: runs through your configured bash command (for example Git Bash).

## Project Layout

```
ColorOS-Port-Windows/
	app.py
	native_app.py
	.revork_engine/
		port.sh
		functions.sh
		setup.sh
		bin/
		devices/
		otatools/
	requirements.txt
	ReVork.exe
	start_ui.bat
	start_web_ui.bat
	build_exe.bat
	templates/
		index.html
	static/
		css/styles.css
		js/app.js
```

## Quick Start (Windows 10/11)

1. Install Python 3.10+.
2. Install WSL (recommended) or Git for Windows (bash mode).
3. Clone this repo.
4. Double-click `start_ui.bat`.
5. The native desktop app opens.

`start_ui.bat` launches `ReVork.exe` (or `dist\\ReVork.exe`) when it exists; otherwise it creates `.venv`, installs requirements, and launches `native_app.py`.

## Optional Web UI

Run `start_web_ui.bat`, then open `http://127.0.0.1:7878`.

## Manual Start

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python native_app.py
```

## Build EXE

Run `build_exe.bat`.

Output EXE:

- `dist\ReVork.exe`
- `ReVork.exe`

## UI Fields

- Base ROM zip/url: required
- Port ROM zip/url: required
- Second source ROM: optional
- Second source partitions: optional
- Workspace path: folder where your script/files exist
- Script path: script to execute (default: `port.sh`)
- Runtime mode: `wsl` or `bash`
- Runner command/path: command to invoke selected runtime (default: `wsl`)

## Runtime Reality Check (Linux vs Windows)

- This porting pipeline is Linux-oriented (`.revork_engine/setup.sh` installs Linux packages; many tools are Linux binaries).
- In `wsl` mode, the job runs inside real Linux userspace (WSL), which is the recommended and reliable path.
- In `bash` mode, it runs through your Windows bash command (for example Git Bash), but Linux-only tools may still fail depending on your environment.

## Notes

- Dry run does not execute anything; it only validates and previews the command.
- Live logs show stdout/stderr merged from the running process.
- Keep `workspace` set to `.revork_engine` unless you intentionally run a different script.
- Engine-specific documentation from the original shell project is available in `.revork_engine/PORT_ENGINE_README.md`.

## Next Steps

- Add file pickers for ROM paths
- Add preset device profiles
- Add per-step progress model
- Add native PowerShell runner path (reduce shell friction on Windows)
- Add packaged desktop app build
