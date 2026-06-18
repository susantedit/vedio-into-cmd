"""
config.py  –  ASCII Studio 2.0
Handles loading / saving ascii_studio.json and named profiles.
"""

import json
import os
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).parent / "ascii_studio.json"
PROFILES_PATH = Path(__file__).parent / "profiles.json"

DEFAULTS: dict[str, Any] = {
    "theme":       "gold",
    "width":       None,       # None = auto
    "color":       True,
    "language":    "es",       # original default language
    "fps_limit":   0,          # 0 = no limit
    "export":      "mp4",
    "skip":        1,
    "loop":        False,
    "sound":       True,
    "recent":      [],         # last 10 file paths
    "bg_color":    [0, 0, 0],
    "font_size":   12,
}

BUILTIN_PROFILES: dict[str, dict] = {
    "Cinema": {
        "color": True,   "width": None,  "skip": 1,
        "fps_limit": 0,  "font_size": 10, "export": "mp4",
    },
    "Fast": {
        "color": False,  "width": 120,   "skip": 2,
        "fps_limit": 30, "font_size": 12, "export": "mp4",
    },
    "Ultra": {
        "color": True,   "width": 200,   "skip": 1,
        "fps_limit": 0,  "font_size": 8,  "export": "mp4",
    },
    "GitHub Demo": {
        "color": True,   "width": 100,   "skip": 1,
        "fps_limit": 24, "font_size": 12, "export": "gif",
    },
}


def load() -> dict:
    """Load config from disk, filling missing keys with defaults."""
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            cfg.update(saved)
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save(cfg: dict) -> None:
    """Persist config to disk."""
    try:
        CONFIG_PATH.write_text(
            json.dumps(cfg, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    except OSError:
        pass


def add_recent(cfg: dict, path: str) -> None:
    """Prepend a path to the recent-files list (max 10, no duplicates)."""
    recent: list = cfg.get("recent", [])
    if path in recent:
        recent.remove(path)
    recent.insert(0, path)
    cfg["recent"] = recent[:10]
    save(cfg)


def load_profiles() -> dict:
    """Return merged dict of builtin + user profiles."""
    profiles = dict(BUILTIN_PROFILES)
    if PROFILES_PATH.exists():
        try:
            user = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
            profiles.update(user)
        except (json.JSONDecodeError, OSError):
            pass
    return profiles


def save_profile(name: str, settings: dict) -> None:
    """Save or update a named profile."""
    profiles = load_profiles()
    # Don't overwrite builtins silently
    profiles[name] = settings
    try:
        PROFILES_PATH.write_text(
            json.dumps(profiles, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    except OSError:
        pass


def apply_profile(cfg: dict, profile_name: str) -> dict:
    """Overlay a profile onto cfg and return the merged dict."""
    profiles = load_profiles()
    if profile_name in profiles:
        cfg.update(profiles[profile_name])
    return cfg
