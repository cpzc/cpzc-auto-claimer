"""Main application window — sidebar navigation, page routing, theme hot-reload."""

import customtkinter as ctk

from src.config import (
    FONT_FAMILY, load_config, set_app_instance, get_app_instance
)
from src.themes import COLORS, load_theme
from src.widgets import SidebarButton, LogPanel
from src.pages.dashboard import DashboardPage
from src.pages.auto_scan import AutoScanPage
from src.pages.generate import GeneratePage
from src.pages.accounts import AccountsPage
from src.pages.settings import SettingsPage
from src.pages.console import ConsolePage


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        set_app_instance(self)
        self._log_queue = []
        self.title("CPZC Auto Claimer")
        self.geometry("1100x720")
        self.minsize(900, 600)

        self.config = load_config()
        self.claimer = None
        COLORS.update(load_theme(self.config))
        self.configure(fg_color=COLORS["bg"])

        self.sidebar = ctk.CTkFrame(self, fg_color=COLORS["sidebar"], width=220, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self._build_sidebar()

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
        self.pages["console"] = ConsolePage(self.page_container, self)
        self.pages["settings"] = SettingsPage(self.page_container, self)

        self.active_page = None
        self.navigate_to("dashboard")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_sidebar(self):
        for widget in self.sidebar.winfo_children():
            widget.destroy()

        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=16, pady=(20, 24))

        ctk.CTkLabel(
            logo_frame, text="CPZC",
            font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            logo_frame, text="Auto Claimer",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w")

        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "Dashboard", "\u2302"),
            ("scan", "Auto Scan", "\u26B2"),
            ("accounts", "Accounts", "\u263A"),
            ("generate", "Generate", "\u2726"),
            ("console", "Console", "\u2328"),
            ("settings", "Settings", "\u2699"),
        ]
        for page_id, label, icon in nav_items:
            btn = SidebarButton(
                self.sidebar, text=label, icon=icon,
                command=lambda p=page_id: self.navigate_to(p),
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[page_id] = btn

    def navigate_to(self, page_id):
        if self.active_page and self.active_page in self.pages:
            self.pages[self.active_page].grid_forget()
        for name, btn in self.nav_buttons.items():
            btn.set_active(name == page_id)
        self.pages[page_id].grid(row=0, column=0, sticky="nsew")
        self.active_page = page_id
        if page_id == "console":
            self.log_frame.grid_forget()
        else:
            self.log_frame.grid(row=1, column=0, sticky="sew", padx=10, pady=(0, 10))
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
        if self.claimer and hasattr(self.claimer, "stop_scan") and not self.claimer.stop_scan.is_set():
            return
        COLORS.update(load_theme(self.config))
        self.configure(fg_color=COLORS["bg"])

        self.sidebar.configure(fg_color=COLORS["sidebar"])
        self._build_sidebar()

        self.content.configure(fg_color=COLORS["bg"])

        for name, page in self.pages.items():
            page.grid_forget()
            page.destroy()

        self.pages = {}
        self.pages["dashboard"] = DashboardPage(self.page_container, self)
        self.pages["scan"] = AutoScanPage(self.page_container, self)
        self.pages["accounts"] = AccountsPage(self.page_container, self)
        self.pages["generate"] = GeneratePage(self.page_container, self)
        self.pages["console"] = ConsolePage(self.page_container, self)
        self.pages["settings"] = SettingsPage(self.page_container, self)

        self.log_panel.destroy()
        self.log_panel = LogPanel(self.log_frame)
        self.log_panel.pack(fill="both", expand=True)

        self.active_page = None
        self.navigate_to("settings")
