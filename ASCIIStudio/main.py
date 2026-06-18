"""
main.py  –  ASCII Studio 2.0
Entry point.  Wires together config, UI, renderer, and exporter.
"""

import sys
import os
import time
import random
from pathlib import Path

# Ensure the project directory is on sys.path so sibling modules are found
sys.path.insert(0, str(Path(__file__).parent))

import argparse
import config as cfg_mod
from theme   import Theme, RESET, BOLD
from ui      import UI
from utils   import (
    setup_windows_terminal,
    detect_system,
    clean_path,
    clear_console,
    terminal_size,
)
from engine       import get_video_info
import plugin_loader
import cv2


# ── Tips pool — original 4 tips preserved + new ones added ───────────────────
TIPS = [
    "Higher output widths provide striking shading transitions, but require smaller console fonts.",
    "Color rendering processing parses absolute TrueColor buffers across active multi-threaded matrix arrays.",
    "Export modes compile image arrays directly back into stable, custom background .mp4 containers.",
    "You can cleanly drop directories and video targets straight into this active platform window.",
    "Export to HTML for a shareable animated web page — no install needed to view.",
    "Use the Cinema profile for the highest quality playback experience.",
    "Press H during playback to see all keyboard shortcuts.",
    "GIF export loops automatically — perfect for GitHub READMEs.",
    "Run the benchmark to see how fast your CPU handles conversion.",
]

# ── Branding: exact original logo ────────────────────────────────────────────
# The two-line block-font logo from the original vediointocmd.py
LOGO_BLOCK = r"""
██████╗ ███████╗██╗   ██╗███████╗██╗      ██████╗  ██████╗ ███████╗██████╗
██╔══██╗██╔════╝██║   ██║██╔════╝██║     ██╔═══██╗██╔══██╗██╔════╝██╔══██╗
██║  ██║█████╗  ██║   ██║█████╗  ██║     ██║   ██║██████╔╝█████╗  ██████╔╝
██║  ██║██╔══╝  ╚██╗ ██╔╝██╔══╝  ██║     ██║   ██║██╔═══╝ ██╔══╝  ██╔══██╗
██████╔╝███████╗ ╚████╔╝ ███████╗███████╗╚██████╔╝██║     ███████╗██║  ██║
╚═════╝ ╚══════╝  ╚═══╝  ╚══════╝╚══════╝ ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═╝

███████╗██╗   ██╗███████╗ █████╗ ███╗   ██╗████████╗
██╔════╝██║   ██║██╔════╝██╔══██╗████╗  ██║╚══██╔══╝
███████╗██║   ██║███████╗███████║██╔██╗ ██║   ██║
╚════██║██║   ██║╚════██║██╔══██║██║╚██╗██║   ██║
███████║╚██████╔╝███████║██║  ██║██║ ╚████║   ██║
╚══════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝
"""

# Compact plain-ASCII fallback for narrow terminals (< 90 cols)
LOGO_COMPACT = r"""
 ____  _____     _______ _     ___  ____  _____ ____
|  _ \| ____|\ / / ____| |   / _ \|  _ \| ____|  _ \
| | | |  _|   V /|  _| | |  | | | | |_) |  _| | |_) |
| |_| | |___  | | |___| |___| |_| |  __/| |___|  _ <
|____/|_____| |_||_____|_____\___/|_|   |_____|_| \_\

  ███████╗██╗   ██╗███████╗ █████╗ ███╗   ██╗████████╗
  ╚════╝  ██║   ██║  ███╔╝ ██╔══██╗████╗  ██║╚══██╔══╝
  ███████╗██║   ██║███╔╝   ███████║██╔██╗ ██║   ██║
       ╚═╝██║   ██║███╗    ██╔══██║██║╚██╗██║   ██║
  ███████║╚██████╔╝███████╗██║  ██║██║ ╚████║   ██║
  ╚══════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝
"""

# Goodbye / thank-you screen (original exact art)
GOODBYE_ART = r"""
████████╗██╗  ██╗ █████╗ ███╗   ██╗██╗ ██╗
╚══██╔══╝██║  ██║██╔══██╗████╗  ██║██║██╔╝
   ██║   ███████║███████║██╔██╗ ██║█████╔╝
   ██║   ██╔══██║██╔══██║██║╚██╗██║██╔═██╗
   ██║   ██║  ██║██║  ██║██║ ╚████║██║  ██╗
   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝
"""

