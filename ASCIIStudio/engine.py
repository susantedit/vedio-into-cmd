"""
engine.py  –  ASCII Studio 2.0
Core frame-to-ASCII conversion kernels.  Pure numpy, no side-effects.
"""

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# Full luminance ramp (86 chars)
ASCII_CHARS = " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczmwqpdbkhao*#MW&8%B@$0QSXGZJKPHDAUYTRENVLCF"
_CHARS_ARRAY = np.array(list(ASCII_CHARS))

FONT_CANDIDATES = ["consola.ttf", "cour.ttf", "DejaVuSansMono.ttf", "LiberationMono-Regular.ttf"]


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    for name in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            pass
    return ImageFont.load_default()


# ── Frame → ASCII (no color) ──────────────────────────────────────────────────

def frame_to_ascii_nocolor(frame: np.ndarray, width: int) -> str:
    """Convert a BGR frame to a plain ASCII string."""
    height = max(1, int(frame.shape[0] * width / frame.shape[1] / 2))
    resized = cv2.resize(frame, (width, height))
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    n = len(ASCII_CHARS) - 1
    lines = ["".join(ASCII_CHARS[int(p / 255.0 * n)] for p in row) for row in gray]
    return "\n".join(lines)


# ── Frame → ASCII (full TrueColor) ───────────────────────────────────────────

def frame_to_ascii_color(frame: np.ndarray, width: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Returns:
        char_map  – (H, W) array of ASCII characters
        rgb_map   – (H, W, 3) uint8 RGB array
    """
    height = max(1, int(frame.shape[0] * width / frame.shape[1] / 2))
    resized = cv2.resize(frame, (width, height))
    rgb_map = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    brightness = (
        0.299 * rgb_map[:, :, 0].astype(np.float32)
        + 0.587 * rgb_map[:, :, 1].astype(np.float32)
        + 0.114 * rgb_map[:, :, 2].astype(np.float32)
    )
    char_indices = np.clip(
        (brightness / 255.0 * (len(ASCII_CHARS) - 1)).astype(np.int32),
        0, len(ASCII_CHARS) - 1
    )
    return _CHARS_ARRAY[char_indices], rgb_map


# ── Build ANSI-colored render string ─────────────────────────────────────────

def render_color_frame(char_map: np.ndarray, rgb_map: np.ndarray) -> str:
    """Build full ANSI-escape colored string for terminal output."""
    lines = []
    for row, rgb_row in zip(char_map, rgb_map):
        seg = "".join(
            f"\033[38;2;{r};{g};{b}m{c}"
            for c, (r, g, b) in zip(row, rgb_row)
        )
        lines.append(seg + "\033[0m")
    return "\n".join(lines)


# ── ASCII → PIL Image (for export) ───────────────────────────────────────────

def ascii_to_image(
    char_map: np.ndarray,
    rgb_map: np.ndarray | None,
    bg_color: tuple[int, int, int],
    font_size: int = 12,
) -> Image.Image:
    """Render char_map to a PIL Image.  rgb_map=None → white text."""
    font = _get_font(font_size)
    h, w = char_map.shape

    # Measure a single character for grid sizing
    sample_img = Image.new("RGB", (1, 1))
    sample_draw = ImageDraw.Draw(sample_img)
    bbox = sample_draw.textbbox((0, 0), "A", font=font)
    char_w = bbox[2] - bbox[0] or int(font_size * 0.6)
    char_h = bbox[3] - bbox[1] or font_size

    img = Image.new("RGB", (w * char_w, h * char_h), bg_color)
    draw = ImageDraw.Draw(img)

    for y in range(h):
        for x in range(w):
            color = tuple(rgb_map[y, x].tolist()) if rgb_map is not None else (255, 255, 255)
            draw.text((x * char_w, y * char_h), char_map[y, x], fill=color, font=font)

    return img


# ── Video info helper ─────────────────────────────────────────────────────────

def get_video_info(cap: cv2.VideoCapture) -> dict:
    fps    = cap.get(cv2.CAP_PROP_FPS)
    fps    = fps if fps > 0 else 30.0
    total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    size_bytes = 0
    try:
        # Try to get file path from cap
        pass
    except Exception:
        pass
    return {
        "fps":          fps,
        "total_frames": total,
        "width_px":     width,
        "height_px":    height,
        "duration_s":   total / fps if fps > 0 else 0,
        "aspect":       width / height if height > 0 else 1.0,
    }


# ── Benchmark ────────────────────────────────────────────────────────────────

def run_benchmark(width: int = 120, frames: int = 60) -> dict:
    """
    Synthesize random frames and benchmark conversion speed.
    Returns a dict with fps, ms_per_frame, thread info.
    """
    import time
    import threading

    dummy = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    # Color benchmark
    start = time.perf_counter()
    for _ in range(frames):
        frame_to_ascii_color(dummy, width)
    elapsed_color = time.perf_counter() - start

    # Nocolor benchmark
    start = time.perf_counter()
    for _ in range(frames):
        frame_to_ascii_nocolor(dummy, width)
    elapsed_plain = time.perf_counter() - start

    return {
        "color_fps":      round(frames / elapsed_color, 2),
        "plain_fps":      round(frames / elapsed_plain, 2),
        "color_ms":       round(elapsed_color / frames * 1000, 2),
        "plain_ms":       round(elapsed_plain / frames * 1000, 2),
        "threads":        threading.active_count(),
        "cpu_count":      threading.active_count(),
        "frames_tested":  frames,
    }
