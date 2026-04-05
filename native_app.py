from __future__ import annotations

import queue
import subprocess
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox, ttk

from port_runtime import build_port_command, command_to_string


THEMES: dict[str, dict[str, str]] = {
    "light": {
        "bg": "#fbf6f8",
        "panel": "#fffcfd",
        "panel_alt": "#fff9fb",
        "panel_border": "#ebdde5",
        "field": "#fffdfd",
        "field_border": "#e8d8e1",
        "entry_bg": "#fffafb",
        "text": "#3f2f3a",
        "muted": "#8d7d88",
        "accent": "#d392ad",
        "accent_soft": "#b17994",
        "ok": "#6f9f8a",
        "warn": "#ba9368",
        "danger": "#bf758c",
        "idle": "#9c8b97",
        "queued": "#b0998f",
        "meta_bg": "#f8eef3",
        "preview_bg": "#f8f0f4",
        "preview_fg": "#6d5061",
        "log_bg": "#2f2735",
        "log_fg": "#faeef5",
        "notice_info_bg": "#f8edf2",
        "notice_info_fg": "#825f71",
        "notice_ok_bg": "#eaf5ef",
        "notice_ok_fg": "#4f7a66",
        "notice_warn_bg": "#f8f1e6",
        "notice_warn_fg": "#886a47",
        "notice_danger_bg": "#f8eaf0",
        "notice_danger_fg": "#986274",
        "button_primary_bg": "#d392ad",
        "button_primary_active_bg": "#c5819d",
        "button_primary_fg": "#ffffff",
        "button_secondary_bg": "#f2e8ee",
        "button_secondary_active_bg": "#e5d8e0",
        "button_secondary_fg": "#3f2f3a",
        "button_stop_bg": "#cea1b0",
        "button_stop_active_bg": "#bc8a9c",
        "button_stop_fg": "#ffffff",
        "button_ghost_bg": "#f4e9ef",
        "button_ghost_active_bg": "#e7d9e2",
        "button_ghost_fg": "#3f2f3a",
        "status_badge_fg": "#fffafc",
        "disabled_primary_fg": "#f3e4ec",
        "disabled_secondary_fg": "#b19faa",
        "disabled_stop_fg": "#f3e2e7",
        "toggle_active_bg": "#e8d8e2",
        "toggle_inactive_bg": "#f8eff3",
        "toggle_active_fg": "#4f3a47",
        "toggle_inactive_fg": "#937d8c",
        "toggle_border": "#ddccd6",
        "theme_label": "#8a6880",
    },
    "dark": {
        "bg": "#000000",
        "panel": "#000000",
        "panel_alt": "#000000",
        "panel_border": "#ff1616",
        "field": "#000000",
        "field_border": "#ff2a2a",
        "entry_bg": "#000000",
        "text": "#f4f4f4",
        "muted": "#b4b4b4",
        "accent": "#ff1f1f",
        "accent_soft": "#00f5ff",
        "ok": "#00ff9f",
        "warn": "#ffd400",
        "danger": "#ff4f4f",
        "idle": "#ff3a3a",
        "queued": "#ff5a2b",
        "meta_bg": "#000000",
        "preview_bg": "#000000",
        "preview_fg": "#82ffff",
        "log_bg": "#000000",
        "log_fg": "#39ff14",
        "notice_info_bg": "#060606",
        "notice_info_fg": "#7af8ff",
        "notice_ok_bg": "#03110c",
        "notice_ok_fg": "#41ffb6",
        "notice_warn_bg": "#161003",
        "notice_warn_fg": "#ffd65a",
        "notice_danger_bg": "#1a0404",
        "notice_danger_fg": "#ff8d8d",
        "button_primary_bg": "#ff1f1f",
        "button_primary_active_bg": "#da1212",
        "button_primary_fg": "#ffffff",
        "button_secondary_bg": "#040404",
        "button_secondary_active_bg": "#141414",
        "button_secondary_fg": "#c9fdff",
        "button_stop_bg": "#8f0909",
        "button_stop_active_bg": "#6e0404",
        "button_stop_fg": "#ffffff",
        "button_ghost_bg": "#030303",
        "button_ghost_active_bg": "#131313",
        "button_ghost_fg": "#b9fffb",
        "status_badge_fg": "#ffffff",
        "disabled_primary_fg": "#8a4a4a",
        "disabled_secondary_fg": "#5f7273",
        "disabled_stop_fg": "#6f4343",
        "toggle_active_bg": "#0d0d0d",
        "toggle_inactive_bg": "#000000",
        "toggle_active_fg": "#95ffef",
        "toggle_inactive_fg": "#ff8f8f",
        "toggle_border": "#ff1c1c",
        "theme_label": "#ff9f9f",
    },
}

