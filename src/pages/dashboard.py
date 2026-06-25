"""Dashboard page — stats overview and quick actions."""

import customtkinter as ctk

from src.config import FONT_FAMILY
from src.themes import COLORS


class DashboardPage(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            scroll, text="Dashboard",
            font=ctk.CTkFont(family=FONT_FAMILY, size=28, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(0, 5))

        ctk.CTkLabel(
            scroll, text="CPZC Auto Claimer - TikTok Username Scanner & Claimer",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w", pady=(0, 20))

        stats_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        stats_frame.pack(fill="x", pady=(0, 20))
        stats_frame.columnconfigure((0, 1, 2), weight=1)

        self.scanned_label = self._stat_card(stats_frame, "Scanned", "0", 0)
        self.claimed_label = self._stat_card(stats_frame, "Claimed", "0", 1)
        self.errors_label = self._stat_card(stats_frame, "Errors", "0", 2)

        self._poll_stats()

        ctk.CTkLabel(
            scroll, text="Quick Actions",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(10, 10))

        actions = ctk.CTkFrame(scroll, fg_color="transparent")
        actions.pack(fill="x")
        actions.columnconfigure((0, 1), weight=1)

        self._action_button(actions, "Start Auto Scan", "scan", 0, 0)
        self._action_button(actions, "Generate Usernames", "generate", 0, 1)

        ctk.CTkLabel(
            scroll, text="How to use",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(20, 10))

        steps = [
            "1.  Place your usernames in  data/usernames.txt  (one per line)",
            "2.  Go to  Auto Scan  and log in to TikTok (manual QR, cookies, or create account)",
            "3.  Configure worker threads and click  Start Scan",
            "4.  The app scans via HTTP and auto-claims available names via the browser",
            "5.  Check  output/claimed.txt  for claimed usernames",
        ]
        for step in steps:
            ctk.CTkLabel(
                scroll, text=step,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=COLORS["text_dim"],
                anchor="w",
            ).pack(anchor="w", pady=2)

    def _stat_card(self, parent, label, value, col):
        card = ctk.CTkFrame(parent, fg_color=COLORS["card"], corner_radius=10)
        card.grid(row=0, column=col, padx=6, pady=4, sticky="nsew")

        ctk.CTkLabel(
            card, text=label,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=COLORS["text_dim"],
        ).pack(pady=(14, 0))

        val_label = ctk.CTkLabel(
            card, text=value,
            font=ctk.CTkFont(family=FONT_FAMILY, size=26, weight="bold"),
            text_color=COLORS["accent"],
        )
        val_label.pack(pady=(2, 12))
        return val_label

    def _action_button(self, parent, text, page, row, col):
        btn = ctk.CTkButton(
            parent,
            text=text,
            height=50,
            corner_radius=10,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dim"],
            text_color="#ffffff",
            command=lambda: self.app.navigate_to(page),
        )
        btn.grid(row=row, column=col, padx=6, pady=4, sticky="nsew")

    def _poll_stats(self):
        if self.app.claimer:
            self.scanned_label.configure(text=str(self.app.claimer.scan_scanned))
            self.claimed_label.configure(text=str(self.app.claimer.scan_claimed))
            self.errors_label.configure(text=str(self.app.claimer.scan_errors))
        self.after(500, self._poll_stats)