# Social links (exact original URLs)
SOCIAL_LINKS = [
    ("󰊤 GitHub",    "https://github.com/susantedit"),
    ("󰗃 YouTube",   "https://youtube.com/@developersusant"),
    ("󰋾 Instagram", "https://instagram.com/susantgamerz"),
    ("󰌻 LinkedIn",  "https://linkedin.com/in/kantaraj-luitel"),
    ("󰐱 Pinterest", "https://pinterest.com/susantluitel"),
    ("󰖂 WhatsApp",  "https://wa.me/9779708838261"),
]


def show_logo(ui: UI) -> None:
    from theme import hyperlink
    clear_console()
    t    = ui.theme
    cols, _ = terminal_size()

    # Wide terminal → full original block-font logo
    # Narrow terminal (<90 cols) → compact fallback
    art = LOGO_BLOCK if cols >= 90 else LOGO_COMPACT
    print(f"{t.primary}{art}{RESET}")

    # Original branding banner box (exact replica)
    print(f" {t.accent}╭──────────────────────────────────────────────────────────────────────────╮{RESET}")
    print(f" {t.accent}│{RESET}                {BOLD}{t.secondary}DEVELOPER SUSANT ASCII VIDEO PIPELINE v2.0{RESET}                {t.accent}│{RESET}")
    print(f" {t.accent}╰──────────────────────────────────────────────────────────────────────────╯{RESET}")
    print(f"    {t.muted}CODE • BUILD • SOLVE • REPEAT{RESET}\n")

    # Professional links (exact original set)
    print(f"    {t.primary}» Professional Core Links{RESET}")
    row1 = [SOCIAL_LINKS[0], SOCIAL_LINKS[1], SOCIAL_LINKS[2]]
    row2 = [SOCIAL_LINKS[3], SOCIAL_LINKS[4], SOCIAL_LINKS[5]]
    line1 = "       •  ".join(f"{t.muted}{hyperlink(url, label)}{RESET}" for label, url in row1)
    line2 = "  •  ".join(f"{t.muted}{hyperlink(url, label)}{RESET}" for label, url in row2)
    print(f"    {line1}")
    print(f"    {line2}\n")
    time.sleep(2)


# ── Main menu ─────────────────────────────────────────────────────────────────

def main_menu(ui: UI, cfg: dict) -> str:
    """Display the main menu and return the user's choice key."""
    clear_console()
    t = ui.theme
    recent = cfg.get("recent", [])

    print(t.box_top(54, " ASCII STUDIO 2.0 "))
    items = [
        ("P", "Play Video",        "preview in terminal"),
        ("E", "Export",            "render to file"),
        ("S", "Settings",          "configure options"),
        ("T", "Themes",            "switch visual theme"),
        ("R", "Recent Files",      f"{len(recent)} saved" if recent else "none yet"),
        ("L", "Load Profile",      "Cinema / Fast / Ultra…"),
        ("B", "Benchmark",         "test conversion speed"),
        ("H", "Help",              "controls & shortcuts"),
        ("Q", "Quit",              ""),
    ]
    for key, label, hint in items:
        print(
            f"  {t.primary}{t.side}{RESET}  "
            f"[{t.secondary}{key}{RESET}] "
            f"{t.accent}{label:<18}{RESET}"
            f"{t.muted}{hint}{RESET}"
        )
    print(t.box_bottom(54))

    tip = random.choice(TIPS)
    print(f"\n  {t.warning}Tip:{RESET} {t.muted}{tip}{RESET}\n")

    return input(f"  {t.primary}Select: {RESET}").strip().upper()


# ── Video path input ──────────────────────────────────────────────────────────

def ask_video_path(ui: UI, cfg: dict) -> str | None:
    t = ui.theme
    recent = cfg.get("recent", [])

    # Show recent files first
    if recent:
        path = ui.show_recent(recent)
        if path and Path(path).exists():
            return path

    # Manual input
    raw = ui.prompt(ui.t("input_path"), "╰─>")
    path = clean_path(raw)

    if not path:
        return None

    if not Path(path).exists():
        ui.show_error(
            f"Unable to locate file",
            path,
            [
                "Check spelling and file extension",
                "Drag the file directly into this terminal",
                "Verify the drive letter and folder name",
                "Check file permissions",
            ]
        )
        time.sleep(2)
        return None

    return path


