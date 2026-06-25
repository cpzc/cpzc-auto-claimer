"""Auto scan & claim page — scan controls, progress, thread config."""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from src.config import SCRIPT_DIR, FONT_FAMILY
from src.themes import COLORS


class AutoScanPage(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self.scanning = False
        self.scan_thread = None
        self._stop_event = threading.Event()

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            scroll, text="Auto Scan & Claim",
            font=ctk.CTkFont(family=FONT_FAMILY, size=28, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(0, 20))

        config_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        config_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            config_card, text="Scan Configuration",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w", padx=16, pady=(12, 8))

        cfg_row = ctk.CTkFrame(config_card, fg_color="transparent")
        cfg_row.pack(fill="x", padx=16, pady=(0, 4))

        ctk.CTkLabel(cfg_row, text="Worker Threads:", font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                      text_color=COLORS["text"]).pack(side="left")
        self.threads_var = ctk.StringVar(value="5")
        ctk.CTkEntry(
            cfg_row, textvariable=self.threads_var, width=60, height=30,
            fg_color=COLORS["input_bg"], border_color=COLORS["border"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
        ).pack(side="left", padx=(8, 0))

        usernames_file = os.path.join(SCRIPT_DIR, "data", "usernames.txt")
        file_frame = ctk.CTkFrame(config_card, fg_color="transparent")
        file_frame.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(file_frame, text="Usernames File:", font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                      text_color=COLORS["text"]).pack(side="left")
        self.file_var = ctk.StringVar(value=usernames_file)
        ctk.CTkEntry(
            file_frame, textvariable=self.file_var, height=30,
            fg_color=COLORS["input_bg"], border_color=COLORS["border"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
        ).pack(side="left", padx=(8, 4), fill="x", expand=True)
        ctk.CTkButton(
            file_frame, text="Browse", width=80, height=30,
            corner_radius=6, font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color=COLORS["border"], hover_color=COLORS["accent_dim"],
            command=self._browse_file,
        ).pack(side="left")

        self._count_username_file()

        action_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        action_frame.pack(fill="x", pady=(0, 12))

        self.scan_btn = ctk.CTkButton(
            action_frame, text="Start Scan", height=44,
            corner_radius=10,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            fg_color=COLORS["success"],
            hover_color="#00b368",
            text_color="#000000",
            command=self._toggle_scan,
        )
        self.scan_btn.pack(side="left", padx=(0, 8), expand=True, fill="x")

        self.pause_btn = ctk.CTkButton(
            action_frame, text="Pause", height=44,
            corner_radius=10,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            fg_color=COLORS["warning"],
            hover_color="#cc8800",
            text_color="#000000",
            command=self._toggle_pause,
            state="disabled",
        )
        self.pause_btn.pack(side="left", expand=True, fill="x")

        progress_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        progress_card.pack(fill="x", pady=(0, 12))

        self.progress_label = ctk.CTkLabel(
            progress_card, text="Ready",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=COLORS["text_dim"],
        )
        self.progress_label.pack(anchor="w", padx=16, pady=(10, 4))

        self.progress_bar = ctk.CTkProgressBar(
            progress_card, height=8,
            fg_color=COLORS["input_bg"],
            progress_color=COLORS["accent"],
            corner_radius=4,
        )
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 10))
        self.progress_bar.set(0)

    def _count_username_file(self):
        path = self.file_var.get()
        if not os.path.exists(path):
            return

        def count():
            try:
                with open(path, "r") as f:
                    c = sum(1 for line in f if line.strip())
                self.app.after(0, lambda c=c: self.progress_label.configure(text=f"Ready \u2014 {c} usernames loaded"))
            except Exception:
                pass

        threading.Thread(target=count, daemon=True).start()

    def _browse_file(self):
        path = filedialog.askopenfilename(
            initialdir=os.path.join(SCRIPT_DIR, "data"),
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self.file_var.set(path)
            self._count_username_file()

    def _toggle_scan(self):
        if self.scanning:
            self._stop_scan()
        else:
            self._start_scan()

    def _start_scan(self):
        if self.scanning:
            return
        if not self.app.claimer or not self.app.claimer.driver:
            messagebox.showwarning("Warning", "Please log in first")
            return
        if not self.app.claimer.current_username:
            messagebox.showwarning("Warning", "Edit profile setup required \u2014 please re-login")
            return

        usernames_file = self.file_var.get()
        if not os.path.exists(usernames_file):
            messagebox.showwarning("Warning", f"File not found:\n{usernames_file}")
            return

        try:
            threads = int(self.threads_var.get())
            threads = max(1, min(20, threads))
        except ValueError:
            threads = 5

        self.scanning = True
        self._stop_event.clear()
        self.scan_btn.configure(text="Stop Scan", fg_color=COLORS["error"], hover_color="#cc0000")
        self.pause_btn.configure(state="normal")
        self.progress_label.configure(text="Scanning...", text_color=COLORS["accent"])

        def run():
            self.app.log(f"Starting scan with {threads} workers")
            self.app.claimer.claimed = False
            self.app.claimer.auto_scan_and_claim_mode(usernames_file, self.app.config, threads=threads)
            self.app.after(0, self._scan_finished)

        self.scan_thread = threading.Thread(target=run, daemon=True)
        self.scan_thread.start()

    def _scan_finished(self):
        self.scanning = False
        self.scan_btn.configure(text="Start Scan", fg_color=COLORS["success"], hover_color="#00b368", state="normal")
        self.pause_btn.configure(text="Pause", state="disabled")
        if self.app.claimer and self.app.claimer.claimed:
            self.progress_label.configure(text="Username claimed!", text_color=COLORS["success"])
            self.app.log("Username claimed successfully!")
        elif self.app.claimer and self.app.claimer.stop_scan.is_set():
            self.progress_label.configure(text="Scan stopped", text_color=COLORS["warning"])
            self.app.log("Scan stopped by user")
        else:
            self.progress_label.configure(text="Scan finished", text_color=COLORS["text_dim"])
            self.app.log("Scan finished")

    def _stop_scan(self):
        if self.app.claimer:
            self.app.claimer.stop_scan.set()
            self.app.claimer.pause_scan.clear()
            self.app.log("Stopping scan...")

    def _toggle_pause(self):
        if not self.app.claimer:
            return
        if self.app.claimer.pause_scan.is_set():
            self.app.claimer.pause_scan.clear()
            self.pause_btn.configure(text="Pause", fg_color=COLORS["warning"])
            self.progress_label.configure(text="Scanning...", text_color=COLORS["accent"])
            self.app.log("Scan resumed")
        else:
            self.app.claimer.pause_scan.set()
            self.pause_btn.configure(text="Resume", fg_color=COLORS["accent"])
            self.progress_label.configure(text="Paused", text_color=COLORS["warning"])
            self.app.log("Scan paused")
