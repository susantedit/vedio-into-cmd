"""
exporter.py  –  ASCII Studio 2.0
Supports: MP4, GIF, WebM, PNG sequence, TXT, HTML, ANSI animation.
Shows a live progress screen with ETA.
"""

import os
import sys
import time
import shutil
import threading
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from engine import (
    frame_to_ascii_color,
    frame_to_ascii_nocolor,
    ascii_to_image,
    get_video_info,
)
from theme import RESET, HIDE_CURSOR, SHOW_CURSOR
from utils import fmt_seconds, fmt_size


class Exporter:
    """
    Converts a source video to an ASCII-rendered output in the chosen format.

    Parameters
    ----------
    video_path   : str
    output_dir   : str         destination folder
    use_color    : bool
    width        : int
    bg_color     : tuple[int,int,int]
    font_size    : int
    export_fmt   : str         one of: mp4 gif webm png_seq txt html ansi
    keep_frames  : bool        keep temp PNG frames after export
    ui           : ui.UI
    """

    SUPPORTED = ("mp4", "gif", "webm", "png_seq", "txt", "html", "ansi")

    def __init__(
        self,
        video_path:  str,
        output_dir:  str,
        use_color:   bool,
        width:       int,
        bg_color:    tuple[int, int, int],
        font_size:   int,
        export_fmt:  str,
        keep_frames: bool,
        ui,
    ):
        self.video_path  = video_path
        self.output_dir  = Path(output_dir)
        self.use_color   = use_color
        self.width       = width
        self.bg_color    = tuple(bg_color)
        self.font_size   = font_size
        self.export_fmt  = export_fmt.lower()
        self.keep_frames = keep_frames
        self.ui          = ui

    # ── Entry point ───────────────────────────────────────────────────────────

    def run(self) -> str:
        """Run the export and return the output file path (or directory)."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        temp_dir = self.output_dir / "temp_ascii_frames"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir()

        cap   = cv2.VideoCapture(self.video_path)
        info  = get_video_info(cap)
        fps   = info["fps"]
        total = info["total_frames"]

        sys.stdout.write(HIDE_CURSOR)
        start = time.time()

        # ── Stage 1: render frames ────────────────────────────────────────────
        saved = 0
        txt_lines_all: list[str] = []
        html_frames:   list[str] = []
        ansi_frames:   list[str] = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            saved += 1

            if self.use_color:
                char_map, rgb_map = frame_to_ascii_color(frame, self.width)
            else:
                txt = frame_to_ascii_nocolor(frame, self.width)
                char_map = np.array([list(l) for l in txt.split("\n")])
                rgb_map  = None

            # PNG frame (always written for video-based formats)
            if self.export_fmt in ("mp4", "gif", "webm", "png_seq"):
                img = ascii_to_image(char_map, rgb_map, self.bg_color, self.font_size)
                img.save(str(temp_dir / f"f_{saved:05d}.png"))

            # TXT
            if self.export_fmt == "txt":
                txt_lines_all.append("".join(char_map.flatten()))

            # HTML
            if self.export_fmt == "html":
                html_frames.append(self._frame_to_html(char_map, rgb_map))

            # ANSI
            if self.export_fmt == "ansi":
                from engine import render_color_frame
                if self.use_color:
                    ansi_frames.append(render_color_frame(char_map, rgb_map))
                else:
                    ansi_frames.append("\n".join("".join(r) for r in char_map))

            # Progress
            elapsed = time.time() - start
            speed   = saved / max(elapsed, 0.001)
            eta     = (total - saved) / max(speed, 0.001)
            self.ui.export_progress(saved, total, eta, self.export_fmt)

        cap.release()
        print()  # newline after progress bar

        # ── Stage 2: compile output ───────────────────────────────────────────
        output_path = self._compile(temp_dir, saved, fps, txt_lines_all, html_frames, ansi_frames)

        # Cleanup temp
        if not self.keep_frames and temp_dir.exists():
            shutil.rmtree(temp_dir)

        sys.stdout.write(SHOW_CURSOR)

        elapsed_total = time.time() - start
        self._show_result(output_path, saved, elapsed_total)
        return str(output_path)

    # ── Compilation helpers ───────────────────────────────────────────────────

    def _compile(
        self,
        temp_dir:     Path,
        saved:        int,
        fps:          float,
        txt_lines:    list[str],
        html_frames:  list[str],
        ansi_frames:  list[str],
    ) -> Path:
        fmt = self.export_fmt
        stem = Path(self.video_path).stem

        if fmt == "png_seq":
            return temp_dir  # already saved

        elif fmt == "txt":
            out = self.output_dir / f"{stem}_ascii.txt"
            out.write_text("\n\n---\n\n".join(txt_lines), encoding="utf-8")
            return out

        elif fmt == "html":
            out = self.output_dir / f"{stem}_ascii.html"
            self._write_html(out, html_frames)
            return out

        elif fmt == "ansi":
            out = self.output_dir / f"{stem}_ascii.ans"
            out.write_text(
                "\033[2J\033[H".join(ansi_frames),
                encoding="utf-8", errors="replace"
            )
            return out

        elif fmt in ("mp4", "gif", "webm"):
            return self._compile_video(temp_dir, saved, fps, stem, fmt)

        return self.output_dir

    def _compile_video(
        self, temp_dir: Path, saved: int, fps: float, stem: str, fmt: str
    ) -> Path:
        sample_path = temp_dir / "f_00001.png"
        sample = cv2.imread(str(sample_path))
        if sample is None:
            raise RuntimeError("Frame export failed — no frames found.")

        h, w = sample.shape[:2]

        if fmt == "gif":
            from PIL import Image as PILImage
            out = self.output_dir / f"{stem}_ascii.gif"
            frames_pil = []
            for i in range(1, saved + 1):
                fp = temp_dir / f"f_{i:05d}.png"
                if fp.exists():
                    img = PILImage.open(str(fp)).convert("RGB")
                    # FASTOCTREE quantization gives much sharper palette than ADAPTIVE
                    try:
                        q_img = img.quantize(
                            colors=256,
                            method=PILImage.Quantize.FASTOCTREE,
                            dither=PILImage.Dither.FLOYDSTEINBERG,
                        )
                    except AttributeError:
                        # Older Pillow fallback
                        q_img = img.quantize(colors=256, dither=1)
                    frames_pil.append(q_img)
            if frames_pil:
                frames_pil[0].save(
                    str(out),
                    save_all=True,
                    append_images=frames_pil[1:],
                    loop=0,
                    duration=int(1000 / fps),
                    optimize=True,
                )
            return out

        ext    = "mp4" if fmt in ("mp4",) else "webm"

        # ── Codec selection with Windows fallback ─────────────────────────────
        # VP80 (WebM) is often absent on Windows OpenCV builds.
        # Try to write one test frame; if the writer is invalid, fall back to mp4v.
        if fmt == "webm":
            fourcc_candidate = cv2.VideoWriter_fourcc(*"VP80")
            test_writer = cv2.VideoWriter(
                str(self.output_dir / "_codec_test.webm"),
                fourcc_candidate, fps, (w, h)
            )
            if test_writer.isOpened():
                test_writer.release()
                import os as _os
                try: _os.remove(str(self.output_dir / "_codec_test.webm"))
                except Exception: pass
                fourcc = fourcc_candidate
            else:
                test_writer.release()
                # Fallback: use mp4v and save as .mp4 instead
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                ext    = "mp4"
                import warnings
                warnings.warn(
                    "VP80/WebM codec not available in this OpenCV build — "
                    "falling back to MP4 (mp4v). Install opencv-python with ffmpeg "
                    "support for WebM output.",
                    RuntimeWarning, stacklevel=2
                )
        else:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        out    = self.output_dir / f"{stem}_ascii.{ext}"
        writer = cv2.VideoWriter(str(out), fourcc, fps, (w, h))
        for i in range(1, saved + 1):
            fp = temp_dir / f"f_{i:05d}.png"
            f  = cv2.imread(str(fp))
            if f is not None:
                writer.write(f)
        writer.release()
        return out

    # ── HTML helpers ──────────────────────────────────────────────────────────

    def _frame_to_html(self, char_map: np.ndarray, rgb_map: np.ndarray | None) -> str:
        lines = []
        for y, row in enumerate(char_map):
            parts = []
            for x, ch in enumerate(row):
                if rgb_map is not None:
                    r, g, b = rgb_map[y, x]
                    parts.append(f'<span style="color:rgb({r},{g},{b})">{_html_escape(ch)}</span>')
                else:
                    parts.append(_html_escape(ch))
            lines.append("".join(parts))
        return "<br>".join(lines)

    def _write_html(self, out_path: Path, frames: list[str]) -> None:
        fps_val = 10   # default display FPS for HTML player
        style = """