# ── Export flow ───────────────────────────────────────────────────────────────

def run_export(ui: UI, cfg: dict, video_path: str) -> None:
    from exporter import Exporter

    t = ui.theme
    clear_console()

    # Output directory
    raw_dir = ui.prompt("Output folder (blank = same as video)", "»")
    out_dir = clean_path(raw_dir) if raw_dir.strip() else str(Path(video_path).parent)

    # Keep frames?
    keep_raw = ui.prompt("Keep raw PNG frames? (y/N)", "»")
    keep = ui.is_yes(keep_raw)

    bg   = tuple(cfg.get("bg_color", [0, 0, 0]))
    exp  = Exporter(
        video_path  = video_path,
        output_dir  = out_dir,
        use_color   = cfg.get("color",     True),
        width       = cfg.get("width",     100) or 100,
        bg_color    = bg,
        font_size   = cfg.get("font_size", 12),
        export_fmt  = cfg.get("export",    "mp4"),
        keep_frames = keep,
        ui          = ui,
    )
    exp.run()
    input(f"\n  {t.muted}Press Enter to continue…{RESET}")


# ── Benchmark ─────────────────────────────────────────────────────────────────

def run_benchmark(ui: UI) -> None:
    from engine import run_benchmark as _bench
    t = ui.theme
    clear_console()
    print(f"\n  {t.primary}Running benchmark…{RESET}  (60 synthetic frames at width 120)\n")
    ui.animate_loading("Benchmarking", duration=0.5)
    results = _bench(width=120, frames=60)
    ui.show_benchmark(results)
    input(f"\n  {t.muted}Press Enter to continue…{RESET}")


# ── First-run wizard ──────────────────────────────────────────────────────────

def _first_run_wizard(ui: UI, cfg: dict) -> dict:
    """
    3-question setup shown only on the very first launch.
    Writes ascii_studio.json so it never shows again.
    """
    from theme import available_themes
    clear_console()
    t = ui.theme
    print(t.box_top(54, " FIRST RUN SETUP "))
    print(f"  {t.primary}{t.side}{RESET}  {t.muted}Welcome to ASCII Studio 2.0{RESET}")
    print(f"  {t.primary}{t.side}{RESET}  {t.muted}Answer 3 quick questions to get started.{RESET}")
    print(t.box_bottom(54))
    print()

    # Q1 – Language
    cfg["language"] = ui.select_language()
    ui._T = ui._T   # already updated by select_language

    # Q2 – Theme
    clear_console()
    themes = available_themes()
    print(f"\n  {BOLD}{t.primary}Choose a theme:{RESET}\n")
    for i, name in enumerate(themes, 1):
        print(f"  [{t.secondary}{i}{RESET}] {t.accent}{name.capitalize()}{RESET}")
    choice = input(f"\n  {t.primary}Select (default: 1 Gold): {RESET}").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(themes):
        cfg["theme"] = themes[int(choice) - 1]
    else:
        cfg["theme"] = "gold"
    t.reload(cfg["theme"])

    # Q3 – Color mode default
    clear_console()
    print(f"\n  {BOLD}{t.primary}Enable TrueColor by default?{RESET}")
    print(f"  {t.muted}Produces richer output but uses more CPU.{RESET}\n")
    c = input(f"  {t.primary}TrueColor? (Y/n): {RESET}").strip().lower()
    cfg["color"] = c not in ("n", "no")

    clear_console()
    print(f"\n  {t.success}✓ Setup complete!  Settings saved to ascii_studio.json{RESET}\n")
    time.sleep(1.2)
    return cfg


# ── Application entry ─────────────────────────────────────────────────────────

