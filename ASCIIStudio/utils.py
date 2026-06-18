"""
utils.py  –  ASCII Studio 2.0
Shared helpers: terminal detection, system info, time formatting, drag-and-drop path cleaning.
"""

import os
import re
import sys
import time
import shutil
import platform
import threading
from pathlib import Path
from typing import Optional

# ── Terminal size ─────────────────────────────────────────────────────────────

def terminal_size() -> tuple[int, int]:
    """Return (columns, lines), falling back to (80, 24)."""
    try:
        s = os.get_terminal_size()
        return s.columns, s.lines
    except OSError:
        return 80, 24


# ── Path cleaning (drag-and-drop support) ─────────────────────────────────────

def clean_path(raw: str) -> str:
    """
    Strip surrounding quotes, escape characters, and whitespace from a path.
    Supports paths dragged into the terminal on Windows / macOS / Linux.
    """
    p = raw.strip()
    # Remove surrounding single or double quotes
    if len(p) >= 2 and p[0] in ('"', "'") and p[-1] == p[0]:
        p = p[1:-1]
    # Windows: strip trailing backslash that sometimes appears
    p = p.rstrip("\\")
    # Normalize path separators on Windows
    if os.name == "nt":
        p = p.replace("/", "\\")
    return p.strip()


# ── Time formatting ───────────────────────────────────────────────────────────

def fmt_seconds(sec: float) -> str:
    """Format seconds as MM:SS."""
    sec = max(0, int(sec))
    return f"{sec // 60:02d}:{sec % 60:02d}"


def fmt_size(bytes_: int) -> str:
    """Human-readable file size."""
    for unit in ("B", "KB", "MB", "GB"):
        if bytes_ < 1024:
            return f"{bytes_:.1f} {unit}"
        bytes_ /= 1024
    return f"{bytes_:.1f} TB"


# ── System detection ──────────────────────────────────────────────────────────

def detect_system() -> dict:
    """
    Probe terminal and system capabilities.
    Returns a dict with boolean flags and string descriptors.
    """
    info: dict = {}

    # OS / CPU / RAM
    info["os"]      = platform.system()
    info["python"]  = platform.python_version()
    info["cpu_count"] = os.cpu_count() or 1

    # RAM (best effort)
    try:
        import psutil  # type: ignore
        mem = psutil.virtual_memory()
        info["ram_total_mb"] = mem.total // (1024 * 1024)
        info["ram_used_mb"]  = mem.used  // (1024 * 1024)
    except ImportError:
        info["ram_total_mb"] = 0
        info["ram_used_mb"]  = 0

    # Terminal type
    term    = os.environ.get("TERM_PROGRAM", "")
    wt      = os.environ.get("WT_SESSION", "")
    colorterm = os.environ.get("COLORTERM", "").lower()
    info["terminal"] = (
        "Windows Terminal" if wt else
        term if term else
        "Unknown"
    )

    # ANSI / TrueColor / Unicode
    info["ansi_colors"] = sys.stdout.isatty() or os.name == "nt"
    info["true_color"]  = colorterm in ("truecolor", "24bit") or bool(wt)

    try:
        "✓".encode(sys.stdout.encoding or "utf-8")
        info["unicode"] = True
    except (UnicodeEncodeError, LookupError):
        info["unicode"] = False

    # OpenCV hardware decode flag
    try:
        import cv2
        info["opencv"]  = cv2.__version__
        info["hw_decode"] = hasattr(cv2, "CAP_PROP_HW_ACCELERATION")
    except ImportError:
        info["opencv"]  = "Not installed"
        info["hw_decode"] = False

    # Pillow
    try:
        import PIL
        info["pillow"] = PIL.__version__
    except ImportError:
        info["pillow"] = "Not installed"

    # numpy
    try:
        import numpy as np
        info["numpy"] = np.__version__
    except ImportError:
        info["numpy"] = "Not installed"

    # pygame (for sound)
    try:
        import pygame  # type: ignore
        info["pygame"] = pygame.version.ver
    except ImportError:
        info["pygame"] = None

    return info


# ── Live performance sampler ──────────────────────────────────────────────────

class PerfMonitor:
    """
    Tracks FPS, CPU, RAM, and dropped frames.
    Call .tick() each frame; read .stats for the latest snapshot.
    """

    def __init__(self, sample_interval: float = 1.0):
        self.sample_interval = sample_interval
        self._lock   = threading.Lock()
        self._times: list[float] = []
        self._dropped = 0
        self._frame   = 0
        self._total   = 0
        self.stats: dict = {
            "fps": 0.0, "cpu": 0, "ram_mb": 0,
            "frame": 0, "total": 0, "dropped": 0,
            "frame_ms": 0.0,
        }
        self._last_tick = time.perf_counter()
        self._cpu_thread = threading.Thread(target=self._sample_cpu, daemon=True)
        self._cpu_thread.start()

    def set_total(self, total: int) -> None:
        with self._lock:
            self._total = total

    def tick(self, dropped: bool = False) -> None:
        now = time.perf_counter()
        elapsed = now - self._last_tick
        self._last_tick = now
        with self._lock:
            self._frame += 1
            if dropped:
                self._dropped += 1
            self._times.append(now)
            # Keep only the last 2 seconds of timestamps
            cutoff = now - 2.0
            self._times = [t for t in self._times if t >= cutoff]
            fps  = len(self._times) / 2.0 if len(self._times) > 1 else 0.0
            self.stats["fps"]       = round(fps, 2)
            self.stats["frame"]     = self._frame
            self.stats["total"]     = self._total
            self.stats["dropped"]   = self._dropped
            self.stats["frame_ms"]  = round(elapsed * 1000, 1)

    def _sample_cpu(self) -> None:
        try:
            import psutil  # type: ignore
        except ImportError:
            # psutil not installed – mark stats as unavailable and exit thread
            with self._lock:
                self.stats["cpu"]    = None   # None signals "N/A" to the HUD
                self.stats["ram_mb"] = None
            return

        proc = psutil.Process()
        while True:
            try:
                cpu = proc.cpu_percent(interval=1.0)
                ram = proc.memory_info().rss // (1024 * 1024)
                with self._lock:
                    self.stats["cpu"]    = cpu
                    self.stats["ram_mb"] = ram
            except Exception:
                time.sleep(1)

    def reset(self) -> None:
        with self._lock:
            self._times.clear()
            self._dropped = 0
            self._frame   = 0


# ── Misc helpers ──────────────────────────────────────────────────────────────

def clear_console() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def setup_windows_terminal() -> None:
    if os.name == "nt":
        try:
            import ctypes
            k32 = ctypes.windll.kernel32
            k32.SetConsoleMode(k32.GetStdHandle(-11), 7)
            os.system("title ASCII Studio 2.0  –  Developer Susant")
        except Exception:
            pass
