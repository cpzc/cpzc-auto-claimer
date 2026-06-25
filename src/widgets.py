"""Custom tkinter widgets — SidebarButton and LogPanel."""

import re as _re
from datetime import datetime

import customtkinter as ctk

from src.config import FONT_FAMILY, FONT_FAMILY_MONO, _log_lock, get_app_instance
from src.themes import COLORS


class SidebarButton(ctk.CTkButton):
    def __init__(self, master, text="", command=None, icon="", **kwargs):
        super().__init__(
            master,
            text=f" {icon}  {text}" if icon else text,
            command=command,
            fg_color="transparent",
            text_color=COLORS["text_dim"],
            hover_color=COLORS["sidebar_active"],
            anchor="w",
            height=44,
            corner_radius=8,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            **kwargs,
        )
        self.active = False

    def set_active(self, active):
        self.active = active
        if active:
            self.configure(fg_color=COLORS["sidebar_active"], text_color=COLORS["accent"])
        else:
            self.configure(fg_color="transparent", text_color=COLORS["text_dim"])


class LogPanel(ctk.CTkFrame):
    _ANSI_COLORS = {
        "30": "#888888", "31": "#cf6679", "32": "#03dac6", "33": "#ffab40",
        "34": "#82b1ff", "35": "#ea80fc", "36": "#80cbc4", "37": "#e8dff5",
        "90": "#555555", "91": "#ff5252", "92": "#69f0ae", "93": "#ffd740",
        "94": "#82b1ff", "95": "#ea80fc", "96": "#a7ffeb", "97": "#ffffff",
    }
    _ANSI_RE = _re.compile(r"\x1b\[([0-9;]*)m")

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=COLORS["card"], corner_radius=10, **kwargs)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 0))

        ctk.CTkLabel(
            header, text="Output Log",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(side="left")

        ctk.CTkButton(
            header, text="Clear", width=60, height=26,
            fg_color=COLORS["border"], hover_color=COLORS["error"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            command=self.clear,
        ).pack(side="right")

        self.textbox = ctk.CTkTextbox(
            self,
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(family=FONT_FAMILY_MONO, size=11),
            corner_radius=6,
            border_width=1,
            border_color=COLORS["border"],
            state="disabled",
        )
        self.textbox.pack(fill="both", expand=True, padx=10, pady=(6, 10))

        self._setup_tags()
        self._poll()

    def _setup_tags(self):
        tw = self.textbox._textbox
        tw.tag_configure("timestamp", foreground="#555555")
        for code, color in self._ANSI_COLORS.items():
            tw.tag_configure(f"ansi_{code}", foreground=color)
        tw.tag_configure("ansi_reset", foreground=COLORS["text"])

    def _poll(self):
        inst = get_app_instance()
        if inst and hasattr(inst, "_log_queue"):
            with _log_lock:
                while inst._log_queue:
                    msg = inst._log_queue.pop(0)
                    self._append(msg)
        self.after(50, self._poll)

    def _append(self, message):
        tw = self.textbox._textbox
        self.textbox.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        tw.insert("end", f"[{timestamp}] ", ("timestamp",))

        parts = self._ANSI_RE.split(message)
        codes = self._ANSI_RE.findall(message)
        current_tags = []

        for i, part in enumerate(parts):
            if not part:
                continue
            if i < len(codes):
                code_str = codes[i]
                if code_str == "0" or code_str == "":
                    current_tags = []
                else:
                    for c in code_str.split(";"):
                        if c in self._ANSI_COLORS:
                            current_tags = [f"ansi_{c}"]
            if part:
                tags = tuple(current_tags) if current_tags else ()
                tw.insert("end", part, tags)

        tw.insert("end", "\n")
        tw.see("end")
        self.textbox.configure(state="disabled")

    def log(self, message):
        self._append(message)

    def clear(self):
        self.textbox.configure(state="normal")
        self.textbox._textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")