body { background: #0d0d0d; margin: 0; padding: 1em; font-family: monospace; color: #eee; }
#player { position: relative; }
pre  { font-size: 10px; line-height: 1.15; margin: 0; white-space: pre; }
.frame { display: none; }
.frame.active { display: block; }
#controls {
  display: flex; align-items: center; gap: 12px;
  margin-top: 10px; padding: 8px 12px;
  background: #1a1a1a; border-radius: 6px;
}
#controls button {
  background: #333; color: #d4af37; border: 1px solid #555;
  padding: 4px 14px; border-radius: 4px; cursor: pointer;
  font-family: monospace; font-size: 13px;
}
#controls button:hover { background: #444; }
#scrubber { flex: 1; accent-color: #d4af37; }
#frame-label { color: #888; font-size: 12px; min-width: 80px; }
"""
        n_frames = len(frames)
        js = f"""
var frames = document.querySelectorAll('.frame');
var n = frames.length;
var current = 0;
var playing = true;
var interval = null;
var fps = {fps_val};

function showFrame(i) {{
  frames[current].classList.remove('active');
  current = ((i % n) + n) % n;
  frames[current].classList.add('active');
  document.getElementById('scrubber').value = current;
  document.getElementById('frame-label').textContent = (current+1) + ' / ' + n;
}}