def main() -> None:
    setup_windows_terminal()

    # ── Boot sequence ─────────────────────────────────────────────────────────
    cfg      = cfg_mod.load()
    theme    = Theme(cfg.get("theme", "gold"))
    sys_info = detect_system()
    ui       = UI(theme, cfg.get("language", "en"))

    # Load plugins early so dashboard can report them
    plugin_loader.load_all()

    # ── Tip of the Day (original boot sequence) ───────────────────────────────
    clear_console()
    print(f" {theme.warning}Tip of the Day:{RESET} {theme.accent}{random.choice(TIPS)}{RESET}\n")
    time.sleep(1.5)
    ui.animate_loading("Checking terminal matrix parameters")

    # Startup dashboard
    ui.show_dashboard(sys_info)
    ui.show_system_check(sys_info)
    if plugin_loader._loaded or plugin_loader._errors:
        t = ui.theme
        print(f"\n  {t.primary}Plugins{RESET}")
        for name in plugin_loader._loaded:
            print(f"  {t.success}✓{RESET}  {t.accent}{name}{RESET}")
        for err in plugin_loader._errors:
            print(f"  {t.error}✗{RESET}  {t.muted}{err}{RESET}")
        print()

    time.sleep(0.6)

    # First-run wizard — fires exactly once when no config file exists yet.
    # Must happen BEFORE load() would create the file, so we check the path
    # directly on disk (load() doesn't write the file, only save() does).
    _is_first_run = not cfg_mod.CONFIG_PATH.exists()
    if _is_first_run:
        cfg = _first_run_wizard(ui, cfg)
        cfg_mod.save(cfg)
    elif not cfg.get("language"):
        cfg["language"] = ui.select_language()
        cfg_mod.save(cfg)

    show_logo(ui)
    time.sleep(1.0)

    # ── Main loop ─────────────────────────────────────────────────────────────
    while True:
        choice = main_menu(ui, cfg)

        if choice == "Q":
            break

        elif choice in ("P", "E"):
            video_path = ask_video_path(ui, cfg)
            if not video_path:
                continue

            # Show file info
            cap  = cv2.VideoCapture(video_path)
            meta = get_video_info(cap)
            cap.release()
            ui.show_file_info(video_path, meta)

            # Collect playback settings interactively
            color_ans = ui.prompt(ui.t("enable_color"), "»")
            use_color = ui.is_yes(color_ans)

            try:
                cols = os.get_terminal_size().columns
            except OSError:
                cols = 120
            w_raw = ui.prompt(ui.t("output_width").format(cols), "»").strip()
            width = int(w_raw) if w_raw.isdigit() else None

            s_raw = ui.prompt(ui.t("skip_n_frames"), "»").strip()
            skip  = int(s_raw) if s_raw.isdigit() else 1

            loop_ans = ui.prompt(ui.t("repeat_video"), "»")
            loop     = ui.is_yes(loop_ans)

            # Update cfg temporarily
            cfg["color"] = use_color
            cfg["width"] = width
            cfg["skip"]  = skip
            cfg["loop"]  = loop

            cfg_mod.add_recent(cfg, video_path)

            if choice == "P":
                # Footer + loading animation before playback — exact original feel
                ui.show_footer()
                ui.animate_loading("Initializing high-speed multi-threaded parsing channels")

                from renderer import Renderer
                r = Renderer(
                    video_path = video_path,
                    use_color  = use_color,
                    width      = width,
                    skip       = skip,
                    loop       = loop,
                    fps_limit  = cfg.get("fps_limit", 0),
                    sound      = cfg.get("sound", True),
                    ui         = ui,
                )
                try:
                    stats = r.play()
                except KeyboardInterrupt:
                    stats = {"frames": 0, "fps_avg": 0.0, "elapsed_s": 0.0}

                ui.show_finish(
                    frames    = stats["frames"],
                    fps       = stats["fps_avg"],
                    elapsed_s = stats["elapsed_s"],
                )
                exp_ans = ui.prompt(ui.t("export_q"), "»")
                if ui.is_yes(exp_ans):
                    run_export(ui, cfg, video_path)

            else:  # "E"
                run_export(ui, cfg, video_path)

        elif choice == "S":
            cfg = ui.settings_menu(cfg)
            theme.reload(cfg.get("theme", "gold"))
            cfg_mod.save(cfg)

        elif choice == "T":
            cfg = ui._settings_theme(cfg)
            theme.reload(cfg.get("theme", "gold"))
            cfg_mod.save(cfg)

        elif choice == "R":
            path = ui.show_recent(cfg.get("recent", []))
            if path:
                cfg["_queued_path"] = path

        elif choice == "L":
            cfg = ui.profiles_menu(cfg)
            cfg_mod.save(cfg)

        elif choice == "B":
            run_benchmark(ui)

        elif choice == "H":
            clear_console()
            ui.show_help()
            input(f"\n  {ui.theme.muted}Press Enter to continue…{RESET}")

    # ── Goodbye (exact original art) ─────────────────────────────────────────
    clear_console()
    t = theme
    print(f"{t.primary}{GOODBYE_ART}{RESET}")
    print(f"{t.accent}Thank you for scaling with Developer Susant ASCII Pipeline.{RESET}")
    print(f"{t.secondary}CODE • BUILD • SOLVE • REPEAT{RESET}\n")


