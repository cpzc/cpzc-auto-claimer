"""Accounts page — account table, login methods, inbox opener."""

import os
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog

import customtkinter as ctk
from colorama import Fore

from src.config import SCRIPT_DIR, FONT_FAMILY
from src.themes import COLORS
from src.engine import TikTokSeleniumClaimer
from src.account_creation import create_account


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
            font=ctk.CTkFont(family=FONT_FAMILY, size=28, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(0, 20))

        login_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        login_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            login_card, text="Login to TikTok",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w", padx=16, pady=(12, 8))

        self.login_status = ctk.CTkLabel(
            login_card, text="Not logged in",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
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
        ]
        self.login_buttons = []
        for i, (text, method) in enumerate(login_methods):
            btn = ctk.CTkButton(
                btn_frame, text=text, height=32,
                corner_radius=6,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                fg_color=COLORS["border"],
                hover_color=COLORS["accent_dim"],
                command=lambda m=method: self._login(m),
            )
            btn.grid(row=0, column=i, padx=3, sticky="nsew")
            self.login_buttons.append(btn)

        ctk.CTkButton(
            login_card, text="Save Cookies", height=28, width=100,
            corner_radius=6,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color=COLORS["success"],
            hover_color="#00b368",
            text_color="#000000",
            command=self._save_cookies,
        ).pack(anchor="w", padx=16, pady=(0, 12))

        table_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        table_card.pack(fill="both", expand=True, pady=(0, 12))

        header_row = ctk.CTkFrame(table_card, fg_color="transparent")
        header_row.pack(fill="x", padx=16, pady=(12, 4))

        ctk.CTkLabel(header_row, text="Username",
                      font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                      text_color=COLORS["accent"], width=250, anchor="w").pack(side="left")
        ctk.CTkLabel(header_row, text="Email",
                      font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
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
            font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=COLORS["text_dim"],
        )

        self.status_label = ctk.CTkLabel(
            table_card, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=COLORS["text_dim"],
        )
        self.status_label.pack(anchor="w", padx=16, pady=(0, 8))

        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(0, 12))
        btn_frame.columnconfigure((0, 1), weight=1)

        self.login_btn = ctk.CTkButton(
            btn_frame, text="Login", height=44,
            corner_radius=10,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dim"],
            command=self._login_account,
        )
        self.login_btn.grid(row=0, column=0, padx=(0, 6), sticky="nsew")

        self.inbox_btn = ctk.CTkButton(
            btn_frame, text="Open Inbox", height=44,
            corner_radius=10,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            fg_color=COLORS["success"],
            hover_color="#00b368",
            text_color="#000000",
            command=self._open_inbox,
        )
        self.inbox_btn.grid(row=0, column=1, padx=(6, 0), sticky="nsew")

        self.after(10, self._load_accounts)

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
                          font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                          text_color=COLORS["text"], width=250, anchor="w").pack(side="left", padx=(10, 0))
            ctk.CTkLabel(row, text=acct["email"] or "\u2014",
                          font=ctk.CTkFont(family=FONT_FAMILY, size=12),
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
        self.app.claimer = TikTokSeleniumClaimer(
            headless=self.app.config.get("headless", False),
            username_input_delay=self.app.config.get("username_input_delay", 2),
        )
        self.app.log("Setting up browser...")
        self.app.after(0, lambda: self._set_account_buttons(loading=True))
        if not self.app.claimer.setup_driver():
            self.app.log("Failed to setup browser")
            self.app.after(0, lambda: self._set_account_buttons(loading=False))
            return False
        self.app.after(0, lambda: self._set_account_buttons(loading=False))
        self.app.log("Browser ready")
        return True

    def _set_account_buttons(self, loading=False):
        state = "disabled" if loading else "normal"
        self.login_btn.configure(state=state)
        self.inbox_btn.configure(state=state)

    def _login_account(self):
        if self.selected_idx is None:
            messagebox.showwarning("No Selection", "Select an account from the table first")
            return
        acct = self.accounts[self.selected_idx]
        if not self._ensure_driver():
            return
        self.login_btn.configure(state="disabled")
        self.inbox_btn.configure(state="disabled")
        self.app.log(f"Logging in as {acct['username']}...")

        def do_login():
            def gui_pause(prompt):
                clean = prompt.replace(Fore.YELLOW, "").replace(Fore.WHITE, "")
                event = threading.Event()
                def show():
                    messagebox.showinfo("Action Required", clean)
                    event.set()
                self.app.after(0, show)
                event.wait(timeout=300)
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
                    self.app.after(0, lambda u=self.app.claimer.current_username: self.login_status.configure(text=f"Logged in as @{u}", text_color=COLORS["success"]))
                else:
                    self.app.after(0, lambda: self.app.log("Login succeeded but edit profile setup failed"))
                    self.app.after(0, lambda: self.login_status.configure(text="Login failed", text_color=COLORS["error"]))
            else:
                self.app.after(0, lambda: self.app.log(f"Login failed for {acct['username']}"))
                self.app.after(0, lambda: self.login_status.configure(text="Login failed", text_color=COLORS["error"]))
                self.app.after(0, lambda: messagebox.showerror("Login Failed", f"Could not login as {acct['username']}"))
            self.app.after(0, lambda: self.login_btn.configure(state="normal"))
            self.app.after(0, lambda: self.inbox_btn.configure(state="normal"))

        threading.Thread(target=do_login, daemon=True).start()

    def _open_inbox(self):
        if self.selected_idx is None:
            messagebox.showwarning("No Selection", "Select an account from the table first")
            return
        acct = self.accounts[self.selected_idx]
        if not acct["email"] or not acct["email_pass"]:
            messagebox.showwarning("No Email", "This account has no email credentials")
            return
        if not self.app.claimer._is_firstmail_email(acct["email"]):
            messagebox.showwarning("Not FirstMail", f"Only FirstMail emails can be used for inbox.\nGot: {acct['email']}")
            return
        if not self._ensure_driver():
            return

        self.login_btn.configure(state="disabled")
        self.inbox_btn.configure(state="disabled")
        self.app.log(f"Opening inbox for {acct['email']}...")

        def do_inbox():
            def gui_pause(prompt):
                clean = prompt.replace(Fore.YELLOW, "").replace(Fore.WHITE, "")
                event = threading.Event()
                def show():
                    messagebox.showinfo("Action Required", clean)
                    event.set()
                self.app.after(0, show)
                event.wait(timeout=300)
            self.app.claimer.open_inbox(acct["email"], acct["email_pass"], pause_fn=gui_pause)
            self.app.after(0, lambda: self.app.log("Inbox opened"))
            self.app.after(0, lambda: self.login_btn.configure(state="normal"))
            self.app.after(0, lambda: self.inbox_btn.configure(state="normal"))

        threading.Thread(target=do_inbox, daemon=True).start()

    def _login(self, method):
        if self.app.claimer and self.app.claimer.driver:
            self.app.claimer.cleanup()
        self.app.claimer = TikTokSeleniumClaimer(
            headless=self.app.config.get("headless", False),
            username_input_delay=self.app.config.get("username_input_delay", 2),
        )

        def setup_and_login():
            self.app.after(0, lambda: self.login_status.configure(text="Setting up browser...", text_color=COLORS["accent"]))
            self.app.after(0, lambda: self._set_buttons(loading=True))
            if not self.app.claimer.setup_driver():
                self.app.after(0, lambda: self.login_status.configure(text="Browser setup failed", text_color=COLORS["error"]))
                self.app.after(0, lambda: self._set_buttons(loading=False))
                self.app.after(0, lambda: messagebox.showerror("Error", "Failed to setup browser. Check Chrome/Chromium is installed."))
                return
            self.app.after(0, lambda: self.login_status.configure(text="Browser ready", text_color=COLORS["success"]))
            self.app.after(0, lambda: self._set_buttons(loading=False))
            self._do_login(method)

        threading.Thread(target=setup_and_login, daemon=True).start()

    def _set_buttons(self, loading=False):
        state = "disabled" if loading else "normal"
        for btn in self.login_buttons:
            btn.configure(state=state)

    def _do_login(self, method):
        def do_login():
            logged_in = False
            try:
                if method == "manual":
                    self.app.log("Opening TikTok login page \u2014 log in manually in the browser window")
                    self.app.claimer.driver.get("https://www.tiktok.com/login")
                    event = threading.Event()
                    def show_manual():
                        messagebox.showinfo(
                            "Manual Login",
                            "Log in to TikTok in the browser window.\nClick OK after you have logged in."
                        )
                        event.set()
                    self.app.after(0, show_manual)
                    event.wait(timeout=300)
                    logged_in = self.app.claimer.verify_logged_in()

                elif method == "cookies_json":
                    path = os.path.join(SCRIPT_DIR, "data", "cookies.json")
                    if not os.path.exists(path):
                        self.app.log(f"File not found: {path}")
                        self.app.after(0, lambda: messagebox.showerror("Error", f"File not found:\n{path}"))
                        return
                    logged_in = self.app.claimer.login_with_cookies(path)

                elif method == "cookies_session":
                    path = os.path.join(SCRIPT_DIR, "data", "sessions.txt")
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
                        event = threading.Event()
                        def show():
                            messagebox.showinfo("Info", clean)
                            event.set()
                        self.app.after(0, show)
                        event.wait(timeout=300)
                    logged_in = create_account(
                        self.app.claimer.driver, input_fn=gui_input, pause_fn=gui_pause
                    )
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
