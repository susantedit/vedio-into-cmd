"""
theme.py  –  ASCII Studio 2.0
Loads a JSON theme and exposes ANSI color helpers.
"""

import json
import os
from pathlib import Path
from typing import Optional

THEMES_DIR = Path(__file__).parent / "themes"

# ── ANSI helpers ──────────────────────────────────────────────────────────────
RESET        = "\033[0m"
BOLD         = "\033[1m"
DIM          = "\033[2m"
HIDE_CURSOR  = "\033[?25l"
SHOW_CURSOR  = "\033[?25h"
CURSOR_HOME  = "\033[H"
CLEAR_SCREEN = "\033[2J"
CLEAR_LINE   = "\033[2K"


def rgb(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


def rgb_bg(r: int, g: int, b: int) -> str:
    return f"\033[48;2;{r};{g};{b}m"


def hyperlink(url: str, text: str) -> str:
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"


def available_themes() -> list[str]:
    if not THEMES_DIR.exists():
        return []
    return [p.stem for p in THEMES_DIR.glob("*.json")]


class Theme:
    def __init__(self, name: str = "gold"):
        self.name = name
        self._data: dict = {}
        self._load(name)

    # ── loading ───────────────────────────────────────────────────────────────
    def _load(self, name: str) -> None:
        path = THEMES_DIR / f"{name}.json"
        if not path.exists():
            path = THEMES_DIR / "gold.json"
        try:
            self._data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._data = {}
        self.name = self._data.get("name", name)

    def reload(self, name: str) -> None:
        self._load(name)

    # ── color getters ─────────────────────────────────────────────────────────
    def _c(self, key: str) -> str:
        v = self._data.get(key, [200, 200, 200])
        return rgb(*v)

    @property
    def primary(self)   -> str: return self._c("primary")
    @property
    def secondary(self) -> str: return self._c("secondary")
    @property
    def accent(self)    -> str: return self._c("accent")
    @property
    def success(self)   -> str: return self._c("success")
    @property
    def warning(self)   -> str: return self._c("warning")
    @property
    def error(self)     -> str: return self._c("error")
    @property
    def muted(self)     -> str: return self._c("muted")

    # ── border characters ─────────────────────────────────────────────────────
    @property
    def border(self)    -> str: return self._data.get("border",    "═")
    @property
    def corner_tl(self) -> str: return self._data.get("corner_tl", "╔")
    @property
    def corner_tr(self) -> str: return self._data.get("corner_tr", "╗")
    @property
    def corner_bl(self) -> str: return self._data.get("corner_bl", "╚")
    @property
    def corner_br(self) -> str: return self._data.get("corner_br", "╝")
    @property
    def side(self)      -> str: return self._data.get("side",      "║")
    @property
    def bar_fill(self)  -> str: return self._data.get("bar_fill",  "█")
    @property
    def bar_empty(self) -> str: return self._data.get("bar_empty", "░")

    # ── box drawing helpers ───────────────────────────────────────────────────
    def box_top(self, width: int, title: str = "") -> str:
        inner = width - 2
        if title:
            pad  = max(0, inner - len(title) - 2)
            left = pad // 2
            right = pad - left
            content = f" {title} ".center(inner, self.border)
        else:
            content = self.border * inner
        return (
            f"{self.primary}{self.corner_tl}"
            f"{content}"
            f"{self.corner_tr}{RESET}"
        )

    def box_bottom(self, width: int) -> str:
        return (
            f"{self.primary}{self.corner_bl}"
            f"{self.border * (width - 2)}"
            f"{self.corner_br}{RESET}"
        )

    def box_row(self, width: int, content: str = "") -> str:
        return f"{self.primary}{self.side}{RESET}{content}{self.primary}{self.side}{RESET}"

    def progress_bar(self, fraction: float, bar_width: int = 40) -> str:
        filled = int(bar_width * max(0.0, min(1.0, fraction)))
        empty  = bar_width - filled
        return (
            f"{self.primary}{self.bar_fill * filled}"
            f"{self.muted}{self.bar_empty * empty}{RESET}"
        )

    def fmt(self, text: str, color: str) -> str:
        return f"{color}{text}{RESET}"
