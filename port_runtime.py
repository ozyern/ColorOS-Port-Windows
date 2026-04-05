from __future__ import annotations

import os
import re
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def command_to_string(command: list[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(command)
    return shlex.join(command)


def _is_url(value: str) -> bool:
    return bool(re.match(r"^https?://", value, flags=re.IGNORECASE))


def _looks_like_windows_path(value: str) -> bool:
    return bool(re.match(r"^[a-zA-Z]:[\\/]", value)) or "\\" in value


def _to_wsl_path(path: Path) -> str:
    path = path.resolve()
    if os.name != "nt":
        return path.as_posix()

    if path.drive:
        drive = path.drive.rstrip(":").lower()
        posix = path.as_posix()
        suffix = posix.split(":/", 1)[1] if ":/" in posix else posix
        return f"/mnt/{drive}/{suffix}"

    return path.as_posix()


def _resolve_maybe_path(raw: str, workspace: Path) -> Path | None:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate.resolve()

    if _looks_like_windows_path(raw) or "/" in raw or "\\" in raw or raw.startswith("."):
        return (workspace / candidate).resolve()

    workspace_candidate = (workspace / candidate).resolve()
    if workspace_candidate.exists():
        return workspace_candidate

    return None


def _adapt_argument_for_wsl(raw: str, workspace: Path) -> str:
    if _is_url(raw):
        return raw

    resolved = _resolve_maybe_path(raw, workspace)
    if resolved is None:
        return raw

    return _to_wsl_path(resolved)


def _build_wsl_command(
    runner_cmd: str,
    workspace: Path,
    script_path: Path,
    base_rom: str,
    port_rom: str,
    port_rom2: str,
    port_parts: str,
) -> list[str]:
    workspace_wsl = _to_wsl_path(workspace)
    script_wsl = _to_wsl_path(script_path)

    base_arg = _adapt_argument_for_wsl(base_rom, workspace)
    port_arg = _adapt_argument_for_wsl(port_rom, workspace)

    args = [script_wsl, base_arg, port_arg]

    if port_rom2:
        args.append(_adapt_argument_for_wsl(port_rom2, workspace))
    elif port_parts:
        args.append("")

    if port_parts:
        args.append(port_parts)

    quoted_args = " ".join(shlex.quote(part) for part in args)
    shell_command = f"cd {shlex.quote(workspace_wsl)} && bash {quoted_args}"

    return [runner_cmd, "bash", "-lc", shell_command]


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

    runner_mode = (payload.get("runnerMode") or payload.get("runner") or "bash").strip().lower()
    runner_cmd = (payload.get("bashPath") or "bash").strip()

    if runner_mode not in {"bash", "wsl"}:
        raise ValueError("runnerMode must be either 'bash' or 'wsl'.")

    if runner_mode == "wsl":
        if not runner_cmd:
            runner_cmd = "wsl"
        command = _build_wsl_command(
            runner_cmd=runner_cmd,
            workspace=workspace,
            script_path=script_path,
            base_rom=base_rom,
            port_rom=port_rom,
            port_rom2=port_rom2,
            port_parts=port_parts,
        )
        return command, workspace

    if not runner_cmd:
        runner_cmd = "bash"

    command: list[str] = [runner_cmd, str(script_path), base_rom, port_rom]

    if port_rom2:
        command.append(port_rom2)
    elif port_parts:
        command.append("")

    if port_parts:
        command.append(port_parts)

    return command, workspace