GLOW_COLORS: tuple[str, ...] = (
    "#ff1a1a",
    "#ff004d",
    "#ff00ff",
    "#8f00ff",
    "#00a2ff",
    "#00ffee",
    "#00ff66",
    "#f6ff00",
    "#ff5a00",
)


def theme_palette(theme_name: str) -> dict[str, str]:
    return THEMES.get(theme_name, THEMES["light"]).copy()


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
        self.theme_mode = "light"
        self.palette = theme_palette(self.theme_mode)

        self.root = tk.Tk()
        self.root.title("ReVork Port Studio")
        self.root.geometry("1360x900")
        self.root.minsize(1180, 780)
        self.root.configure(bg=self.palette["bg"])

        self.font_roles = {
            "heading": self._resolve_font_family("Anntons", "Anton", "Impact", "Segoe UI"),
            "logo": self._resolve_font_family("Haverbrooke", "Haverbrook", "Georgia", "Times New Roman"),
            "body": self._resolve_font_family("Poppions", "Poppins", "Segoe UI"),
            "mono": self._resolve_font_family("Consolas", "Cascadia Mono", "Courier New"),
        }

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
        self.theme_mode_var = tk.StringVar(value=self.theme_mode)

        self.status_var = tk.StringVar(value="idle")
        self.notice_var = tk.StringVar(value="Ready. Configure paths and start a job.")
        self.job_id_var = tk.StringVar(value="-")
        self.started_var = tk.StringVar(value="-")
        self.finished_var = tk.StringVar(value="-")
        self.return_code_var = tk.StringVar(value="-")
        self.command_preview_var = tk.StringVar(value="")
        self.notice_level = "info"

        self.start_btn: tk.Button | None = None
        self.dry_run_btn: tk.Button | None = None
        self.stop_btn: tk.Button | None = None
        self.log_box: tk.Text | None = None
        self.status_badge: tk.Label | None = None
        self.notice_label: tk.Label | None = None
        self.command_box: tk.Text | None = None
        self.theme_light_btn: tk.Button | None = None
        self.theme_dark_btn: tk.Button | None = None
        self.ui_outer: tk.Frame | None = None
        self.glow_widgets: list[tk.Widget] = []
        self.glow_after_id: str | None = None
        self.glow_index = 0

        self._build_ui()
        self.command_preview_var.trace_add("write", self._sync_command_preview)
        self._bind_live_preview()
        self._refresh_command_preview()
        self._set_status("idle")

        self.root.after(120, self._pump_events)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _resolve_font_family(self, *candidates: str) -> str:
        try:
            available = {name.casefold(): name for name in tkfont.families(self.root)}
            for candidate in candidates:
                match = available.get(candidate.casefold())
                if match:
                    return match
        except tk.TclError:
            pass
        return candidates[0] if candidates else "Segoe UI"

    def _font(self, role: str, size: int, weight: str = "normal") -> tuple[str, int] | tuple[str, int, str]:
        family = self.font_roles.get(role, self.font_roles["body"])
        if weight == "normal":
            return (family, size)
        return (family, size, weight)

    def _border_thickness(self) -> int:
        return 2 if self.theme_mode == "dark" else 1

    def _register_glow_widget(self, widget: tk.Widget) -> None:
        self.glow_widgets.append(widget)

    def _stop_glow_animation(self) -> None:
        if self.glow_after_id is None:
            return
        try:
            self.root.after_cancel(self.glow_after_id)
        except tk.TclError:
            pass
        self.glow_after_id = None

    def _apply_glow_color(self, color: str) -> None:
        alive: list[tk.Widget] = []
        for widget in self.glow_widgets:
            try:
                widget.configure(highlightbackground=color, highlightcolor=color)
                alive.append(widget)
            except tk.TclError:
                continue
        self.glow_widgets = alive

    def _start_or_refresh_glow(self) -> None:
        self._stop_glow_animation()
        if self.theme_mode != "dark":
            self._apply_glow_color(self.palette["panel_border"])
            return

        self.glow_index = 0
        self._animate_glow()

    def _animate_glow(self) -> None:
        if self.theme_mode != "dark":
            return

        color = GLOW_COLORS[self.glow_index % len(GLOW_COLORS)]
        self.glow_index += 1
        self._apply_glow_color(color)
        self.glow_after_id = self.root.after(140, self._animate_glow)

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
        frame = tk.Frame(
            parent,
            bg=bg,
            highlightthickness=self._border_thickness(),
            highlightbackground=self.palette["panel_border"],
            highlightcolor=self.palette["panel_border"],
        )
        self._register_glow_widget(frame)
        return frame

    def _build_ui(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "ReVork.TCombobox",
            fieldbackground=self.palette["field"],
            background=self.palette["field"],
            foreground=self.palette["text"],
            arrowcolor=self.palette["accent_soft"],
            bordercolor=self.palette["field_border"],
        )
        style.map(
            "ReVork.TCombobox",
            fieldbackground=[("readonly", self.palette["field"])],
            foreground=[("readonly", self.palette["text"])],
            selectforeground=[("readonly", self.palette["text"])],
            selectbackground=[("readonly", self.palette["field"])],
        )

        self.glow_widgets = []

        outer = tk.Frame(self.root, bg=self.palette["bg"])
        outer.pack(fill="both", expand=True, padx=20, pady=18)
        self.ui_outer = outer

        self._build_header(outer)

        self.notice_label = tk.Label(
            outer,
            textvariable=self.notice_var,
            font=self._font("body", 10, "bold"),
            fg=self.palette["notice_info_fg"],
            bg=self.palette["notice_info_bg"],
            anchor="w",
            padx=14,
            pady=9,
            relief="flat",
            bd=0,
        )
        self.notice_label.pack(fill="x", pady=(12, 12))

        content = tk.Frame(outer, bg=self.palette["bg"])
        content.pack(fill="both", expand=True)
        content.grid_columnconfigure(0, weight=45)
        content.grid_columnconfigure(1, weight=55)
        content.grid_rowconfigure(0, weight=1)

        left_panel = self._create_panel(content, self.palette["panel"])
        right_panel = self._create_panel(content, self.palette["panel_alt"])
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self._build_form(left_panel)
        self._build_monitor(right_panel)
        self._style_theme_toggle_buttons()
        self._set_notice(self.notice_var.get(), self.notice_level)
        self._start_or_refresh_glow()

    def _build_header(self, parent: tk.Widget) -> None:
        header = self._create_panel(parent, self.palette["panel"])
        header.pack(fill="x")

        body = tk.Frame(header, bg=self.palette["panel"])
        body.pack(fill="x", padx=18, pady=14)

        if self.header_logo_image is not None:
            tk.Label(body, image=self.header_logo_image, bg=self.palette["panel"]).pack(side="left", padx=(0, 14))

        text_col = tk.Frame(body, bg=self.palette["panel"])
        text_col.pack(side="left", fill="x", expand=True)

        tk.Label(
            text_col,
            text="REVORK STUDIO",
            font=self._font("logo", 11, "bold"),
            fg=self.palette["accent_soft"],
            bg=self.palette["panel"],
        ).pack(anchor="w")

        tk.Label(
            text_col,
            text="Dreamlight Port Studio",
            font=self._font("logo", 30, "bold"),
            fg=self.palette["text"],
            bg=self.palette["panel"],
        ).pack(anchor="w", pady=(2, 0))

        tk.Label(
            text_col,
            text="Calm workflow inspired by soft pop visuals, with full control over WSL and Bash runtime.",
            font=self._font("body", 10),
            fg=self.palette["muted"],
            bg=self.palette["panel"],
        ).pack(anchor="w", pady=(2, 0))

        toggle_col = tk.Frame(body, bg=self.palette["panel"])
        toggle_col.pack(side="right", anchor="n", padx=(16, 0))

        tk.Label(
            toggle_col,
            text="Theme",
            font=self._font("body", 9, "bold"),
            fg=self.palette["theme_label"],
            bg=self.palette["panel"],
        ).pack(anchor="e")

        toggle_row = tk.Frame(
            toggle_col,
            bg=self.palette["panel"],
            highlightthickness=self._border_thickness(),
            highlightbackground=self.palette["toggle_border"],
            padx=4,
            pady=4,
        )
        toggle_row.pack(anchor="e", pady=(6, 0))
        self._register_glow_widget(toggle_row)

        self.theme_light_btn = tk.Button(
            toggle_row,
            text="Light Calm",
            font=self._font("body", 9, "bold"),
            relief="flat",
            bd=0,
            padx=10,
            pady=5,
            command=lambda: self._change_theme("light"),
        )
        self.theme_light_btn.pack(side="left", padx=(0, 6))

        self.theme_dark_btn = tk.Button(
            toggle_row,
            text="Dark Neon",
            font=self._font("body", 9, "bold"),
            relief="flat",
            bd=0,
            padx=10,
            pady=5,
            command=lambda: self._change_theme("dark"),
        )
        self.theme_dark_btn.pack(side="left")

    def _build_form(self, parent: tk.Frame) -> None:
        body = tk.Frame(parent, bg=self.palette["panel"])
        body.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(
            body,
            text="Job Setup",
            font=self._font("heading", 17, "bold"),
            fg=self.palette["text"],
            bg=self.palette["panel"],
        ).pack(anchor="w")

        tk.Label(
            body,
            text="Fill ROM sources and runtime options before starting.",
            font=self._font("body", 10),
            fg=self.palette["muted"],
            bg=self.palette["panel"],
        ).pack(anchor="w", pady=(0, 10))

        fields = tk.Frame(body, bg=self.palette["panel"])
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

        button_row = tk.Frame(body, bg=self.palette["panel"])
        button_row.pack(fill="x", pady=(12, 0))

        self.start_btn = tk.Button(
            button_row,
            text="Start Job",
            font=self._font("body", 10, "bold"),
            fg=self.palette["button_primary_fg"],
            bg=self.palette["button_primary_bg"],
            activebackground=self.palette["button_primary_active_bg"],
            activeforeground=self.palette["button_primary_fg"],
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
            font=self._font("body", 10, "bold"),
            fg=self.palette["button_secondary_fg"],
            bg=self.palette["button_secondary_bg"],
            activebackground=self.palette["button_secondary_active_bg"],
            activeforeground=self.palette["button_secondary_fg"],
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
            font=self._font("body", 10, "bold"),
            fg=self.palette["button_stop_fg"],
            bg=self.palette["button_stop_bg"],
            activebackground=self.palette["button_stop_active_bg"],
            activeforeground=self.palette["button_stop_fg"],
            relief="flat",
            bd=0,
            padx=14,
            pady=8,
            command=self._stop_job,
        )
        self.stop_btn.pack(side="left")

    def _build_monitor(self, parent: tk.Frame) -> None:
        body = tk.Frame(parent, bg=self.palette["panel_alt"])
        body.pack(fill="both", expand=True, padx=16, pady=16)

        top = tk.Frame(body, bg=self.palette["panel_alt"])
        top.pack(fill="x")

        tk.Label(
            top,
            text="Execution Monitor",
            font=self._font("heading", 17, "bold"),
            fg=self.palette["text"],
            bg=self.palette["panel_alt"],
        ).pack(side="left")

        self.status_badge = tk.Label(
            top,
            textvariable=self.status_var,
            font=self._font("body", 10, "bold"),
            fg=self.palette["status_badge_fg"],
            bg=self.palette["idle"],
            padx=11,
            pady=4,
        )
        self.status_badge.pack(side="right")

        meta = tk.Frame(body, bg=self.palette["panel_alt"])
        meta.pack(fill="x", pady=(12, 10))

        self._meta_pair(meta, "Job ID", self.job_id_var, 0, 0)
        self._meta_pair(meta, "Return Code", self.return_code_var, 0, 1)
        self._meta_pair(meta, "Started", self.started_var, 1, 0)
        self._meta_pair(meta, "Finished", self.finished_var, 1, 1)

        preview_head = tk.Frame(body, bg=self.palette["panel_alt"])
        preview_head.pack(fill="x", pady=(4, 4))

        tk.Label(
            preview_head,
            text="Command Preview",
            font=self._font("heading", 10, "bold"),
            fg=self.palette["accent_soft"],
            bg=self.palette["panel_alt"],
        ).pack(side="left")

        tk.Button(
            preview_head,
            text="Copy",
            font=self._font("body", 9, "bold"),
            fg=self.palette["button_ghost_fg"],
            bg=self.palette["button_ghost_bg"],
            activebackground=self.palette["button_ghost_active_bg"],
            activeforeground=self.palette["button_ghost_fg"],
            relief="flat",
            bd=0,
            padx=10,
            pady=4,
            command=self._copy_command_preview,
        ).pack(side="right")

        self.command_box = tk.Text(
            body,
            height=4,
            bg=self.palette["preview_bg"],
            fg=self.palette["preview_fg"],
            insertbackground=self.palette["preview_fg"],
            relief="flat",
            bd=0,
            wrap="word",
            padx=10,
            pady=10,
            font=self._font("mono", 10),
        )
        self.command_box.pack(fill="x")
        self.command_box.configure(state="disabled")

        log_head = tk.Frame(body, bg=self.palette["panel_alt"])
        log_head.pack(fill="x", pady=(10, 6))

        tk.Label(
            log_head,
            text="Live Logs",
            font=self._font("heading", 12, "bold"),
            fg=self.palette["accent_soft"],
            bg=self.palette["panel_alt"],
        ).pack(side="left")

        tk.Button(
            log_head,
            text="Clear View",
            font=self._font("body", 9, "bold"),
            fg=self.palette["button_ghost_fg"],
            bg=self.palette["button_ghost_bg"],
            activebackground=self.palette["button_ghost_active_bg"],
            activeforeground=self.palette["button_ghost_fg"],
            relief="flat",
            bd=0,
            padx=10,
            pady=4,
            command=self._clear_logs,
        ).pack(side="right")

        logs_wrap = tk.Frame(body, bg=self.palette["panel_alt"])
        logs_wrap.pack(fill="both", expand=True)

        self.log_box = tk.Text(
            logs_wrap,
            wrap="none",
            bg=self.palette["log_bg"],
            fg=self.palette["log_fg"],
            insertbackground=self.palette["log_fg"],
            relief="flat",
            bd=0,
            padx=12,
            pady=12,
            font=self._font("mono", 9),
        )
        self.log_box.pack(side="left", fill="both", expand=True)

        scroll_y = ttk.Scrollbar(logs_wrap, orient="vertical", command=self.log_box.yview)
        scroll_y.pack(side="right", fill="y")
        self.log_box.configure(yscrollcommand=scroll_y.set)

        self._append_log("[log] Waiting for a job...")

    def _add_entry(self, parent: tk.Frame, label: str, variable: tk.StringVar) -> None:
        field = tk.Frame(
            parent,
            bg=self.palette["field"],
            highlightthickness=self._border_thickness(),
            highlightbackground=self.palette["field_border"],
        )
        field.pack(fill="x", pady=(0, 10))
        self._register_glow_widget(field)

        tk.Label(
            field,
            text=label,
            font=self._font("body", 9, "bold"),
            fg=self.palette["accent_soft"],
            bg=self.palette["field"],
        ).pack(anchor="w", padx=10, pady=(8, 2))

        tk.Entry(
            field,
            textvariable=variable,
            font=self._font("body", 10),
            bg=self.palette["entry_bg"],
            fg=self.palette["text"],
            insertbackground=self.palette["text"],
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
            bg=self.palette["field"],
            highlightthickness=self._border_thickness(),
            highlightbackground=self.palette["field_border"],
        )
        field.pack(fill="x", pady=(0, 10))
        self._register_glow_widget(field)

        tk.Label(
            field,
            text=label,
            font=self._font("body", 9, "bold"),
            fg=self.palette["accent_soft"],
            bg=self.palette["field"],
        ).pack(anchor="w", padx=10, pady=(8, 2))

        combo = ttk.Combobox(
            field,
            textvariable=variable,
            values=values,
            state="readonly",
            font=self._font("body", 10),
            style="ReVork.TCombobox",
        )
        combo.pack(fill="x", padx=10, pady=(0, 6), ipady=3)

        tk.Label(
            field,
            text=hint,
            font=self._font("body", 8),
            fg=self.palette["muted"],
            bg=self.palette["field"],
        ).pack(anchor="w", padx=10, pady=(0, 8))

    def _meta_pair(self, parent: tk.Frame, label: str, value: tk.StringVar, row: int, col: int) -> None:
        frame = tk.Frame(
            parent,
            bg=self.palette["meta_bg"],
            highlightthickness=self._border_thickness(),
            highlightbackground=self.palette["panel_border"],
            padx=10,
            pady=8,
        )
        frame.grid(row=row, column=col, sticky="nsew", padx=(0, 10), pady=(0, 8))
        self._register_glow_widget(frame)

        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)

        tk.Label(
            frame,
            text=label,
            font=self._font("body", 8, "bold"),
            fg=self.palette["accent_soft"],
            bg=self.palette["meta_bg"],
        ).pack(anchor="w")

        tk.Label(
            frame,
            textvariable=value,
            font=self._font("body", 9),
            fg=self.palette["text"],
            bg=self.palette["meta_bg"],
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

    def _style_theme_toggle_buttons(self) -> None:
        buttons = {
            "light": self.theme_light_btn,
            "dark": self.theme_dark_btn,
        }
        for mode, button in buttons.items():
            if button is None:
                continue
            selected = mode == self.theme_mode
            button.configure(
                bg=self.palette["toggle_active_bg"] if selected else self.palette["toggle_inactive_bg"],
                fg=self.palette["toggle_active_fg"] if selected else self.palette["toggle_inactive_fg"],
                activebackground=self.palette["toggle_active_bg"],
                activeforeground=self.palette["toggle_active_fg"],
            )

    def _change_theme(self, mode: str) -> None:
        if mode not in THEMES or mode == self.theme_mode:
            return

        current_logs = ""
        if self.log_box is not None:
            current_logs = self.log_box.get("1.0", "end-1c")

        self.theme_mode = mode
        self.theme_mode_var.set(mode)
        self.palette = theme_palette(mode)
        self.root.configure(bg=self.palette["bg"])
        self._stop_glow_animation()

        if self.ui_outer is not None:
            self.ui_outer.destroy()
            self.ui_outer = None

        self._build_ui()
        self._set_status(self.status_var.get())
        self._sync_command_preview()

        if self.log_box is None:
            return

        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        if current_logs.strip():
            self.log_box.insert("1.0", current_logs + "\n")
            self.log_box.see("end")
        else:
            self._append_log("[log] Waiting for a job...")

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
        self.notice_level = level
        self.notice_var.set(message)
        if not self.notice_label:
            return

        if level == "ok":
            self.notice_label.configure(
                bg=self.palette["notice_ok_bg"],
                fg=self.palette["notice_ok_fg"],
            )
        elif level == "warn":
            self.notice_label.configure(
                bg=self.palette["notice_warn_bg"],
                fg=self.palette["notice_warn_fg"],
            )
        elif level == "danger":
            self.notice_label.configure(
                bg=self.palette["notice_danger_bg"],
                fg=self.palette["notice_danger_fg"],
            )
        else:
            self.notice_label.configure(
                bg=self.palette["notice_info_bg"],
                fg=self.palette["notice_info_fg"],
            )

    def _set_status(self, status: str) -> None:
        status = status.lower()
        self.status_var.set(status)

        if self.status_badge is not None:
            color_map = {
                "idle": self.palette["idle"],
                "queued": self.palette["queued"],
                "running": self.palette["ok"],
                "completed": self.palette["ok"],
                "failed": self.palette["danger"],
                "stopping": self.palette["warn"],
                "stopped": self.palette["warn"],
            }
            self.status_badge.configure(
                bg=color_map.get(status, self.palette["idle"]),
                fg=self.palette["status_badge_fg"],
            )

        running = status in {"queued", "running", "stopping"}
        if self.start_btn is not None:
            self.start_btn.configure(
                state="disabled" if running else "normal",
                disabledforeground=self.palette["disabled_primary_fg"],
            )
        if self.dry_run_btn is not None:
            self.dry_run_btn.configure(
                state="disabled" if running else "normal",
                disabledforeground=self.palette["disabled_secondary_fg"],
            )
        if self.stop_btn is not None:
            self.stop_btn.configure(
                state="normal" if running else "disabled",
                disabledforeground=self.palette["disabled_stop_fg"],
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

        self._stop_glow_animation()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = NativePortApp()
    app.run()


if __name__ == "__main__":
    main()
