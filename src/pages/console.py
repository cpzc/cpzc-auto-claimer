"""Console page — full-screen log output with line counter."""

import customtkinter as ctk

from src.config import FONT_FAMILY, FONT_FAMILY_MONO
from src.themes import COLORS
from src.widgets import LogPanel


class ConsolePage(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header, text="Console",
            font=ctk.CTkFont(family=FONT_FAMILY, size=28, weight="bold"),
            text_color=COLORS["text"],
        ).pack(side="left")

        self.counter_label = ctk.CTkLabel(
            header, text="0 lines",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=COLORS["text_dim"],
        )
        self.counter_label.pack(side="left", padx=(12, 0))

        ctk.CTkButton(
            header, text="Clear", width=80, height=32,
            fg_color=COLORS["border"], hover_color=COLORS["error"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=lambda: self.app.log_panel.clear(),
        ).pack(side="right")

        self.textbox = ctk.CTkTextbox(
            self,
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(family=FONT_FAMILY_MONO, size=12),
            corner_radius=10,
            border_width=1,
            border_color=COLORS["border"],
            state="disabled",
        )
        self.textbox.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self._setup_tags()
        self._last_len = 0
        self._poll()

    def _setup_tags(self):
        tw = self.textbox._textbox
        tw.tag_configure("timestamp", foreground="#555555")
        for code, color in LogPanel._ANSI_COLORS.items():
            tw.tag_configure(f"ansi_{code}", foreground=color)

    def _poll(self):
        if self.app.log_panel:
            src = self.app.log_panel.textbox._textbox
            line_count = int(src.index("end-1c").split(".")[0])
            if line_count != self._last_len:
                self._last_len = line_count
                count = max(0, line_count - 1)
                self.counter_label.configure(text=f"{count} lines")
                dst = self.textbox._textbox
                self.textbox.configure(state="normal")
                dst.delete("1.0", "end")
                dst.insert("1.0", src.get("1.0", "end"))
                for tag_name in src.tag_names():
                    if tag_name == "sel":
                        continue
                    ranges = src.tag_ranges(tag_name)
                    for i in range(0, len(ranges), 2):
                        dst.tag_add(tag_name, ranges[i], ranges[i + 1])
                dst.see("end")
                self.textbox.configure(state="disabled")
        self.after(100, self._poll)
