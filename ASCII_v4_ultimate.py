"""
ASCII Art Video Player - Version 4 (Ultimate / CLI)
====================================================
Versi lengkap dengan argparse CLI. Menggabungkan v2 (no color) dan v3 (color).

Fitur:
  - argparse: semua opsi via command line
  - --color / --no-color flag
  - --width, --skip (skip setiap N frame untuk mempercepat)
  - --loop untuk mengulang video
  - --info untuk hanya tampilkan info video tanpa putar
  - Background decoder thread (selalu aktif)
  - Graceful shutdown
"""

import argparse
import cv2
import os
import sys
import time
import threading
import numpy as np
from queue import Queue, Empty

# ── Karakter set 92 karakter ──────────────────────────────────────────────────
ASCII_CHARS = (
    " `.-':_,^=;><+!rc*/z?sLTv)J7(|Fi{C}fI31tlu"
    "[neoZ5Yxjya]2ESwqkP6h9d4VpOGbUAKXHm8RD#$Bg0MNWQ%&@"
)
_CHARS_ARRAY = np.array(list(ASCII_CHARS))

# ── ANSI Escape Codes ─────────────────────────────────────────────────────────
CURSOR_HOME  = "\033[H"
CLEAR_SCREEN = "\033[2J"
HIDE_CURSOR  = "\033[?25l"
SHOW_CURSOR  = "\033[?25h"
RESET_COLOR  = "\033[0m"

# ── Warna teks untuk UI ───────────────────────────────────────────────────────
C_CYAN   = "\033[96m"
C_GREEN  = "\033[92m"
C_YELLOW = "\033[93m"
C_RED    = "\033[91m"
C_GRAY   = "\033[90m"
C_BOLD   = "\033[1m"


# ── Utility ───────────────────────────────────────────────────────────────────

def enable_ansi_windows() -> None:
    """Aktifkan ANSI escape codes"""
    if os.name == "nt":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass


def get_video_info(cap: cv2.VideoCapture) -> dict:
    """Ambil metadata video."""
    return {
        "fps"          : cap.get(cv2.CAP_PROP_FPS),
        "total_frames" : int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "width_px"     : int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height_px"    : int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "duration_s"   : cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(cap.get(cv2.CAP_PROP_FPS), 1),
    }


def print_info(video_path: str, info: dict) -> None:
    """Tampilkan informasi video ke terminal."""
    dur   = int(info["duration_s"])
    mins  = dur // 60
    secs  = dur % 60
    print(f"\n{C_BOLD}{C_CYAN}{'─' * 52}{RESET_COLOR}")
    print(f"  {C_BOLD}ASCII Video Player v4 — Ultimate Edition{RESET_COLOR}")
    print(f"{C_CYAN}{'─' * 52}{RESET_COLOR}")
    print(f"  {C_YELLOW}File       {RESET_COLOR}: {os.path.basename(video_path)}")
    print(f"  {C_YELLOW}Resolusi   {RESET_COLOR}: {info['width_px']} x {info['height_px']} px")
    print(f"  {C_YELLOW}FPS        {RESET_COLOR}: {info['fps']:.2f}")
    print(f"  {C_YELLOW}Durasi     {RESET_COLOR}: {mins:02d}:{secs:02d} ({info['total_frames']} frame)")
    print(f"{C_CYAN}{'─' * 52}{RESET_COLOR}\n")


# ── Frame Converter ───────────────────────────────────────────────────────────

def frame_to_ascii_nocolor(frame, width: int) -> str:
    """Konversi frame ke ASCII tanpa warna (lebih cepat)."""
    height = max(1, int(frame.shape[0] * width / frame.shape[1] / 2))
    resized = cv2.resize(frame, (width, height))
    gray    = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

    n_chars = len(ASCII_CHARS) - 1
    lines = []
    for row in gray:
        line = "".join(ASCII_CHARS[int(p / 255.0 * n_chars)] for p in row)
        lines.append(line)
    return "\n".join(lines)


def frame_to_ascii_color(frame, width: int) -> str:
    """Konversi frame ke ASCII art berwarna ANSI 24-bit (numpy vectorized)."""
    height = max(1, int(frame.shape[0] * width / frame.shape[1] / 2))
    resized     = cv2.resize(frame, (width, height))
    resized_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

    r = resized_rgb[:, :, 0].astype(np.float32)
    g = resized_rgb[:, :, 1].astype(np.float32)
    b = resized_rgb[:, :, 2].astype(np.float32)

    brightness   = 0.299 * r + 0.587 * g + 0.114 * b
    char_indices = np.clip(
        (brightness / 255.0 * (len(ASCII_CHARS) - 1)).astype(np.int32),
        0, len(ASCII_CHARS) - 1
    )
    char_map = _CHARS_ARRAY[char_indices]

    lines = []
    for row_i in range(height):
        parts = []
        for col_i in range(width):
            rv = int(resized_rgb[row_i, col_i, 0])
            gv = int(resized_rgb[row_i, col_i, 1])
            bv = int(resized_rgb[row_i, col_i, 2])
            ch = char_map[row_i, col_i]
            parts.append(f"\033[38;2;{rv};{gv};{bv}m{ch}")
        parts.append(RESET_COLOR)
        lines.append("".join(parts))
    return "\n".join(lines)


