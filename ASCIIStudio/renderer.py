"""
renderer.py  –  ASCII Studio 2.0
Multi-threaded real-time playback with:
  • Live performance HUD
  • Pause / resume / replay  (Space)
  • Screenshot hotkey        (S)
  • Quit                     (Q)
  • Help overlay             (H)
  • Sound via pygame         (optional)
  • FPS-limited timing
"""

import os
import sys
import time
import threading
from pathlib import Path
from queue import Queue

import cv2
import numpy as np

from engine import (
    frame_to_ascii_color,
    frame_to_ascii_nocolor,
    render_color_frame,
    get_video_info,
)
from theme import HIDE_CURSOR, SHOW_CURSOR, CURSOR_HOME, CLEAR_SCREEN, RESET
from utils import terminal_size, PerfMonitor, fmt_seconds

# ── Optional PIL for screenshot ───────────────────────────────────────────────
try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

# ── Non-blocking keyboard reader (cross-platform) ────────────────────────────

if os.name == "nt":
    import msvcrt

    def _kbhit() -> bool:
        return msvcrt.kbhit()

    def _getch() -> str:
        ch = msvcrt.getwch()
        return ch.lower()

else:
    import tty
    import termios
    import select

    def _kbhit() -> bool:
        dr, _, _ = select.select([sys.stdin], [], [], 0)
        return bool(dr)

    def _getch() -> str:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        return ch.lower()


