"""Settings page — theme picker, headless toggle, notification config."""

import json
import os
import tkinter as tk
from tkinter import colorchooser, messagebox

import customtkinter as ctk

from src.config import SCRIPT_DIR, FONT_FAMILY
from src.themes import COLORS, THEME_PRESETS, COLOR_LABELS, load_theme


class SettingsPage(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            scroll, text="Settings",
            font=ctk.CTkFont(family=FONT_FAMILY, size=28, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(0, 20))

        theme_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        theme_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            theme_card, text="Theme",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w", padx=16, pady=(12, 8))

        theme_row = ctk.CTkFrame(theme_card, fg_color="transparent")
        theme_row.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(theme_row, text="Preset:", font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                      text_color=COLORS["text"]).pack(side="left")
        self.theme_var = ctk.StringVar(value=self.app.config.get("theme", "Midnight"))
        self.theme_menu = ctk.CTkOptionMenu(
            theme_row, variable=self.theme_var,
            values=list(THEME_PRESETS.keys()),
            width=160, height=30, corner_radius=6,
            fg_color=COLORS["input_bg"],
            button_color=COLORS["border"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=self._on_theme_change,
        )
        self.theme_menu.pack(side="left", padx=(8, 0))

        self.preview_frame = ctk.CTkFrame(theme_card, fg_color="transparent")
        self.preview_frame.pack(fill="x", padx=16, pady=(8, 4))

        self.custom_frame = ctk.CTkFrame(theme_card, fg_color="transparent")
        self.custom_frame.pack(fill="x", padx=16, pady=(0, 4))

        self._color_buttons = {}
        self._custom_colors = {}
        self._build_preview()
        self._build_custom_pickers()
        self._on_theme_change(self.theme_var.get())

        ctk.CTkButton(
            theme_card, text="Apply Theme", height=36,
            corner_radius=8,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dim"],
            command=self._apply_theme,
        ).pack(anchor="w", padx=16, pady=(4, 12))

        general_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        general_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            general_card, text="General",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w", padx=16, pady=(12, 8))

        row = ctk.CTkFrame(general_card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(row, text="Headless Mode:", font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                      text_color=COLORS["text"]).pack(side="left")
        self.headless_var = ctk.BooleanVar(value=self.app.config.get("headless", False))
        ctk.CTkSwitch(
            row, text="", variable=self.headless_var,
            onvalue=True, offvalue=False,
            button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_dim"],
            fg_color=COLORS["border"],
        ).pack(side="left", padx=(8, 0))

        row2 = ctk.CTkFrame(general_card, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=(4, 12))

        ctk.CTkLabel(row2, text="Username Input Delay (s):", font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                      text_color=COLORS["text"]).pack(side="left")
        self.delay_var = ctk.StringVar(value=str(self.app.config.get("username_input_delay", 2)))
        ctk.CTkEntry(
            row2, textvariable=self.delay_var, width=60, height=30,
            fg_color=COLORS["input_bg"], border_color=COLORS["border"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
        ).pack(side="left", padx=(8, 0))

        notif_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        notif_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            notif_card, text="Notifications",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w", padx=16, pady=(12, 8))

        fields = [
            ("Discord Webhook URL:", "discord_webhook_url"),
            ("Telegram Bot Token:", "telegram_bot_token"),
            ("Telegram Chat ID:", "telegram_chat_id"),
        ]
        self._entries = {}
        for label, key in fields:
            f = ctk.CTkFrame(notif_card, fg_color="transparent")
            f.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(f, text=label, font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                          text_color=COLORS["text"], width=180, anchor="w").pack(side="left")
            var = ctk.StringVar(value=self.app.config.get(key, ""))
            self._entries[key] = var
            ctk.CTkEntry(
                f, textvariable=var, height=30,
                fg_color=COLORS["input_bg"], border_color=COLORS["border"],
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                show="*" if "token" in key.lower() else "",
            ).pack(side="left", padx=(8, 0), fill="x", expand=True)

        ctk.CTkButton(
            notif_card, text="Save Settings", height=40,
            corner_radius=10,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dim"],
            command=self._save,
        ).pack(anchor="w", padx=16, pady=(8, 12))

    def _build_preview(self):
        for w in self.preview_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self.preview_frame, text="Preview",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w", pady=(0, 4))

        row = ctk.CTkFrame(self.preview_frame, fg_color="transparent")
        row.pack(fill="x")
        for i, (key, label) in enumerate(COLOR_LABELS.items()):
            color = COLORS.get(key, "#888888")
            swatch = ctk.CTkFrame(row, fg_color=color, width=32, height=32, corner_radius=6,
                                   border_width=1, border_color=COLORS["border"])
            swatch.pack(side="left", padx=(0, 2))
            swatch.pack_propagate(False)
        hint = ctk.CTkLabel(
            self.preview_frame, text="Current active colors",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=COLORS["text_dim"],
        )
        hint.pack(anchor="w", pady=(4, 0))

    def _build_custom_pickers(self):
        for w in self.custom_frame.winfo_children():
            w.destroy()
        grid = ctk.CTkFrame(self.custom_frame, fg_color="transparent")
        grid.pack(fill="x")
        cols = 4
        for i, (key, label) in enumerate(COLOR_LABELS.items()):
            r, c = divmod(i, cols)
            cell = ctk.CTkFrame(grid, fg_color="transparent")
            cell.grid(row=r, column=c, padx=4, pady=3, sticky="w")

            color = self.app.config.get("theme_custom", {}).get(key, COLORS.get(key, "#888888"))
            preview = ctk.CTkFrame(cell, fg_color=color, width=20, height=20, corner_radius=4,
                                    border_width=1, border_color=COLORS["border"])
            preview.pack(side="left", padx=(0, 4))
            preview.pack_propagate(False)

            btn = ctk.CTkButton(
                cell, text=label, width=90, height=24,
                corner_radius=4,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                fg_color=COLORS["input_bg"],
                hover_color=COLORS["card_hover"],
                command=lambda k=key, p=preview: self._pick_color(k, p),
            )
            btn.pack(side="left")

    def _pick_color(self, key, preview_widget):
        current = self._custom_colors.get(key, COLORS.get(key, "#888888"))
        result = colorchooser.askcolor(initialcolor=current, title=f"Choose {COLOR_LABELS.get(key, key)}")
        if result and result[1]:
            hex_color = result[1]
            preview_widget.configure(fg_color=hex_color)
            self._custom_colors[key] = hex_color
            self.app.config.setdefault("theme_custom", {})[key] = hex_color

    def _on_theme_change(self, name):
        if name == "Custom":
            self.custom_frame.pack(fill="x", padx=16, pady=(0, 4))
        else:
            self.custom_frame.pack_forget()

    def _apply_theme(self):
        self._save_config()
        self.app.apply_theme()
        self.app.log("Theme applied")

    def _save(self):
        self._save_config()
        self.app.log("Settings saved")
        messagebox.showinfo("Saved", "Settings saved to config.json")

    def _save_config(self):
        self.app.config["headless"] = self.headless_var.get()
        self.app.config["theme"] = self.theme_var.get()
        try:
            self.app.config["username_input_delay"] = float(self.delay_var.get())
        except ValueError:
            pass
        for key, var in self._entries.items():
            self.app.config[key] = var.get()
        if self._custom_colors:
            self.app.config.setdefault("theme_custom", {}).update(self._custom_colors)

        config_path = os.path.join(SCRIPT_DIR, "config.json")
        try:
            with open(config_path, "r") as f:
                cfg = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            cfg = {}
        cfg.update(self.app.config)
        with open(config_path, "w") as f:
            json.dump(cfg, f, indent=4)
