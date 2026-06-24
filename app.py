"""
CPZC Auto Claimer - Modern GUI Application

A professional Tkinter GUI for the TikTok Username Auto-Claimer.
All logic is preserved from the original auto_claimer.py.

Requirements:
    pip install customtkinter selenium requests colorama
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, colorchooser
from colorama import Fore
import threading
import json
import os
import sys
import time
import re
import random
import string
import requests
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, SCRIPT_DIR)
import auto_claimer

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

THEME_PRESETS = {
    "Midnight": {
        "bg": "#0f0f0f", "card": "#1a1a2e", "card_hover": "#1f1f3a",
        "accent": "#00d4ff", "accent_dim": "#0099cc",
        "success": "#00e676", "error": "#ff5252", "warning": "#ffab40",
        "text": "#e0e0e0", "text_dim": "#808080",
        "sidebar": "#0d1117", "sidebar_active": "#161b22",
        "border": "#30363d", "input_bg": "#161b22",
    },
    "Ocean": {
        "bg": "#0a1628", "card": "#0f2240", "card_hover": "#142d52",
        "accent": "#00b4d8", "accent_dim": "#0096b7",
        "success": "#48cae4", "error": "#e63946", "warning": "#f4a261",
        "text": "#caf0f8", "text_dim": "#5e8aae",
        "sidebar": "#061020", "sidebar_active": "#0c1a30",
        "border": "#1b3a5c", "input_bg": "#0c1a30",
    },
    "Forest": {
        "bg": "#0d1a0d", "card": "#1a2e1a", "card_hover": "#1f3a1f",
        "accent": "#4caf50", "accent_dim": "#388e3c",
        "success": "#81c784", "error": "#e57373", "warning": "#ffb74d",
        "text": "#c8e6c9", "text_dim": "#6d8b6d",
        "sidebar": "#0a140a", "sidebar_active": "#142814",
        "border": "#2e5a2e", "input_bg": "#142814",
    },
    "Sunset": {
        "bg": "#1a0f0f", "card": "#2e1a1a", "card_hover": "#3a1f1f",
        "accent": "#ff6b6b", "accent_dim": "#e05555",
        "success": "#51cf66", "error": "#ff4757", "warning": "#ffa502",
        "text": "#f5e6cc", "text_dim": "#a08060",
        "sidebar": "#140a0a", "sidebar_active": "#221414",
        "border": "#5a2e2e", "input_bg": "#221414",
    },
    "Purple Haze": {
        "bg": "#12081e", "card": "#1e1030", "card_hover": "#281840",
        "accent": "#bb86fc", "accent_dim": "#9a60d6",
        "success": "#03dac6", "error": "#cf6679", "warning": "#ffab40",
        "text": "#e8dff5", "text_dim": "#7a6a9a",
        "sidebar": "#0a0414", "sidebar_active": "#160c24",
        "border": "#3a2060", "input_bg": "#160c24",
    },
    "Custom": {},
}

COLOR_LABELS = {
    "bg": "Background", "card": "Card", "card_hover": "Card Hover",
    "accent": "Accent", "accent_dim": "Accent Dim",
    "success": "Success", "error": "Error", "warning": "Warning",
    "text": "Text", "text_dim": "Text Dim",
    "sidebar": "Sidebar", "sidebar_active": "Sidebar Active",
    "border": "Border", "input_bg": "Input Background",
}


def load_theme(config):
    name = config.get("theme", "Midnight")
    if name == "Custom":
        custom = config.get("theme_custom", {})
        colors = dict(THEME_PRESETS["Midnight"])
        colors.update(custom)
        return colors
    return dict(THEME_PRESETS.get(name, THEME_PRESETS["Midnight"]))


COLORS = load_theme({})


class SidebarButton(ctk.CTkButton):
    def __init__(self, master, text="", command=None, icon="", **kwargs):
        super().__init__(
            master,
            text=f"  {icon}  {text}" if icon else text,
            command=command,
            fg_color="transparent",
            text_color=COLORS["text_dim"],
            hover_color=COLORS["sidebar_active"],
            anchor="w",
            height=44,
            corner_radius=8,
            font=ctk.CTkFont(size=13),
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
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=COLORS["card"], corner_radius=10, **kwargs)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 0))

        ctk.CTkLabel(
            header, text="Output Log",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(side="left")

        ctk.CTkButton(
            header, text="Clear", width=60, height=26,
            fg_color=COLORS["border"], hover_color=COLORS["error"],
            font=ctk.CTkFont(size=11),
            command=self.clear,
        ).pack(side="right")

        self.textbox = ctk.CTkTextbox(
            self,
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=6,
            border_width=1,
            border_color=COLORS["border"],
            state="disabled",
        )
        self.textbox.pack(fill="both", expand=True, padx=10, pady=(6, 10))

    def log(self, message):
        self.textbox.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.textbox.insert("end", f"[{timestamp}] {message}\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def clear(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")


class DashboardPage(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            scroll, text="Dashboard",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(0, 5))

        ctk.CTkLabel(
            scroll, text="CPZC Auto Claimer - TikTok Username Scanner & Claimer",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w", pady=(0, 20))

        stats_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        stats_frame.pack(fill="x", pady=(0, 20))
        stats_frame.columnconfigure((0, 1, 2), weight=1)

        self.scanned_label = self._stat_card(stats_frame, "Scanned", "0", 0)
        self.claimed_label = self._stat_card(stats_frame, "Claimed", "0", 1)
        self.errors_label = self._stat_card(stats_frame, "Errors", "0", 2)

        ctk.CTkLabel(
            scroll, text="Quick Actions",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(10, 10))

        actions = ctk.CTkFrame(scroll, fg_color="transparent")
        actions.pack(fill="x")
        actions.columnconfigure((0, 1), weight=1)

        self._action_button(actions, "Start Auto Scan", "scan", 0, 0)
        self._action_button(actions, "Generate Usernames", "generate", 0, 1)

        ctk.CTkLabel(
            scroll, text="How to use",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(20, 10))

        steps = [
            "1.  Place your usernames in  data/usernames.txt  (one per line)",
            "2.  Go to  Auto Scan  and log in to TikTok (manual QR, cookies, or credentials)",
            "3.  Configure worker threads and click  Start Scan",
            "4.  The app scans via HTTP and auto-claims available names via the browser",
            "5.  Check  output/claimed.txt  for claimed usernames",
        ]
        for step in steps:
            ctk.CTkLabel(
                scroll, text=step,
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_dim"],
                anchor="w",
            ).pack(anchor="w", pady=2)

    def _stat_card(self, parent, label, value, col):
        card = ctk.CTkFrame(parent, fg_color=COLORS["card"], corner_radius=10)
        card.grid(row=0, column=col, padx=6, pady=4, sticky="nsew")

        ctk.CTkLabel(
            card, text=label,
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_dim"],
        ).pack(pady=(14, 0))

        val_label = ctk.CTkLabel(
            card, text=value,
            font=ctk.CTkFont(size=26, weight="bold"),
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
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dim"],
            text_color="#ffffff",
            command=lambda: self.app.navigate_to(page),
        )
        btn.grid(row=row, column=col, padx=6, pady=4, sticky="nsew")

    def update_stats(self, scanned, claimed, errors):
        self.scanned_label.configure(text=str(scanned))
        self.claimed_label.configure(text=str(claimed))
        self.errors_label.configure(text=str(errors))


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
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(0, 20))

        login_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        login_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            login_card, text="Login to TikTok",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w", padx=16, pady=(12, 8))

        self.login_status = ctk.CTkLabel(
            login_card, text="Not logged in",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["error"],
        )
        self.login_status.pack(anchor="w", padx=16, pady=(0, 8))

        btn_frame = ctk.CTkFrame(login_card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(0, 12))
        for i in range(5):
            btn_frame.columnconfigure(i, weight=1)

        login_methods = [
            ("Manual (QR)", "manual"),
            ("Cookies (JSON)", "cookies_json"),
            ("Cookies (sessions)", "cookies_session"),
            ("Create Account", "create"),
            ("Email:Pass File", "credentials"),
        ]
        for i, (text, method) in enumerate(login_methods):
            ctk.CTkButton(
                btn_frame, text=text, height=32,
                corner_radius=6,
                font=ctk.CTkFont(size=11),
                fg_color=COLORS["border"],
                hover_color=COLORS["accent_dim"],
                command=lambda m=method: self._login(m),
            ).grid(row=0, column=i, padx=3, sticky="nsew")

        ctk.CTkButton(
            login_card, text="Save Cookies", height=28, width=100,
            corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color=COLORS["success"],
            hover_color="#00b368",
            text_color="#000000",
            command=self._save_cookies,
        ).pack(anchor="w", padx=16, pady=(0, 12))

        config_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        config_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            config_card, text="Scan Configuration",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w", padx=16, pady=(12, 8))

        cfg_row = ctk.CTkFrame(config_card, fg_color="transparent")
        cfg_row.pack(fill="x", padx=16, pady=(0, 4))

        ctk.CTkLabel(cfg_row, text="Worker Threads:", font=ctk.CTkFont(size=12),
                      text_color=COLORS["text"]).pack(side="left")
        self.threads_var = ctk.StringVar(value="5")
        ctk.CTkEntry(
            cfg_row, textvariable=self.threads_var, width=60, height=30,
            fg_color=COLORS["input_bg"], border_color=COLORS["border"],
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(8, 0))

        usernames_file = os.path.join(SCRIPT_DIR, "data", "usernames.txt")
        file_frame = ctk.CTkFrame(config_card, fg_color="transparent")
        file_frame.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(file_frame, text="Usernames File:", font=ctk.CTkFont(size=12),
                      text_color=COLORS["text"]).pack(side="left")
        self.file_var = ctk.StringVar(value=usernames_file)
        ctk.CTkEntry(
            file_frame, textvariable=self.file_var, height=30,
            fg_color=COLORS["input_bg"], border_color=COLORS["border"],
            font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=(8, 4), fill="x", expand=True)
        ctk.CTkButton(
            file_frame, text="Browse", width=80, height=30,
            corner_radius=6, font=ctk.CTkFont(size=11),
            fg_color=COLORS["border"], hover_color=COLORS["accent_dim"],
            command=self._browse_file,
        ).pack(side="left")

        self._count_username_file()

        action_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        action_frame.pack(fill="x", pady=(0, 12))

        self.start_btn = ctk.CTkButton(
            action_frame, text="Start Scan", height=44,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["success"],
            hover_color="#00b368",
            text_color="#000000",
            command=self._start_scan,
        )
        self.start_btn.pack(side="left", padx=(0, 8), expand=True, fill="x")

        self.stop_btn = ctk.CTkButton(
            action_frame, text="Stop", height=44,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["error"],
            hover_color="#cc0000",
            command=self._stop_scan,
            state="disabled",
        )
        self.stop_btn.pack(side="left", expand=True, fill="x")

        progress_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        progress_card.pack(fill="x", pady=(0, 12))

        self.progress_label = ctk.CTkLabel(
            progress_card, text="Ready",
            font=ctk.CTkFont(size=13),
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
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    count = sum(1 for line in f if line.strip())
                self.progress_label.configure(text=f"Ready — {count} usernames loaded")
            except Exception:
                pass

    def _browse_file(self):
        path = filedialog.askopenfilename(
            initialdir=os.path.join(SCRIPT_DIR, "data"),
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self.file_var.set(path)
            self._count_username_file()

    def _login(self, method):
        if self.app.claimer and self.app.claimer.driver:
            self.app.claimer.cleanup()
        self.app.claimer = auto_claimer.TikTokSeleniumClaimer(
            headless=self.app.config.get("headless", False),
            username_input_delay=self.app.config.get("username_input_delay", 2),
        )
        self.app.log("Setting up browser...")
        if not self.app.claimer.setup_driver():
            self.app.log("Failed to setup browser")
            messagebox.showerror("Error", "Failed to setup browser. Check Chrome/Chromium is installed.")
            return
        self.app.log("Browser ready")

        def do_login():
            script_dir = SCRIPT_DIR
            logged_in = False
            try:
                if method == "manual":
                    self.app.log("Opening TikTok login page — log in manually in the browser window")
                    self.app.claimer.driver.get("https://www.tiktok.com/login")
                    done = [False]
                    event = threading.Event()
                    def show_manual():
                        messagebox.showinfo(
                            "Manual Login",
                            "Log in to TikTok in the browser window.\nClick OK after you have logged in."
                        )
                        done[0] = True
                        event.set()
                    self.app.after(0, show_manual)
                    event.wait(timeout=300)
                    logged_in = self.app.claimer.verify_logged_in()

                elif method == "cookies_json":
                    path = os.path.join(script_dir, "data", "cookies.json")
                    if not os.path.exists(path):
                        self.app.log(f"File not found: {path}")
                        self.app.after(0, lambda: messagebox.showerror("Error", f"File not found:\n{path}"))
                        return
                    logged_in = self.app.claimer.login_with_cookies(path)

                elif method == "cookies_session":
                    path = os.path.join(script_dir, "data", "sessions.txt")
                    if not os.path.exists(path):
                        self.app.log(f"File not found: {path}")
                        self.app.after(0, lambda: messagebox.showerror("Error", f"File not found:\n{path}"))
                        return
                    logged_in = self.app.claimer.login_with_cookies(path)

                elif method == "create":
                    def gui_input(prompt):
                        result = [None]
                        event = threading.Event()
                        def ask():
                            result[0] = simpledialog.askstring("Input Required", prompt)
                            event.set()
                        self.app.after(0, ask)
                        event.wait(timeout=120)
                        return result[0] or ""
                    def gui_pause(prompt):
                        clean = prompt.replace(Fore.YELLOW, "").replace(Fore.WHITE, "")
                        done = [False]
                        event = threading.Event()
                        def show():
                            messagebox.showinfo("Info", clean)
                            done[0] = True
                            event.set()
                        self.app.after(0, show)
                        event.wait(timeout=30)
                    logged_in = auto_claimer.create_account(
                        self.app.claimer.driver, input_fn=gui_input, pause_fn=gui_pause
                    )

                elif method == "credentials":
                    path = os.path.join(script_dir, "data", "accounts.txt")
                    if not os.path.exists(path):
                        self.app.log(f"File not found: {path}")
                        self.app.after(0, lambda: messagebox.showerror("Error", f"File not found:\n{path}"))
                        return
                    logged_in = self.app.claimer.login_with_credentials(path)
            except Exception as e:
                self.app.log(f"Login error: {e}")

            if logged_in:
                self.app.log("Login successful")
                if not self.app.claimer.initialize_edit_profile_setup():
                    self.app.log("Edit profile setup failed")
                    self.app.after(0, lambda: self.login_status.configure(
                        text="Logged in (edit profile failed)", text_color=COLORS["warning"]
                    ))
                else:
                    self.app.after(0, lambda: self.login_status.configure(
                        text=f"Logged in as @{self.app.claimer.current_username}",
                        text_color=COLORS["success"],
                    ))
            else:
                self.app.log("Login failed")
                self.app.after(0, lambda: self.login_status.configure(
                    text="Login failed", text_color=COLORS["error"]
                ))

        threading.Thread(target=do_login, daemon=True).start()

    def _save_cookies(self):
        if not self.app.claimer or not self.app.claimer.driver:
            messagebox.showwarning("Warning", "No browser session to save")
            return
        path = os.path.join(SCRIPT_DIR, "data", "sessions.txt")
        try:
            self.app.claimer.save_cookies(path)
            self.app.log(f"Cookies saved to {path}")
        except Exception as e:
            self.app.log(f"Failed to save cookies: {e}")

    def update_login_status(self, username=None, error=False):
        """Update the login status label from external pages (e.g. Accounts tab)."""
        if error:
            self.app.after(0, lambda: self.login_status.configure(
                text="Login failed", text_color=COLORS["error"]
            ))
        elif username:
            self.app.after(0, lambda: self.login_status.configure(
                text=f"Logged in as @{username}",
                text_color=COLORS["success"],
            ))
        else:
            self.app.after(0, lambda: self.login_status.configure(
                text="Not logged in", text_color=COLORS["text_dim"]
            ))

    def _start_scan(self):
        if self.scanning:
            return
        if not self.app.claimer or not self.app.claimer.driver:
            messagebox.showwarning("Warning", "Please log in first")
            return
        if not self.app.claimer.current_username:
            messagebox.showwarning("Warning", "Edit profile setup required — please re-login")
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
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
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
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
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
            self.app.log("Stopping scan...")


class GeneratePage(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            scroll, text="Generate Usernames",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(0, 20))

        card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            card, text="Configuration",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w", padx=16, pady=(12, 8))

        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(row1, text="Character Set:", font=ctk.CTkFont(size=12),
                      text_color=COLORS["text"]).pack(side="left")
        self.charset_var = ctk.StringVar(value="both")
        ctk.CTkOptionMenu(
            row1, variable=self.charset_var,
            values=["letters", "numbers", "both"],
            width=120, height=30, corner_radius=6,
            fg_color=COLORS["input_bg"],
            button_color=COLORS["border"],
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(8, 0))

        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=4)

        for label, default, attr in [("Min Length:", "4", "min_len"), ("Max Length:", "6", "max_len"), ("Count:", "1000", "count")]:
            ctk.CTkLabel(row2, text=label, font=ctk.CTkFont(size=12),
                          text_color=COLORS["text"]).pack(side="left", padx=(0, 4))
            var = ctk.StringVar(value=default)
            setattr(self, f"_{attr}_var", var)
            ctk.CTkEntry(
                row2, textvariable=var, width=70, height=30,
                fg_color=COLORS["input_bg"], border_color=COLORS["border"],
                font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=(0, 12))

        row3 = ctk.CTkFrame(card, fg_color="transparent")
        row3.pack(fill="x", padx=16, pady=(4, 12))

        ctk.CTkLabel(row3, text="Prefix:", font=ctk.CTkFont(size=12),
                      text_color=COLORS["text"]).pack(side="left")
        self.prefix_var = ctk.StringVar(value="")
        ctk.CTkEntry(
            row3, textvariable=self.prefix_var, width=150, height=30,
            fg_color=COLORS["input_bg"], border_color=COLORS["border"],
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(8, 0))

        action_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        action_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkButton(
            action_frame, text="Generate", height=44,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dim"],
            command=self._generate,
        ).pack(side="left", padx=(0, 8), expand=True, fill="x")

        ctk.CTkButton(
            action_frame, text="Save to File", height=44,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["success"],
            hover_color="#00b368",
            text_color="#000000",
            command=self._save_to_file,
        ).pack(side="left", expand=True, fill="x")

        result_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        result_card.pack(fill="both", expand=True)

        ctk.CTkLabel(
            result_card, text="Generated Usernames",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w", padx=16, pady=(10, 4))

        self.result_textbox = ctk.CTkTextbox(
            result_card,
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(family="Consolas", size=11),
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


class AccountsPage(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self.accounts = []
        self.selected_idx = None

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            scroll, text="Accounts",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(0, 20))

        table_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        table_card.pack(fill="both", expand=True, pady=(0, 12))

        header_row = ctk.CTkFrame(table_card, fg_color="transparent")
        header_row.pack(fill="x", padx=16, pady=(12, 4))

        ctk.CTkLabel(header_row, text="Username",
                      font=ctk.CTkFont(size=12, weight="bold"),
                      text_color=COLORS["accent"], width=250, anchor="w").pack(side="left")
        ctk.CTkLabel(header_row, text="Email",
                      font=ctk.CTkFont(size=12, weight="bold"),
                      text_color=COLORS["accent"], anchor="w").pack(side="left", padx=(20, 0))

        ctk.CTkFrame(table_card, fg_color=COLORS["border"], height=1).pack(fill="x", padx=16, pady=(0, 4))

        list_frame = ctk.CTkFrame(table_card, fg_color="transparent")
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self.table_canvas = tk.Canvas(list_frame, bg=COLORS["input_bg"], highlightthickness=0)
        self.table_scrollbar = ctk.CTkScrollbar(list_frame, orientation="vertical", command=self.table_canvas.yview)
        self.table_inner = ctk.CTkFrame(self.table_canvas, fg_color="transparent")

        self.table_inner.bind("<Configure>", lambda e: self.table_canvas.configure(scrollregion=self.table_canvas.bbox("all")))
        self.table_canvas_window = self.table_canvas.create_window((0, 0), window=self.table_inner, anchor="nw")
        self.table_canvas.configure(yscrollcommand=self.table_scrollbar.set)

        self.table_canvas.pack(side="left", fill="both", expand=True)
        self.table_scrollbar.pack(side="right", fill="y")

        self.table_canvas.bind("<Configure>", self._on_canvas_resize)

        self.row_widgets = []
        self.empty_label = ctk.CTkLabel(
            self.table_inner, text="No accounts found in data/accounts.txt",
            font=ctk.CTkFont(size=12), text_color=COLORS["text_dim"],
        )

        self.status_label = ctk.CTkLabel(
            table_card, text="",
            font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"],
        )
        self.status_label.pack(anchor="w", padx=16, pady=(0, 8))

        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(0, 12))
        btn_frame.columnconfigure((0, 1), weight=1)

        self.login_btn = ctk.CTkButton(
            btn_frame, text="Login", height=44,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dim"],
            command=self._login_account,
        )
        self.login_btn.grid(row=0, column=0, padx=(0, 6), sticky="nsew")

        self.inbox_btn = ctk.CTkButton(
            btn_frame, text="Open Inbox", height=44,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["success"],
            hover_color="#00b368",
            text_color="#000000",
            command=self._open_inbox,
        )
        self.inbox_btn.grid(row=0, column=1, padx=(6, 0), sticky="nsew")

        self._load_accounts()

    def _on_canvas_resize(self, event):
        self.table_canvas.itemconfig(self.table_canvas_window, width=event.width)

    def _load_accounts(self):
        self.accounts = []
        path = os.path.join(SCRIPT_DIR, "data", "accounts.txt")
        if not os.path.exists(path):
            self.empty_label.pack(pady=20)
            self.status_label.configure(text="File not found: data/accounts.txt")
            self.inbox_btn.configure(state="disabled")
            return
        try:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if ":" not in line:
                        continue
                    parts = line.split(":", 3)
                    username = parts[0]
                    password = parts[1]
                    email = parts[2] if len(parts) > 2 else ""
                    email_pass = parts[3] if len(parts) > 3 else ""
                    self.accounts.append({
                        "username": username,
                        "password": password,
                        "email": email,
                        "email_pass": email_pass,
                    })
        except Exception as e:
            self.app.log(f"Error loading accounts: {e}")

        if not self.accounts:
            self.empty_label.pack(pady=20)
            self.status_label.configure(text="No valid accounts found")
            self.inbox_btn.configure(state="disabled")
            return

        has_email = any(a["email"] and a["email_pass"] for a in self.accounts)
        if not has_email:
            self.inbox_btn.configure(state="disabled")

        self._build_rows()
        self.status_label.configure(text=f"{len(self.accounts)} accounts loaded")

    def _build_rows(self):
        for w in self.table_inner.winfo_children():
            if w != self.empty_label:
                w.destroy()
        self.row_widgets.clear()
        self.selected_idx = None

        for i, acct in enumerate(self.accounts):
            row_bg = COLORS["input_bg"] if i % 2 == 0 else COLORS["card"]
            row = ctk.CTkFrame(self.table_inner, fg_color=row_bg, corner_radius=0, height=36)
            row.pack(fill="x", pady=0)
            row.pack_propagate(False)

            ctk.CTkLabel(row, text=acct["username"],
                          font=ctk.CTkFont(size=12),
                          text_color=COLORS["text"], width=250, anchor="w").pack(side="left", padx=(10, 0))
            ctk.CTkLabel(row, text=acct["email"] or "—",
                          font=ctk.CTkFont(size=12),
                          text_color=COLORS["text_dim"], anchor="w").pack(side="left", padx=(20, 0))

            row.bind("<Button-1>", lambda e, idx=i: self._select(idx))
            for child in row.winfo_children():
                child.bind("<Button-1>", lambda e, idx=i: self._select(idx))

            self.row_widgets.append(row)

    def _select(self, idx):
        if self.selected_idx is not None and self.selected_idx < len(self.row_widgets):
            prev = self.row_widgets[self.selected_idx]
            prev.configure(fg_color=COLORS["input_bg"] if self.selected_idx % 2 == 0 else COLORS["card"])
        self.selected_idx = idx
        self.row_widgets[idx].configure(fg_color=COLORS["accent_dim"])

    def _ensure_driver(self):
        if self.app.claimer and self.app.claimer.driver:
            return True
        self.app.claimer = auto_claimer.TikTokSeleniumClaimer(
            headless=self.app.config.get("headless", False),
            username_input_delay=self.app.config.get("username_input_delay", 2),
        )
        self.app.log("Setting up browser...")
        if not self.app.claimer.setup_driver():
            self.app.log("Failed to setup browser")
            return False
        self.app.log("Browser ready")
        return True

    def _login_account(self):
        if self.selected_idx is None:
            messagebox.showwarning("No Selection", "Select an account from the table first")
            return
        acct = self.accounts[self.selected_idx]
        if not self._ensure_driver():
            return

        def do_login():
            def gui_pause(prompt):
                clean = prompt.replace(Fore.YELLOW, "").replace(Fore.WHITE, "")
                event = threading.Event()
                def show():
                    messagebox.showinfo("Action Required", clean)
                    event.set()
                self.app.after(0, show)
                event.wait(timeout=300)
            self.app.log(f"Logging in as {acct['username']}...")
            success = self.app.claimer.login_with_single_account(
                acct["username"], acct["password"],
                email=acct.get("email") or None,
                email_password=acct.get("email_pass") or None,
                pause_fn=gui_pause,
                config=self.app.config,
            )
            if success:
                if self.app.claimer.initialize_edit_profile_setup():
                    self.app.after(0, lambda: messagebox.showinfo(
                        "Login Success",
                        f"Logged in as @{self.app.claimer.current_username}"
                    ))
                    self.app.log(f"Logged in as @{self.app.claimer.current_username}")
                    self.app.pages["scan"].update_login_status(self.app.claimer.current_username)
                else:
                    self.app.log("Login succeeded but edit profile setup failed")
                    self.app.pages["scan"].update_login_status(error=True)
            else:
                self.app.log(f"Login failed for {acct['username']}")
                self.app.pages["scan"].update_login_status(error=True)
                self.app.after(0, lambda: messagebox.showerror("Login Failed", f"Could not login as {acct['username']}"))

        threading.Thread(target=do_login, daemon=True).start()

    def _open_inbox(self):
        if self.selected_idx is None:
            messagebox.showwarning("No Selection", "Select an account from the table first")
            return
        acct = self.accounts[self.selected_idx]
        if not acct["email"] or not acct["email_pass"]:
            messagebox.showwarning("No Email", "This account has no email credentials")
            return
        if not self._ensure_driver():
            return

        def do_inbox():
            def gui_pause(prompt):
                clean = prompt.replace(Fore.YELLOW, "").replace(Fore.WHITE, "")
                done = [False]
                event = threading.Event()
                def show():
                    messagebox.showinfo("Action Required", clean)
                    done[0] = True
                    event.set()
                self.app.after(0, show)
                event.wait(timeout=300)
            self.app.log(f"Opening inbox for {acct['email']}...")
            self.app.claimer.open_inbox(acct["email"], acct["email_pass"], pause_fn=gui_pause)
            self.app.log("Inbox opened")

        threading.Thread(target=do_inbox, daemon=True).start()


class SettingsPage(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            scroll, text="Settings",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(0, 20))

        theme_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        theme_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            theme_card, text="Theme",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w", padx=16, pady=(12, 8))

        theme_row = ctk.CTkFrame(theme_card, fg_color="transparent")
        theme_row.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(theme_row, text="Preset:", font=ctk.CTkFont(size=12),
                      text_color=COLORS["text"]).pack(side="left")
        self.theme_var = ctk.StringVar(value=self.app.config.get("theme", "Midnight"))
        self.theme_menu = ctk.CTkOptionMenu(
            theme_row, variable=self.theme_var,
            values=list(THEME_PRESETS.keys()),
            width=160, height=30, corner_radius=6,
            fg_color=COLORS["input_bg"],
            button_color=COLORS["border"],
            font=ctk.CTkFont(size=12),
            command=self._on_theme_change,
        )
        self.theme_menu.pack(side="left", padx=(8, 0))

        self.preview_frame = ctk.CTkFrame(theme_card, fg_color="transparent")
        self.preview_frame.pack(fill="x", padx=16, pady=(8, 4))

        self.custom_frame = ctk.CTkFrame(theme_card, fg_color="transparent")
        self.custom_frame.pack(fill="x", padx=16, pady=(0, 4))

        self._color_buttons = {}
        self._build_preview()
        self._build_custom_pickers()
        self._on_theme_change(self.theme_var.get())

        ctk.CTkButton(
            theme_card, text="Apply Theme", height=36,
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dim"],
            command=self._apply_theme,
        ).pack(anchor="w", padx=16, pady=(4, 12))

        general_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        general_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            general_card, text="General",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w", padx=16, pady=(12, 8))

        row = ctk.CTkFrame(general_card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(row, text="Headless Mode:", font=ctk.CTkFont(size=12),
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

        ctk.CTkLabel(row2, text="Username Input Delay (s):", font=ctk.CTkFont(size=12),
                      text_color=COLORS["text"]).pack(side="left")
        self.delay_var = ctk.StringVar(value=str(self.app.config.get("username_input_delay", 2)))
        ctk.CTkEntry(
            row2, textvariable=self.delay_var, width=60, height=30,
            fg_color=COLORS["input_bg"], border_color=COLORS["border"],
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(8, 0))

        notif_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        notif_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            notif_card, text="Notifications",
            font=ctk.CTkFont(size=15, weight="bold"),
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
            ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=12),
                          text_color=COLORS["text"], width=180, anchor="w").pack(side="left")
            var = ctk.StringVar(value=self.app.config.get(key, ""))
            self._entries[key] = var
            ctk.CTkEntry(
                f, textvariable=var, height=30,
                fg_color=COLORS["input_bg"], border_color=COLORS["border"],
                font=ctk.CTkFont(size=11),
                show="*" if "token" in key.lower() else "",
            ).pack(side="left", padx=(8, 0), fill="x", expand=True)

        ctk.CTkButton(
            notif_card, text="Save Settings", height=40,
            corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dim"],
            command=self._save,
        ).pack(anchor="w", padx=16, pady=(8, 12))

    def _build_preview(self):
        for w in self.preview_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self.preview_frame, text="Preview",
            font=ctk.CTkFont(size=11, weight="bold"),
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
            font=ctk.CTkFont(size=10),
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
                font=ctk.CTkFont(size=10),
                fg_color=COLORS["input_bg"],
                hover_color=COLORS["card_hover"],
                command=lambda k=key, p=preview: self._pick_color(k, p),
            )
            btn.pack(side="left")

    def _pick_color(self, key, preview_widget):
        current = COLORS.get(key, "#888888")
        result = colorchooser.askcolor(initialcolor=current, title=f"Choose {COLOR_LABELS.get(key, key)}")
        if result and result[1]:
            hex_color = result[1]
            COLORS[key] = hex_color
            preview_widget.configure(fg_color=hex_color)
            if not hasattr(self, "_custom_colors"):
                self._custom_colors = {}
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
        if hasattr(self, "_custom_colors"):
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


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CPZC Auto Claimer")
        self.geometry("1100x720")
        self.minsize(900, 600)

        self.config = auto_claimer.load_config()
        self.claimer = None
        global COLORS
        COLORS = load_theme(self.config)
        self.configure(fg_color=COLORS["bg"])

        self.sidebar = ctk.CTkFrame(self, fg_color=COLORS["sidebar"], width=220, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=16, pady=(20, 24))

        ctk.CTkLabel(
            logo_frame, text="CPZC",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            logo_frame, text="Auto Claimer",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w")

        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "Dashboard", "home"),
            ("scan", "Auto Scan", "search"),
            ("accounts", "Accounts", "people"),
            ("generate", "Generate", "wand"),
            ("settings", "Settings", "gear"),
        ]
        for page_id, label, icon in nav_items:
            btn = SidebarButton(
                self.sidebar, text=label, icon=icon,
                command=lambda p=page_id: self.navigate_to(p),
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[page_id] = btn

        self.content = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        self.content.pack(side="left", fill="both", expand=True)
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.page_container = ctk.CTkFrame(self.content, fg_color="transparent")
        self.page_container.grid(row=0, column=0, sticky="nsew")
        self.page_container.grid_rowconfigure(0, weight=1)
        self.page_container.grid_columnconfigure(0, weight=1)

        self.log_frame = ctk.CTkFrame(self.content, fg_color="transparent", height=180)
        self.log_frame.grid(row=1, column=0, sticky="sew", padx=10, pady=(0, 10))
        self.log_frame.grid_propagate(False)
        self.log_panel = LogPanel(self.log_frame)
        self.log_panel.pack(fill="both", expand=True)

        self.pages = {}
        self.pages["dashboard"] = DashboardPage(self.page_container, self)
        self.pages["scan"] = AutoScanPage(self.page_container, self)
        self.pages["accounts"] = AccountsPage(self.page_container, self)
        self.pages["generate"] = GeneratePage(self.page_container, self)
        self.pages["settings"] = SettingsPage(self.page_container, self)

        self.active_page = None
        self.navigate_to("dashboard")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def navigate_to(self, page_id):
        if self.active_page and self.active_page in self.pages:
            self.pages[self.active_page].grid_forget()
        for name, btn in self.nav_buttons.items():
            btn.set_active(name == page_id)
        self.pages[page_id].grid(row=0, column=0, sticky="nsew")
        self.active_page = page_id
        if page_id == "scan" and self.claimer:
            self.pages["scan"]._count_username_file()

    def log(self, message):
        self.log_panel.log(message)

    def _on_close(self):
        if self.claimer and self.claimer.stop_scan:
            self.claimer.stop_scan.set()
        if self.claimer and self.claimer.driver:
            try:
                self.claimer.driver.quit()
            except Exception:
                pass
        self.destroy()

    def apply_theme(self):
        global COLORS
        COLORS = load_theme(self.config)
        self.configure(fg_color=COLORS["bg"])

        self.sidebar.configure(fg_color=COLORS["sidebar"])

        for widget in self.sidebar.winfo_children():
            widget.destroy()

        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=16, pady=(20, 24))
        ctk.CTkLabel(
            logo_frame, text="CPZC",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            logo_frame, text="Auto Claimer",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w")

        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "Dashboard", "home"),
            ("scan", "Auto Scan", "search"),
            ("accounts", "Accounts", "people"),
            ("generate", "Generate", "wand"),
            ("settings", "Settings", "gear"),
        ]
        for page_id, label, icon in nav_items:
            btn = SidebarButton(
                self.sidebar, text=label, icon=icon,
                command=lambda p=page_id: self.navigate_to(p),
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[page_id] = btn

        self.content.configure(fg_color=COLORS["bg"])

        for name, page in self.pages.items():
            page.grid_forget()
            page.destroy()

        self.pages = {}
        self.pages["dashboard"] = DashboardPage(self.page_container, self)
        self.pages["scan"] = AutoScanPage(self.page_container, self)
        self.pages["accounts"] = AccountsPage(self.page_container, self)
        self.pages["generate"] = GeneratePage(self.page_container, self)
        self.pages["settings"] = SettingsPage(self.page_container, self)

        self.log_panel.destroy()
        self.log_panel = LogPanel(self.log_frame)
        self.log_panel.pack(fill="both", expand=True)

        self.active_page = None
        self.navigate_to("settings")


if __name__ == "__main__":
    app = App()
    app.mainloop()
