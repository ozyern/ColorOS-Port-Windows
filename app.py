from __future__ import annotations

import os
import shlex
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

jobs: dict[str, dict[str, Any]] = {}
jobs_lock = threading.Lock()
TERMINAL_STATUSES = {"completed", "failed", "stopped"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def command_to_string(command: list[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(command)
    return shlex.join(command)


def append_log(job_id: str, line: str) -> None:
    clean_line = line.rstrip("\r\n")
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return
        job["logs"].append(clean_line)


def make_job_payload(job: dict[str, Any], from_line: int = 0) -> dict[str, Any]:
    from_line = max(from_line, 0)
    all_logs = job.get("logs", [])
    delta_logs = all_logs[from_line:]

    return {
        "id": job["id"],
        "status": job["status"],
        "createdAt": job["created_at"],
        "startedAt": job.get("started_at"),
        "finishedAt": job.get("finished_at"),
        "cwd": job["cwd"],
        "command": job["command"],
        "commandString": job["command_string"],
        "returnCode": job.get("return_code"),
        "error": job.get("error"),
        "logs": delta_logs,
        "nextFrom": from_line + len(delta_logs),
        "logCount": len(all_logs),
    }


def build_port_command(payload: dict[str, Any]) -> tuple[list[str], Path]:
    base_rom = (payload.get("baseRom") or "").strip()
    port_rom = (payload.get("portRom") or "").strip()
    port_rom2 = (payload.get("portRom2") or "").strip()
    port_parts = (payload.get("portParts") or "").strip()

    if not base_rom or not port_rom:
        raise ValueError("baseRom and portRom are required.")

    workspace_raw = (payload.get("workspace") or ".").strip()
    workspace = Path(workspace_raw).expanduser().resolve()
    if not workspace.exists():
        raise ValueError(f"Workspace not found: {workspace}")

    script_raw = (payload.get("scriptPath") or "port.sh").strip()
    script_path = Path(script_raw)
    if not script_path.is_absolute():
        script_path = workspace / script_path
    script_path = script_path.resolve()
    if not script_path.exists():
        raise ValueError(f"Script not found: {script_path}")

    bash_path = (payload.get("bashPath") or "bash").strip()
    command: list[str] = [bash_path, str(script_path), base_rom, port_rom]

    if port_rom2:
        command.append(port_rom2)
    elif port_parts:
        # Keep positional args aligned with port.sh usage.
        command.append("")

    if port_parts:
        command.append(port_parts)

    return command, workspace


def run_job(job_id: str, command: list[str], cwd: Path) -> None:
    with jobs_lock:
        job = jobs[job_id]
        job["status"] = "running"
        job["started_at"] = utc_now_iso()

    append_log(job_id, f"[info] Working directory: {cwd}")
    append_log(job_id, f"[info] Command: {command_to_string(command)}")

    process: subprocess.Popen[str] | None = None

    try:
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        with jobs_lock:
            jobs[job_id]["process"] = process

        if process.stdout is not None:
            for line in process.stdout:
                append_log(job_id, line)

        return_code = process.wait()

        with jobs_lock:
            job = jobs[job_id]
            job["return_code"] = return_code
            job["finished_at"] = utc_now_iso()
            if job["status"] == "stopping":
                job["status"] = "stopped"
            elif return_code == 0:
                job["status"] = "completed"
            else:
                job["status"] = "failed"

    except Exception as exc:
        with jobs_lock:
            job = jobs[job_id]
            job["status"] = "failed"
            job["error"] = str(exc)
            job["finished_at"] = utc_now_iso()
        append_log(job_id, f"[error] {exc}")

    finally:
        with jobs_lock:
            job = jobs.get(job_id)
            if job is not None:
                job["process"] = None


def create_job(command: list[str], cwd: Path) -> dict[str, Any]:
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "status": "queued",
        "created_at": utc_now_iso(),
        "started_at": None,
        "finished_at": None,
        "cwd": str(cwd),
        "command": command,
        "command_string": command_to_string(command),
        "return_code": None,
        "error": None,
        "logs": [],
        "process": None,
    }

    with jobs_lock:
        jobs[job_id] = job

    worker = threading.Thread(target=run_job, args=(job_id, command, cwd), daemon=True)
    worker.start()
    return job


@app.get("/")
def index() -> str:
    repo_root = Path(__file__).resolve().parent
    defaults = {
        "workspace": str(repo_root),
        "scriptPath": "port.sh",
        "bashPath": "bash",
    }
    return render_template("index.html", defaults=defaults)


@app.get("/api/health")
def health() -> Any:
    return jsonify({"ok": True, "time": utc_now_iso()})


@app.post("/api/jobs")
def start_job() -> Any:
    payload = request.get_json(silent=True) or {}

    try:
        command, cwd = build_port_command(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    dry_run = bool(payload.get("dryRun", False))
    if dry_run:
        job_id = str(uuid.uuid4())
        dry_job = {
            "id": job_id,
            "status": "completed",
            "created_at": utc_now_iso(),
            "started_at": utc_now_iso(),
            "finished_at": utc_now_iso(),
            "cwd": str(cwd),
            "command": command,
            "command_string": command_to_string(command),
            "return_code": 0,
            "error": None,
            "logs": [
                "[dry-run] No process started.",
                f"[dry-run] Working directory: {cwd}",
                f"[dry-run] Command: {command_to_string(command)}",
            ],
            "process": None,
        }
        with jobs_lock:
            jobs[job_id] = dry_job
        return jsonify(make_job_payload(dry_job, from_line=0)), 201

    job = create_job(command, cwd)
    return jsonify(make_job_payload(job, from_line=0)), 201


@app.get("/api/jobs/<job_id>")
def get_job(job_id: str) -> Any:
    from_line = request.args.get("from", default="0")
    try:
        from_line_num = max(0, int(from_line))
    except ValueError:
        from_line_num = 0

    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return jsonify({"error": f"Job not found: {job_id}"}), 404
        payload = make_job_payload(job, from_line=from_line_num)

    return jsonify(payload)


@app.post("/api/jobs/<job_id>/stop")
def stop_job(job_id: str) -> Any:
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return jsonify({"error": f"Job not found: {job_id}"}), 404

        process: subprocess.Popen[str] | None = job.get("process")
        if process is None or process.poll() is not None:
            return jsonify({"message": "Job is not running.", "status": job["status"]}), 200

        job["status"] = "stopping"

    try:
        process.terminate()
        append_log(job_id, "[info] Stop requested by user.")
    except Exception as exc:
        append_log(job_id, f"[warn] Stop request failed: {exc}")
        return jsonify({"error": str(exc)}), 500

    return jsonify({"message": "Stop signal sent.", "status": "stopping"}), 202


if __name__ == "__main__":
    port = int(os.getenv("PORT", "7878"))
    app.run(host="127.0.0.1", port=port, debug=False)