# ── Background Decoder Thread ─────────────────────────────────────────────────

def _frame_decoder(
    cap: cv2.VideoCapture,
    frame_queue: Queue,
    stop_event: threading.Event,
    skip: int
) -> None:
    """Worker thread: baca frame dari video ke queue dengan dukungan frame skipping."""
    frame_idx = 0
    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            break

        # Skip frame jika diminta (untuk mempercepat di PC lambat)
        if skip > 1 and frame_idx % skip != 0:
            frame_idx += 1
            continue

        frame_idx += 1
        while not stop_event.is_set():
            try:
                frame_queue.put(frame, timeout=0.05)
                break
            except Exception:
                pass

    frame_queue.put(None)  # sentinel


# ── Playback Engine ───────────────────────────────────────────────────────────

def play_video(
    video_path : str,
    width      : int  = None,
    use_color  : bool = False,
    skip       : int  = 1,
    loop       : bool = False,
    fit_screen : bool = True,
) -> None:
    """Engine utama pemutaran video ASCII."""
    if not os.path.exists(video_path):
        print(f"{C_RED}[ERROR]{RESET_COLOR} File tidak ditemukan: '{video_path}'")
        sys.exit(1)

    enable_ansi_windows()
    converter = frame_to_ascii_color if use_color else frame_to_ascii_nocolor

    play_count = 0
    while True:
        play_count += 1
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"{C_RED}[ERROR]{RESET_COLOR} Tidak bisa membuka video.")
            sys.exit(1)

        info        = get_video_info(cap)
        fps         = info["fps"] if info["fps"] > 0 else 30.0
        frame_delay = (1.0 / fps) * skip
        
        # Original video aspect ratio
        video_ar = info["width_px"] / info["height_px"]

        if play_count == 1:
            print_info(video_path, info)
            mode_str = f"{C_GREEN}WARNA (ANSI 24-bit){RESET_COLOR}" if use_color else f"{C_GRAY}HITAM-PUTIH{RESET_COLOR}"
            print(f"  Mode      : {mode_str}")
            print(f"  Ajust     : {'Auto (Terminal)' if fit_screen else f'{width} chars'}")
            print(f"  Skip      : setiap {skip} frame")
            print(f"  Loop      : {'Ya' if loop else 'Tidak'}")
            print(f"\n{C_YELLOW}Memulai dalam 2 detik... Ctrl+C untuk berhenti.{RESET_COLOR}\n")
            time.sleep(2.0)

        # Background decoder
        frame_queue = Queue(maxsize=8)
        stop_event  = threading.Event()
        decoder     = threading.Thread(
            target=_frame_decoder,
            args=(cap, frame_queue, stop_event, skip),
            daemon=True
        )
        decoder.start()

        # Setup terminal
        sys.stdout.write(HIDE_CURSOR)
        sys.stdout.write(CLEAR_SCREEN)
        sys.stdout.flush()

        frame_count   = 0
        total_frames  = max(1, info["total_frames"] // skip)

        try:
            while True:
                t_start = time.perf_counter()

                try:
                    frame = frame_queue.get(timeout=2.0)
                except Empty:
                    break

                if frame is None:
                    break

                frame_count += 1
                
                # Dynamic terminal size detection
                term_size = os.get_terminal_size()
                tw, th = term_size.columns, term_size.lines
                
                if fit_screen:
                    available_h = max(1, th - 2)
                    available_w = tw
                    # 2.0 factor for character aspect ratio
                    w_from_h = int(available_h * video_ar * 2.0)
                    current_width = min(available_w, w_from_h)
                else:
                    current_width = width if width else 120

                ascii_art = converter(frame, current_width)

                # Render
                sys.stdout.write(CURSOR_HOME)
                sys.stdout.write(ascii_art)

                # Status bar pinned to bottom
                progress = frame_count / total_frames
                bar_len  = max(10, tw - 45)
                filled   = int(bar_len * progress)
                bar      = "█" * filled + "░" * (bar_len - filled)
                loop_info = f" | Loop #{play_count}" if loop else ""
                
                sys.stdout.write(f"\033[{th};1H") # Move to last line
                sys.stdout.write(
                    f"{RESET_COLOR}{C_GRAY}[{bar}] "
                    f"{frame_count}/{total_frames}{loop_info} | Ctrl+C stop{RESET_COLOR}"
                )
                sys.stdout.flush()

                # Timing akurat
                elapsed    = time.perf_counter() - t_start
                sleep_time = frame_delay - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            stop_event.set()
            raise

        finally:
            stop_event.set()
            decoder.join(timeout=2.0)
            cap.release()

        if not loop:
            break

    # Restore terminal
    sys.stdout.write(SHOW_CURSOR)
    sys.stdout.write(RESET_COLOR)
    sys.stdout.write(f"\n\n{C_GREEN}[INFO]{RESET_COLOR} Playback selesai.\n")
    sys.stdout.flush()


# ── CLI Argument Parser ───────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog        = "ASCII_v4_ultimate.py",
        description = "ASCII Art Video Player - Ultimate Edition",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Contoh penggunaan:
  python ASCII_v4_ultimate.py vid.mp4
  python ASCII_v4_ultimate.py vid.mp4 --color --width 100
  python ASCII_v4_ultimate.py vid.mp4 --no-fit --width 140 --loop
  python ASCII_v4_ultimate.py vid.mp4 --color --skip 2
  python ASCII_v4_ultimate.py vid.mp4 --info
"""
    )

    parser.add_argument(
        "video",
        nargs   = "?",
        default = None,
        help    = "Path ke file video (mp4, avi, mkv, dll.)"
    )
    parser.add_argument(
        "--width", "-w",
        type    = int,
        default = None,
        help    = "Lebar tetap (mematikan auto-fit)"
    )

    color_group = parser.add_mutually_exclusive_group()
    color_group.add_argument(
        "--color", "-c",
        action  = "store_true",
        default = False,
        help    = "Aktifkan warna ANSI 24-bit"
    )
    color_group.add_argument(
        "--no-color",
        action  = "store_true",
        default = False,
        help    = "Paksa mode hitam-putih"
    )

    parser.add_argument(
        "--no-fit",
        action  = "store_false",
        dest    = "fit",
        default = True,
        help    = "Matikan auto-fit ke ukuran terminal"
    )

    parser.add_argument(
        "--skip", "-s",
        type    = int,
        default = 1,
        metavar = "N",
        help    = "Render setiap N frame"
    )
    parser.add_argument(
        "--loop", "-l",
        action  = "store_true",
        default = False,
        help    = "Ulangi video terus-menerus"
    )
    parser.add_argument(
        "--info", "-i",
        action  = "store_true",
        default = False,
        help    = "Hanya tampilkan info video"
    )

    return parser


# ── Entry Point ───────────────────────────────────────────────────────────────
def main() -> None:
    enable_ansi_windows()
    parser = build_parser()
    args   = parser.parse_args()

    # Jika tidak ada argumen sama sekali, mode interaktif
    if args.video is None:
        print(f"\n{C_BOLD}{C_CYAN}{'─' * 52}{RESET_COLOR}")
        print(f"  {C_BOLD}ASCII Video Player v4 — Ultimate Edition{RESET_COLOR}")
        print(f"{C_CYAN}{'─' * 52}{RESET_COLOR}")
        print(f"\n  Untuk opsi lengkap: {C_YELLOW}python ASCII_v4_ultimate.py --help{RESET_COLOR}\n")

        args.video = input("  Masukkan path video: ").strip().strip('"')
        if not args.video:
            print(f"{C_RED}[ERROR]{RESET_COLOR} Path video tidak boleh kosong.")
            sys.exit(1)

        color_input = input("  Aktifkan warna? (y/N): ").strip().lower()
        args.color  = color_input == "y"

        fit_input = input("  Auto-fit terminal size? (Y/n): ").strip().lower()
        args.fit   = fit_input != "n"

        if not args.fit:
            term_cols = os.get_terminal_size().columns
            try:
                w = input(f"  Lebar output (default 120, terminal={term_cols}): ").strip()
                args.width = int(w) if w else 120
            except ValueError:
                args.width = 120

        try:
            s = input("  Skip setiap N frame (default 1 = semua frame): ").strip()
            args.skip = int(s) if s else 1
        except ValueError:
            args.skip = 1

        loop_input = input("  Loop video? (y/N): ").strip().lower()
        args.loop   = loop_input == "y"

    # Jika sepesifikasi lebar manual, matikan fit otomatis
    if args.width is not None:
        args.fit = False

    # Validasi
    if args.skip < 1:
        args.skip = 1

    # Mode --info saja
    if args.info:
        if not os.path.exists(args.video):
            print(f"{C_RED}[ERROR]{RESET_COLOR} File tidak ditemukan: '{args.video}'")
            sys.exit(1)
        cap  = cv2.VideoCapture(args.video)
        info = get_video_info(cap)
        cap.release()
        print_info(args.video, info)
        return

    # Putar video
    try:
        play_video(
            video_path = args.video,
            width      = args.width,
            use_color  = args.color,
            skip       = args.skip,
            loop       = args.loop,
            fit_screen = args.fit
        )
    except KeyboardInterrupt:
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.write(RESET_COLOR)
        print(f"\n\n{C_YELLOW}[INFO]{RESET_COLOR} Dihentikan oleh pengguna.\n")


if __name__ == "__main__":
    main()