function startPlay() {{
  if (interval) clearInterval(interval);
  interval = setInterval(function() {{ showFrame(current + 1); }}, 1000 / fps);
  document.getElementById('btn-play').textContent = '⏸';
  playing = true;
}}

function stopPlay() {{
  if (interval) clearInterval(interval);
  document.getElementById('btn-play').textContent = '▶';
  playing = false;
}}

document.getElementById('btn-play').addEventListener('click', function() {{
  if (playing) stopPlay(); else startPlay();
}});

document.getElementById('scrubber').addEventListener('input', function() {{
  stopPlay();
  showFrame(parseInt(this.value));
}});

document.getElementById('btn-prev').addEventListener('click', function() {{
  stopPlay(); showFrame(current - 1);
}});

document.getElementById('btn-next').addEventListener('click', function() {{
  stopPlay(); showFrame(current + 1);
}});

document.getElementById('scrubber').max = n - 1;
showFrame(0);
startPlay();
"""
        divs = "\n".join(f'<pre class="frame">{f}</pre>' for f in frames)
        controls = (
            '<div id="controls">'
            '<button id="btn-prev">⏮</button>'
            '<button id="btn-play">⏸</button>'
            '<button id="btn-next">⏭</button>'
            '<input id="scrubber" type="range" min="0" value="0" step="1">'
            '<span id="frame-label">1 / ' + str(n_frames) + '</span>'
            '</div>'
        )
        html = (
            f'<!DOCTYPE html><html lang="en">'
            f'<head><meta charset="utf-8">'
            f'<title>ASCII Studio Export</title>'
            f'<style>{style}</style></head>'
            f'<body><div id="player">{divs}</div>'
            f'{controls}'
            f'<script>{js}</script></body></html>'
        )
        out_path.write_text(html, encoding="utf-8")

    # ── Result summary ────────────────────────────────────────────────────────

    def _show_result(self, output_path: Path, frames: int, elapsed: float) -> None:
        t  = self.ui.theme
        size = ""
        try:
            if output_path.is_file():
                size = fmt_size(output_path.stat().st_size)
        except Exception:
            pass
        print(f"\n  {t.success}✔ Export complete{RESET}")
        print(f"  {t.secondary}Output:{RESET}  {t.accent}{output_path}{RESET}")
        print(f"  {t.secondary}Frames:{RESET}  {t.accent}{frames:,}{RESET}")
        print(f"  {t.secondary}Time:  {RESET}  {t.accent}{fmt_seconds(elapsed)}{RESET}")
        if size:
            print(f"  {t.secondary}Size:  {RESET}  {t.accent}{size}{RESET}")
        print()


def _html_escape(ch: str) -> str:
    return ch.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