def _parse_args():
    """
    Optional CLI flags for headless / scripted use.

    Examples
    --------
    # Interactive (default)
    python main.py

    # Headless export — no prompts
    python main.py video.mp4 --export gif --width 80 --no-color --out ./output

    # Headless play only
    python main.py video.mp4 --play --width 120
    """
    p = argparse.ArgumentParser(
        prog="ascii-studio",
        description="ASCII Studio 2.0 – terminal ASCII video player & exporter",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument("video",        nargs="?",  help="path to video file (optional – uses interactive menu if omitted)")
    p.add_argument("--play",       action="store_true", help="play video in terminal (headless)")
    p.add_argument("--export",     metavar="FMT",
                   choices=["mp4","gif","webm","png_seq","txt","html","ansi"],
                   help="export format")
    p.add_argument("--out",        metavar="DIR",  default="",    help="output directory for export")
    p.add_argument("--width",      metavar="N",    type=int,      help="output character width")
    p.add_argument("--skip",       metavar="N",    type=int,      default=1, help="skip every N frames")
    p.add_argument("--no-color",   action="store_true", help="disable TrueColor mode")
    p.add_argument("--fps-limit",  metavar="N",    type=int,      default=0, help="cap playback FPS (0=unlimited)")
    p.add_argument("--theme",      metavar="NAME", default="",    help="theme name (gold, matrix, …)")
    p.add_argument("--no-sound",   action="store_true", help="disable audio during playback")
    p.add_argument("--benchmark",  action="store_true", help="run benchmark and exit")
    return p.parse_args()


def _run_headless(args) -> None:
    """Execute non-interactive CLI mode."""
    setup_windows_terminal()
    cfg      = cfg_mod.load()
    if args.theme:
        cfg["theme"] = args.theme
    theme    = Theme(cfg.get("theme", "gold"))
    sys_info = detect_system()
    ui       = UI(theme, cfg.get("language", "en"))
    plugin_loader.load_all()

    if args.benchmark:
        run_benchmark(ui)
        return

    video_path = clean_path(args.video or "")
    if not video_path or not Path(video_path).exists():
        ui.show_error("File not found", video_path, ["Provide a valid path as first argument"])
        sys.exit(1)

    use_color  = not args.no_color
    width      = args.width
    skip       = args.skip
    fps_limit  = args.fps_limit
    sound      = not args.no_sound

    cfg_mod.add_recent(cfg, video_path)

    if args.play or not args.export:
        from renderer import Renderer
        r = Renderer(
            video_path=video_path, use_color=use_color,
            width=width, skip=skip, loop=False,
            fps_limit=fps_limit, sound=sound, ui=ui,
        )
        try:
            stats = r.play()
        except KeyboardInterrupt:
            stats = {"frames": 0, "fps_avg": 0.0, "elapsed_s": 0.0}
        ui.show_finish(stats["frames"], stats["fps_avg"], stats["elapsed_s"])

    if args.export:
        from exporter import Exporter
        out_dir = clean_path(args.out) if args.out else str(Path(video_path).parent)
        exp = Exporter(
            video_path=video_path, output_dir=out_dir,
            use_color=use_color, width=width or 100,
            bg_color=tuple(cfg.get("bg_color", [0, 0, 0])),
            font_size=cfg.get("font_size", 12),
            export_fmt=args.export, keep_frames=False, ui=ui,
        )
        exp.run()


if __name__ == "__main__":
    args = _parse_args()
    # Headless mode: any flag or positional video arg triggers it
    if args.video or args.benchmark:
        try:
            _run_headless(args)
        except KeyboardInterrupt:
            sys.stdout.write("\n")
            sys.exit(0)
    else:
        try:
            main()
        except KeyboardInterrupt:
            sys.stdout.write("\n")
            sys.exit(0)