class Renderer:
    """
    Plays an ASCII video in the terminal.

    Parameters
    ----------
    video_path : str
    use_color  : bool
    width      : int | None    (None = auto)
    skip       : int           (render 1 in every `skip` frames)
    loop       : bool
    fps_limit  : int           (0 = no cap beyond source FPS)
    sound      : bool          (play audio track via pygame if available)
    ui         : ui.UI         (for HUD rendering)
    """

    def __init__(
        self,
        video_path: str,
        use_color:  bool,
        width:      int | None,
        skip:       int,
        loop:       bool,
        fps_limit:  int,
        sound:      bool,
        ui,
    ):
        self.video_path = video_path
        self.use_color  = use_color
        self.width      = width
        self.skip       = max(1, skip)
        self.loop       = loop
        self.fps_limit  = fps_limit
        self.sound      = sound
        self.ui         = ui
        self._stop      = threading.Event()
        self._paused    = threading.Event()
        self._replay    = threading.Event()   # set to trigger replay from start
        self._show_help = threading.Event()   # set to show help overlay
        self._perf      = PerfMonitor()
        self._screenshot_dir = Path(video_path).parent
        self._last_frame: np.ndarray | None = None   # kept for screenshot

    # ── Keyboard polling thread ───────────────────────────────────────────────

    def _kb_poll(self) -> None:
        """
        Runs in its own daemon thread.  Polls for keypresses without blocking
        the render loop.  Handles:
          Space  – pause / resume
          R      – replay from beginning
          S      – save screenshot of current frame
          H      – toggle help overlay
          Q      – quit
        """
        while not self._stop.is_set():
            try:
                if _kbhit():
                    ch = _getch()
                    if ch == " ":
                        if self._paused.is_set():
                            self._paused.clear()
                        else:
                            self._paused.set()
                    elif ch == "r":
                        self._paused.clear()
                        self._replay.set()
                        self._stop.set()
                    elif ch == "s":
                        if self._last_frame is not None:
                            f_idx = self._perf.stats.get("frame", 0)
                            threading.Thread(
                                target=self._take_screenshot,
                                args=(self._last_frame.copy(), f_idx),
                                daemon=True,
                            ).start()
                    elif ch == "h":
                        if self._show_help.is_set():
                            self._show_help.clear()
                        else:
                            self._show_help.set()
                    elif ch in ("q", "\x03", "\x1b"):   # Q, Ctrl+C, Esc
                        self._paused.clear()
                        self._stop.set()
            except Exception:
                pass
            time.sleep(0.02)

    # ── Sound helpers ─────────────────────────────────────────────────────────

    def _start_audio(self) -> None:
        if not self.sound:
            return
        try:
            import pygame  # type: ignore
            pygame.mixer.init()
            pygame.mixer.music.load(self.video_path)
            pygame.mixer.music.play()
        except Exception:
            pass

    def _stop_audio(self) -> None:
        try:
            import pygame  # type: ignore
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except Exception:
            pass

    # ── Screenshot helper ─────────────────────────────────────────────────────

    def _take_screenshot(self, frame: np.ndarray, frame_idx: int) -> None:
        if not _PIL_OK:
            return
        try:
            from engine import frame_to_ascii_color, ascii_to_image
            char_map, rgb_map = frame_to_ascii_color(frame, self.width or 120)
            img = ascii_to_image(char_map, rgb_map, (0, 0, 0))
            out = self._screenshot_dir / f"screenshot_{frame_idx:05d}.png"
            img.save(str(out))
        except Exception:
            pass

    # ── Decoder thread ────────────────────────────────────────────────────────

    def _decoder(self, cap: cv2.VideoCapture, q: Queue) -> None:
        idx = 0
        while not self._stop.is_set():
            # respect pause
            while self._paused.is_set() and not self._stop.is_set():
                time.sleep(0.05)
            ret, frame = cap.read()
            if not ret:
                break
            if self.skip > 1 and idx % self.skip != 0:
                idx += 1
                continue
            idx += 1
            while not self._stop.is_set():
                try:
                    q.put(frame, timeout=0.05)
                    break
                except Exception:
                    pass
        q.put(None)

    # ── Main playback loop ────────────────────────────────────────────────────

    def play(self) -> dict:
        """
        Run playback.  Returns stats dict: {frames, fps_avg, elapsed_s}.
        """
        cap  = cv2.VideoCapture(self.video_path)
        info = get_video_info(cap)
        src_fps   = info["fps"]
        total_raw = info["total_frames"]
        video_ar  = info["aspect"]
        total_playback = max(1, total_raw // self.skip)

        # Compute target frame delay
        target_fps = min(src_fps, self.fps_limit) if self.fps_limit > 0 else src_fps
        target_fps = max(1.0, target_fps)
        frame_delay = 1.0 / target_fps * self.skip

        self._perf.set_total(total_playback)
        start_time = time.time()

        self._start_audio()

        # Start keyboard polling thread
        kb_thread = threading.Thread(target=self._kb_poll, daemon=True)
        kb_thread.start()

        sys.stdout.write(HIDE_CURSOR + CLEAR_SCREEN)
        sys.stdout.flush()

        try:
            while True:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                q = Queue(maxsize=16)
                self._stop.clear()
                self._replay.clear()

                dec_thread = threading.Thread(target=self._decoder, args=(cap, q), daemon=True)
                dec_thread.start()

                self._perf.reset()

                try:
                    self._render_loop(q, video_ar, frame_delay, total_playback, info)
                except KeyboardInterrupt:
                    self._stop.set()

                self._stop.set()
                dec_thread.join(timeout=1.0)

                # Replay requested (R key)
                if self._replay.is_set():
                    self._replay.clear()
                    self._stop.clear()
                    continue

                if not self.loop:
                    break

        finally:
            self._stop.set()          # ensure kb thread exits
            cap.release()
            self._stop_audio()
            sys.stdout.write(SHOW_CURSOR + RESET + "\n")
            sys.stdout.flush()

        elapsed = time.time() - start_time
        perf    = self._perf.stats
        return {
            "frames":    perf.get("frame", 0),
            "fps_avg":   perf.get("fps",   0.0),
            "elapsed_s": elapsed,
        }

    def _render_loop(
        self,
        q:              Queue,
        video_ar:       float,
        frame_delay:    float,
        total_playback: int,
        info:           dict,
    ) -> None:
        cols, lines = terminal_size()
        perf = self._perf

        while True:
            ts = time.perf_counter()

            # Handle pause — keep screen alive, show PAUSED tag
            while self._paused.is_set():
                if self._stop.is_set():
                    return
                cols, lines = terminal_size()
                t = self.ui.theme
                sys.stdout.write(
                    f"\033[{lines};1H\033[2K"
                    f"  {t.warning}⏸  PAUSED  —  Space to resume  R to replay  Q to quit{RESET}"
                )
                sys.stdout.flush()
                time.sleep(0.1)

            if self._stop.is_set():
                return

            frame = q.get(timeout=2.0)
            if frame is None:
                return

            self._last_frame = frame   # store for screenshot

            # Recalculate width every frame (terminal can be resized)
            try:
                cols, lines = terminal_size()
            except Exception:
                pass

            if self.width is None:
                avail_h = max(1, lines - 3)
                w_from_h = int(avail_h * video_ar * 2.0)
                cur_w = min(cols, w_from_h)
            else:
                cur_w = self.width

            # Render frame
            if self.use_color:
                char_map, rgb_map = frame_to_ascii_color(frame, cur_w)
                art = render_color_frame(char_map, rgb_map)
            else:
                art = frame_to_ascii_nocolor(frame, cur_w)

            perf.tick()

            # Write frame
            sys.stdout.write(CURSOR_HOME + art)

            # ── Bottom status bar ─────────────────────────────────────────────
            stats  = perf.stats
            f_cnt  = stats["frame"]
            frac   = f_cnt / total_playback
            bar_w  = max(10, cols - 52)
            bar    = self.ui.theme.progress_bar(frac, bar_w)
            eta    = fmt_seconds((total_playback - f_cnt) / max(1, stats["fps"]))
            t      = self.ui.theme
            status = (
                f"{bar}  "
                f"{t.accent}{int(frac*100):>3}%{RESET}  "
                f"{t.secondary}FPS {stats['fps']:<6}{RESET}"
                f"{t.muted}ETA {eta}  [Space=pause R=replay S=shot H=help Q=quit]{RESET}"
            )
            sys.stdout.write(f"\033[{lines};1H\033[2K{status}")

            # ── Perf HUD (second-to-last line) ────────────────────────────────
            self.ui.perf_hud(stats, cols, max(1, lines - 1))

            # ── Help overlay (third-to-last line block) ───────────────────────
            if self._show_help.is_set():
                help_line = (
                    f"  {t.primary}[Space]{RESET}{t.muted}Pause  "
                    f"{t.primary}[R]{RESET}{t.muted}Replay  "
                    f"{t.primary}[S]{RESET}{t.muted}Screenshot  "
                    f"{t.primary}[H]{RESET}{t.muted}Help  "
                    f"{t.primary}[Q]{RESET}{t.muted}Quit{RESET}"
                )
                sys.stdout.write(f"\033[{max(1, lines - 2)};1H\033[2K{help_line}")

            sys.stdout.flush()

            # Timing
            elapsed = time.perf_counter() - ts
            sleep_t = frame_delay - elapsed
            if sleep_t > 0:
                time.sleep(sleep_t)
