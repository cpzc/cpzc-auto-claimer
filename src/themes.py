"""Theme presets, color labels, and theme loader."""

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
