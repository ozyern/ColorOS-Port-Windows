from __future__ import annotations

import queue
import subprocess
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from port_runtime import build_port_command, command_to_string


PALETTE = {
    "bg": "#070b12",
    "panel": "#121a26",
    "panel_alt": "#0f1620",
    "panel_border": "#243246",
    "field": "#0c121b",
    "field_border": "#2a3b52",
    "text": "#eef3fb",
    "muted": "#9aabc3",
    "accent": "#ff6f3d",
    "accent_soft": "#ff9d75",
    "ok": "#1f9c66",
    "warn": "#b7832d",
    "danger": "#b54843",
    "idle": "#5f6e82",
}


def app_root_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resolve_asset_path(app_root: Path, relative: Path) -> Path:
    if getattr(sys, "frozen", False):
        bundled = Path(getattr(sys, "_MEIPASS", app_root)) / relative
        if bundled.exists():
            return bundled
    return app_root / relative


class NativePortApp:
    def __init__(self) -> None:
        self.app_root = app_root_dir()

        self.root = tk.Tk()
        self.root.title("ReVork Port Studio")
        self.root.geometry("1360x900")
        self.root.minsize(1180, 780)
        self.root.configure(bg=PALETTE["bg"])

        self.icon_image: tk.PhotoImage | None = None
        self.header_logo_image: tk.PhotoImage | None = None
        self._set_window_icon()

        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.proc_lock = threading.Lock()
        self.process: subprocess.Popen[str] | None = None
        self.stop_requested = False

        self.base_rom_var = tk.StringVar()
        self.port_rom_var = tk.StringVar()
        self.port_rom2_var = tk.StringVar()
        self.port_parts_var = tk.StringVar()
        engine_root = self.app_root / ".revork_engine"
        default_workspace = engine_root if engine_root.exists() else self.app_root
        self.workspace_var = tk.StringVar(value=str(default_workspace))
        self.script_path_var = tk.StringVar(value="port.sh")
        self.runner_mode_var = tk.StringVar(value="wsl")
        self.runner_cmd_var = tk.StringVar(value="wsl")

        self.status_var = tk.StringVar(value="idle")
        self.notice_var = tk.StringVar(value="Ready. Configure paths and start a job.")
        self.job_id_var = tk.StringVar(value="-")
        self.started_var = tk.StringVar(value="-")
        self.finished_var = tk.StringVar(value="-")
        self.return_code_var = tk.StringVar(value="-")
        self.command_preview_var = tk.StringVar(value="")

        self.start_btn: tk.Button | None = None
        self.dry_run_btn: tk.Button | None = None
        self.stop_btn: tk.Button | None = None
        self.log_box: tk.Text | None = None
        self.status_badge: tk.Label | None = None
        self.notice_label: tk.Label | None = None
        self.command_box: tk.Text | None = None

        self._build_ui()
        self.command_preview_var.trace_add("write", self._sync_command_preview)
        self._bind_live_preview()
        self._refresh_command_preview()
        self._set_status("idle")

        self.root.after(120, self._pump_events)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_window_icon(self) -> None:
        logo_path = resolve_asset_path(self.app_root, Path("static") / "logo.png")
        if not logo_path.exists():
            return

        try:
            self.icon_image = tk.PhotoImage(file=str(logo_path))
            self.root.iconphoto(True, self.icon_image)
            ratio = max(1, self.icon_image.width() // 90)
            self.header_logo_image = self.icon_image.subsample(ratio, ratio)
        except tk.TclError:
            self.icon_image = None
            self.header_logo_image = None

    def _create_panel(self, parent: tk.Widget, bg: str) -> tk.Frame:
        return tk.Frame(
            parent,
            bg=bg,
            highlightthickness=1,
            highlightbackground=PALETTE["panel_border"],
            highlightcolor=PALETTE["panel_border"],
        )

    def _build_ui(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "ReVork.TCombobox",
            fieldbackground=PALETTE["field"],
            background=PALETTE["field"],
            foreground=PALETTE["text"],
            arrowcolor=PALETTE["accent_soft"],
            bordercolor=PALETTE["field_border"],
        )
        style.map(
            "ReVork.TCombobox",
            fieldbackground=[("readonly", PALETTE["field"])],
            foreground=[("readonly", PALETTE["text"])],
            selectforeground=[("readonly", PALETTE["text"])],
            selectbackground=[("readonly", PALETTE["field"])],
        )

        outer = tk.Frame(self.root, bg=PALETTE["bg"])
        outer.pack(fill="both", expand=True, padx=20, pady=18)

        self._build_header(outer)

        self.notice_label = tk.Label(
            outer,
            textvariable=self.notice_var,
            font=("Segoe UI", 10, "bold"),
            fg="#ffcdb9",
            bg="#28140f",
            anchor="w",
            padx=14,
            pady=9,
            relief="flat",
            bd=0,
        )
        self.notice_label.pack(fill="x", pady=(12, 12))

        content = tk.Frame(outer, bg=PALETTE["bg"])
        content.pack(fill="both", expand=True)
        content.grid_columnconfigure(0, weight=45)
        content.grid_columnconfigure(1, weight=55)
        content.grid_rowconfigure(0, weight=1)

        left_panel = self._create_panel(content, PALETTE["panel"])
        right_panel = self._create_panel(content, PALETTE["panel_alt"])
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self._build_form(left_panel)
        self._build_monitor(right_panel)

    def _build_header(self, parent: tk.Widget) -> None:
        header = self._create_panel(parent, PALETTE["panel"])
        header.pack(fill="x")

        body = tk.Frame(header, bg=PALETTE["panel"])
        body.pack(fill="x", padx=18, pady=14)

        if self.header_logo_image is not None:
            tk.Label(body, image=self.header_logo_image, bg=PALETTE["panel"]).pack(side="left", padx=(0, 14))

        text_col = tk.Frame(body, bg=PALETTE["panel"])
        text_col.pack(side="left", fill="x", expand=True)

        tk.Label(
            text_col,
            text="REVORK STUDIO",
            font=("Segoe UI Semibold", 11),
            fg=PALETTE["accent_soft"],
            bg=PALETTE["panel"],
        ).pack(anchor="w")

        tk.Label(
            text_col,
            text="Port Command Center",
            font=("Segoe UI", 30, "bold"),
            fg=PALETTE["text"],
            bg=PALETTE["panel"],
        ).pack(anchor="w", pady=(2, 0))

        tk.Label(
            text_col,
            text="Sharper layout, cleaner controls, and direct control over WSL vs Bash runtime.",
            font=("Segoe UI", 10),
            fg=PALETTE["muted"],
            bg=PALETTE["panel"],
        ).pack(anchor="w", pady=(2, 0))

    def _build_form(self, parent: tk.Frame) -> None:
        body = tk.Frame(parent, bg=PALETTE["panel"])
        body.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(
            body,
            text="Job Setup",
            font=("Segoe UI", 18, "bold"),
            fg=PALETTE["text"],
            bg=PALETTE["panel"],
        ).pack(anchor="w")

        tk.Label(
            body,
            text="Fill ROM sources and runtime options before starting.",
            font=("Segoe UI", 10),
            fg=PALETTE["muted"],
            bg=PALETTE["panel"],
        ).pack(anchor="w", pady=(0, 10))

        fields = tk.Frame(body, bg=PALETTE["panel"])
        fields.pack(fill="both", expand=True)

        self._add_entry(fields, "Base ROM zip/url", self.base_rom_var)
        self._add_entry(fields, "Port ROM zip/url", self.port_rom_var)
        self._add_entry(fields, "Second source ROM (optional)", self.port_rom2_var)
        self._add_entry(fields, "Second source partitions (optional)", self.port_parts_var)
        self._add_entry(fields, "Workspace path", self.workspace_var)
        self._add_entry(fields, "Script path", self.script_path_var)
        self._add_combo(
            fields,
            "Runtime mode",
            self.runner_mode_var,
            values=("wsl", "bash"),
            hint="wsl uses real Linux userspace. bash uses your selected shell command.",
        )
        self._add_entry(fields, "Runner command/path", self.runner_cmd_var)

        button_row = tk.Frame(body, bg=PALETTE["panel"])
        button_row.pack(fill="x", pady=(12, 0))

        self.start_btn = tk.Button(
            button_row,
            text="Start Job",
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg=PALETTE["accent"],
            activebackground="#ea5d2f",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=14,
            pady=8,
            command=lambda: self._start_job(dry_run=False),
        )
        self.start_btn.pack(side="left", padx=(0, 8))

        self.dry_run_btn = tk.Button(
            button_row,
            text="Dry Run",
            font=("Segoe UI", 10, "bold"),
            fg=PALETTE["text"],
            bg="#1f2a3a",
            activebackground="#2a3750",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=14,
            pady=8,
            command=lambda: self._start_job(dry_run=True),
        )
        self.dry_run_btn.pack(side="left", padx=(0, 8))

        self.stop_btn = tk.Button(
            button_row,
            text="Stop",
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg="#7e2a28",
            activebackground="#692120",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=14,
            pady=8,
            command=self._stop_job,
        )
        self.stop_btn.pack(side="left")

    def _build_monitor(self, parent: tk.Frame) -> None:
        body = tk.Frame(parent, bg=PALETTE["panel_alt"])
        body.pack(fill="both", expand=True, padx=16, pady=16)

        top = tk.Frame(body, bg=PALETTE["panel_alt"])
        top.pack(fill="x")

        tk.Label(
            top,
            text="Execution Monitor",
            font=("Segoe UI", 18, "bold"),
            fg=PALETTE["text"],
            bg=PALETTE["panel_alt"],
        ).pack(side="left")

        self.status_badge = tk.Label(
            top,
            textvariable=self.status_var,
            font=("Segoe UI", 10, "bold"),
            fg="#f2f7ff",
            bg=PALETTE["idle"],
            padx=11,
            pady=4,
        )
        self.status_badge.pack(side="right")

        meta = tk.Frame(body, bg=PALETTE["panel_alt"])
        meta.pack(fill="x", pady=(12, 10))

        self._meta_pair(meta, "Job ID", self.job_id_var, 0, 0)
        self._meta_pair(meta, "Return Code", self.return_code_var, 0, 1)
        self._meta_pair(meta, "Started", self.started_var, 1, 0)
        self._meta_pair(meta, "Finished", self.finished_var, 1, 1)

        preview_head = tk.Frame(body, bg=PALETTE["panel_alt"])
        preview_head.pack(fill="x", pady=(4, 4))

        tk.Label(
            preview_head,
            text="Command Preview",
            font=("Segoe UI", 10, "bold"),
            fg=PALETTE["accent_soft"],
            bg=PALETTE["panel_alt"],
        ).pack(side="left")

        tk.Button(
            preview_head,
            text="Copy",
            font=("Segoe UI", 9, "bold"),
            fg=PALETTE["text"],
            bg="#203044",
            activebackground="#2a3f5a",
            relief="flat",
            bd=0,
            padx=10,
            pady=4,
            command=self._copy_command_preview,
        ).pack(side="right")

        self.command_box = tk.Text(
            body,
            height=4,
            bg="#0b121c",
            fg="#f1d8cc",
            insertbackground="#f1d8cc",
            relief="flat",
            bd=0,
            wrap="word",
            padx=10,
            pady=10,
            font=("Consolas", 10),
        )
        self.command_box.pack(fill="x")
        self.command_box.configure(state="disabled")

        log_head = tk.Frame(body, bg=PALETTE["panel_alt"])
        log_head.pack(fill="x", pady=(10, 6))

        tk.Label(
            log_head,
            text="Live Logs",
            font=("Segoe UI", 12, "bold"),
            fg=PALETTE["accent_soft"],
            bg=PALETTE["panel_alt"],
        ).pack(side="left")

        tk.Button(
            log_head,
            text="Clear View",
            font=("Segoe UI", 9, "bold"),
            fg=PALETTE["text"],
            bg="#2a3342",
            activebackground="#364154",
            relief="flat",
            bd=0,
            padx=10,
            pady=4,
            command=self._clear_logs,
        ).pack(side="right")

        logs_wrap = tk.Frame(body, bg=PALETTE["panel_alt"])
        logs_wrap.pack(fill="both", expand=True)

        self.log_box = tk.Text(
            logs_wrap,
            wrap="none",
            bg="#090e15",
            fg="#c4f7d9",
            insertbackground="#c4f7d9",
            relief="flat",
            bd=0,
            padx=12,
            pady=12,
            font=("Consolas", 9),
        )
        self.log_box.pack(side="left", fill="both", expand=True)

        scroll_y = ttk.Scrollbar(logs_wrap, orient="vertical", command=self.log_box.yview)
        scroll_y.pack(side="right", fill="y")
        self.log_box.configure(yscrollcommand=scroll_y.set)

        self._append_log("[log] Waiting for a job...")

    def _add_entry(self, parent: tk.Frame, label: str, variable: tk.StringVar) -> None:
        field = tk.Frame(
            parent,
            bg=PALETTE["field"],
            highlightthickness=1,
            highlightbackground=PALETTE["field_border"],
        )
        field.pack(fill="x", pady=(0, 10))

        tk.Label(
            field,
            text=label,
            font=("Segoe UI", 9, "bold"),
            fg=PALETTE["accent_soft"],
            bg=PALETTE["field"],
        ).pack(anchor="w", padx=10, pady=(8, 2))

        tk.Entry(
            field,
            textvariable=variable,
            font=("Consolas", 10),
            bg="#0b121c",
            fg=PALETTE["text"],
            insertbackground=PALETTE["text"],
            relief="flat",
            bd=0,
        ).pack(fill="x", padx=10, pady=(0, 9), ipady=6)

    def _add_combo(
        self,
        parent: tk.Frame,
        label: str,
        variable: tk.StringVar,
        values: tuple[str, ...],
        hint: str,
    ) -> None:
        field = tk.Frame(
            parent,
            bg=PALETTE["field"],
            highlightthickness=1,
            highlightbackground=PALETTE["field_border"],
        )
        field.pack(fill="x", pady=(0, 10))

        tk.Label(
            field,
            text=label,
            font=("Segoe UI", 9, "bold"),
            fg=PALETTE["accent_soft"],
            bg=PALETTE["field"],
        ).pack(anchor="w", padx=10, pady=(8, 2))

        combo = ttk.Combobox(
            field,
            textvariable=variable,
            values=values,
            state="readonly",
            font=("Consolas", 10),
            style="ReVork.TCombobox",
        )
        combo.pack(fill="x", padx=10, pady=(0, 6), ipady=3)

        tk.Label(
            field,
            text=hint,
            font=("Segoe UI", 8),
            fg=PALETTE["muted"],
            bg=PALETTE["field"],
        ).pack(anchor="w", padx=10, pady=(0, 8))

    def _meta_pair(self, parent: tk.Frame, label: str, value: tk.StringVar, row: int, col: int) -> None:
        frame = tk.Frame(
            parent,
            bg="#111a27",
            highlightthickness=1,
            highlightbackground=PALETTE["panel_border"],
            padx=10,
            pady=8,
        )
        frame.grid(row=row, column=col, sticky="nsew", padx=(0, 10), pady=(0, 8))

        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)

        tk.Label(
            frame,
            text=label,
            font=("Segoe UI", 8, "bold"),
            fg=PALETTE["accent_soft"],
            bg="#111a27",
        ).pack(anchor="w")

        tk.Label(
            frame,
            textvariable=value,
            font=("Consolas", 9),
            fg=PALETTE["text"],
            bg="#111a27",
            wraplength=330,
            justify="left",
        ).pack(anchor="w", pady=(3, 0))

    def _sync_command_preview(self, *_: object) -> None:
        if self.command_box is None:
            return

        self.command_box.configure(state="normal")
        self.command_box.delete("1.0", "end")
        self.command_box.insert("1.0", self.command_preview_var.get())
        self.command_box.configure(state="disabled")

    def _copy_command_preview(self) -> None:
        preview = self.command_preview_var.get().strip()
        if not preview:
            self._set_notice("No command to copy yet.", "warn")
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(preview)
        self._set_notice("Command copied to clipboard.", "ok")

    def _bind_live_preview(self) -> None:
        tracked = [
            self.base_rom_var,
            self.port_rom_var,
            self.port_rom2_var,
            self.port_parts_var,
            self.workspace_var,
            self.script_path_var,
            self.runner_mode_var,
            self.runner_cmd_var,
        ]
        for var in tracked:
            var.trace_add("write", self._refresh_command_preview)

    def _set_notice(self, message: str, level: str = "info") -> None:
        self.notice_var.set(message)
        if not self.notice_label:
            return

        if level == "ok":
            self.notice_label.configure(bg="#12301f", fg="#aef0ce")
        elif level == "warn":
            self.notice_label.configure(bg="#312311", fg="#ffdca8")
        elif level == "danger":
            self.notice_label.configure(bg="#341513", fg="#ffc1bd")
        else:
            self.notice_label.configure(bg="#291710", fg="#ffcdb9")

    def _set_status(self, status: str) -> None:
        status = status.lower()
        self.status_var.set(status)

        if self.status_badge is not None:
            color_map = {
                "idle": PALETTE["idle"],
                "queued": "#6f5b47",
                "running": PALETTE["ok"],
                "completed": PALETTE["ok"],
                "failed": PALETTE["danger"],
                "stopping": PALETTE["warn"],
                "stopped": PALETTE["warn"],
            }
            self.status_badge.configure(bg=color_map.get(status, PALETTE["idle"]))

        running = status in {"queued", "running", "stopping"}
        if self.start_btn is not None:
            self.start_btn.configure(
                state="disabled" if running else "normal",
                disabledforeground="#f4d0bf",
            )
        if self.dry_run_btn is not None:
            self.dry_run_btn.configure(
                state="disabled" if running else "normal",
                disabledforeground="#b3bdd0",
            )
        if self.stop_btn is not None:
            self.stop_btn.configure(
                state="normal" if running else "disabled",
                disabledforeground="#e6c5c3",
            )

    def _payload(self) -> dict[str, str]:
        return {
            "baseRom": self.base_rom_var.get().strip(),
            "portRom": self.port_rom_var.get().strip(),
            "portRom2": self.port_rom2_var.get().strip(),
            "portParts": self.port_parts_var.get().strip(),
            "workspace": self.workspace_var.get().strip(),
            "scriptPath": self.script_path_var.get().strip(),
            "bashPath": self.runner_cmd_var.get().strip(),
            "runnerMode": self.runner_mode_var.get().strip(),
        }

    def _refresh_command_preview(self, *_: object) -> None:
        payload = self._payload()
        if not payload["baseRom"] or not payload["portRom"]:
            self.command_preview_var.set(
                "Runner command will appear once Base ROM and Port ROM are set."
            )
            return

        try:
            command, _cwd = build_port_command(payload)
        except ValueError as exc:
            self.command_preview_var.set(f"[preview pending] {exc}")
            return

        self.command_preview_var.set(command_to_string(command))

    def _append_log(self, line: str) -> None:
        if self.log_box is None:
            return
        self.log_box.insert("end", line.rstrip("\r\n") + "\n")
        self.log_box.see("end")

    def _clear_logs(self) -> None:
        if self.log_box is None:
            return
        self.log_box.delete("1.0", "end")
        self._append_log("[log] Cleared. Waiting for output...")

    def _start_job(self, dry_run: bool) -> None:
        payload = self._payload()
        try:
            command, cwd = build_port_command(payload)
        except ValueError as exc:
            self._set_notice(str(exc), "warn")
            return

        self.command_preview_var.set(command_to_string(command))
        self.job_id_var.set(str(uuid.uuid4()))
        self.started_var.set(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.finished_var.set("-")
        self.return_code_var.set("-")

        self._clear_logs()
        self._append_log(f"[info] Working directory: {cwd}")
        self._append_log(f"[info] Command: {command_to_string(command)}")

        if dry_run:
            self._append_log("[dry-run] No process started.")
            self._set_status("completed")
            self.finished_var.set(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            self.return_code_var.set("0")
            self._set_notice("Dry run completed.", "ok")
            return

        self.stop_requested = False
        self._set_status("queued")
        self._set_notice("Starting port job...", "info")

        worker = threading.Thread(target=self._run_job_worker, args=(command, cwd), daemon=True)
        worker.start()

    def _run_job_worker(self, command: list[str], cwd: Path) -> None:
        self.events.put(("status", "running"))
        try:
            proc = subprocess.Popen(
                command,
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            with self.proc_lock:
                self.process = proc

            if proc.stdout is not None:
                for line in proc.stdout:
                    self.events.put(("log", line))

            code = proc.wait()
            self.events.put(("finished", code))
        except Exception as exc:
            self.events.put(("error", str(exc)))
        finally:
            with self.proc_lock:
                self.process = None

    def _stop_job(self) -> None:
        with self.proc_lock:
            proc = self.process

        if proc is None or proc.poll() is not None:
            self._set_notice("No running process to stop.", "warn")
            return

        self.stop_requested = True
        self._set_status("stopping")
        self._set_notice("Stop signal sent.", "warn")
        self._append_log("[info] Stop requested by user.")

        try:
            proc.terminate()
        except Exception as exc:
            self._set_notice(f"Failed to stop process: {exc}", "danger")

    def _pump_events(self) -> None:
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break

            if kind == "status":
                self._set_status(str(payload))
            elif kind == "log":
                self._append_log(str(payload))
            elif kind == "error":
                self._set_status("failed")
                self.finished_var.set(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                self._append_log(f"[error] {payload}")
                self._set_notice(f"Job failed: {payload}", "danger")
            elif kind == "finished":
                code = int(payload)
                self.return_code_var.set(str(code))
                self.finished_var.set(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                if self.stop_requested:
                    self._set_status("stopped")
                    self._set_notice("Job stopped by user.", "warn")
                elif code == 0:
                    self._set_status("completed")
                    self._set_notice("Job completed successfully.", "ok")
                else:
                    self._set_status("failed")
                    self._set_notice("Job failed. Check logs for details.", "danger")

        self.root.after(120, self._pump_events)

    def _on_close(self) -> None:
        with self.proc_lock:
            running = self.process is not None and self.process.poll() is None

        if running:
            should_exit = messagebox.askyesno(
                "Exit",
                "A porting job is still running. Stop it and close the app?",
            )
            if not should_exit:
                return
            self._stop_job()

        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = NativePortApp()
    app.run()


if __name__ == "__main__":
    main()
