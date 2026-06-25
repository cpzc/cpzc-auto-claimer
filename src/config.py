"""Shared configuration, globals, and the GUI print override."""

import builtins
import json
import os
import re
import threading

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FONT_FAMILY = "Segoe UI"
FONT_FAMILY_MONO = "Cascadia Code"

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_log_lock = threading.Lock()

_app_instance = None


def set_app_instance(instance):
    global _app_instance
    _app_instance = instance


def get_app_instance():
    return _app_instance


def _gui_print(*args, **kwargs):
    msg = " ".join(str(a) for a in args)
    msg = _ANSI_RE.sub("", msg).strip()
    if not msg:
        return
    inst = get_app_instance()
    if inst and hasattr(inst, "_log_queue"):
        with _log_lock:
            inst._log_queue.append(msg)


def load_config():
    config_path = os.path.join(SCRIPT_DIR, "config.json")
    defaults = {
        "discord_webhook_url": "",
        "telegram_bot_token": "",
        "telegram_chat_id": "",
        "username_input_delay": 2,
        "headless": False,
    }
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return defaults
    for k, v in defaults.items():
        config.setdefault(k, v)
    return config


builtins.print = _gui_print
