"""Username generator page — configurable generation with save to file."""

import os
import random
import string
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from src.config import SCRIPT_DIR, FONT_FAMILY, FONT_FAMILY_MONO
from src.themes import COLORS


class GeneratePage(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            scroll, text="Generate Usernames",
            font=ctk.CTkFont(family=FONT_FAMILY, size=28, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(0, 20))

        card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            card, text="Configuration",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w", padx=16, pady=(12, 8))

        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(row1, text="Character Set:", font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                      text_color=COLORS["text"]).pack(side="left")
        self.charset_var = ctk.StringVar(value="both")
        ctk.CTkOptionMenu(
            row1, variable=self.charset_var,
            values=["letters", "numbers", "both"],
            width=120, height=30, corner_radius=6,
            fg_color=COLORS["input_bg"],
            button_color=COLORS["border"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
        ).pack(side="left", padx=(8, 0))

        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=4)

        for label, default, attr in [("Min Length:", "4", "min_len"), ("Max Length:", "6", "max_len"), ("Count:", "1000", "count")]:
            ctk.CTkLabel(row2, text=label, font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                          text_color=COLORS["text"]).pack(side="left", padx=(0, 4))
            var = ctk.StringVar(value=default)
            setattr(self, f"_{attr}_var", var)
            ctk.CTkEntry(
                row2, textvariable=var, width=70, height=30,
                fg_color=COLORS["input_bg"], border_color=COLORS["border"],
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            ).pack(side="left", padx=(0, 12))

        row3 = ctk.CTkFrame(card, fg_color="transparent")
        row3.pack(fill="x", padx=16, pady=(4, 12))

        ctk.CTkLabel(row3, text="Prefix:", font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                      text_color=COLORS["text"]).pack(side="left")
        self.prefix_var = ctk.StringVar(value="")
        ctk.CTkEntry(
            row3, textvariable=self.prefix_var, width=150, height=30,
            fg_color=COLORS["input_bg"], border_color=COLORS["border"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
        ).pack(side="left", padx=(8, 0))

        action_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        action_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkButton(
            action_frame, text="Generate", height=44,
            corner_radius=10,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dim"],
            command=self._generate,
        ).pack(side="left", padx=(0, 8), expand=True, fill="x")

        ctk.CTkButton(
            action_frame, text="Save to File", height=44,
            corner_radius=10,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            fg_color=COLORS["success"],
            hover_color="#00b368",
            text_color="#000000",
            command=self._save_to_file,
        ).pack(side="left", expand=True, fill="x")

        result_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        result_card.pack(fill="both", expand=True)

        ctk.CTkLabel(
            result_card, text="Generated Usernames",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w", padx=16, pady=(10, 4))

        self.result_textbox = ctk.CTkTextbox(
            result_card,
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(family=FONT_FAMILY_MONO, size=11),
            corner_radius=6,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.result_textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._generated = []

    def _get_params(self):
        charset = self.charset_var.get()
        if charset == "letters":
            pool = string.ascii_lowercase
        elif charset == "numbers":
            pool = string.digits
        else:
            pool = string.ascii_lowercase + string.digits

        try:
            min_len = max(1, int(self._min_len_var.get()))
        except ValueError:
            min_len = 4
        try:
            max_len = max(min_len, int(self._max_len_var.get()))
        except ValueError:
            max_len = 6
        try:
            count = max(1, int(self._count_var.get()))
        except ValueError:
            count = 1000
        prefix = self.prefix_var.get()

        return pool, min_len, max_len, count, prefix

    def _generate(self):
        pool, min_len, max_len, count, prefix = self._get_params()
        self._generated = []
        for _ in range(count):
            length = random.randint(min_len, max_len)
            u = prefix + "".join(random.choices(pool, k=length))
            self._generated.append(u)

        self.result_textbox.delete("1.0", "end")
        display = self._generated[:200]
        self.result_textbox.insert("1.0", "\n".join(display))
        if count > 200:
            self.result_textbox.insert("end", f"\n\n... and {count - 200} more")
        self.app.log(f"Generated {count} usernames")

    def _save_to_file(self):
        if not self._generated:
            self._generate()
        path = filedialog.asksaveasfilename(
            initialdir=os.path.join(SCRIPT_DIR, "data"),
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile="usernames.txt",
        )
        if path:
            try:
                with open(path, "w") as f:
                    for u in self._generated:
                        f.write(u + "\n")
                self.app.log(f"Saved {len(self._generated)} usernames to {path}")
                messagebox.showinfo("Saved", f"Saved {len(self._generated)} usernames to:\n{path}")
            except Exception as e:
                self.app.log(f"Save error: {e}")
                messagebox.showerror("Error", str(e))
