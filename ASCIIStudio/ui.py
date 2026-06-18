"""
ui.py  –  ASCII Studio 2.0
All terminal UI: startup dashboard, system detection, menus, progress bars,
settings menu, themes picker, error display, finish screen.
"""

import os
import sys
import time
import threading
import importlib.metadata
from pathlib import Path

from theme import Theme, RESET, BOLD, DIM, HIDE_CURSOR, SHOW_CURSOR, rgb, hyperlink
from utils  import terminal_size, detect_system, fmt_seconds, fmt_size, clear_console


# ── Translations — all 6 languages, all keys from original ───────────────────
TRANSLATIONS: dict[str, dict] = {
    "base": {  # Bahasa Indonesia
        "input_path":    "Seret atau masukkan path video",
        "enable_color":  "Aktifkan warna karakter? (y/N)",
        "output_width":  "Lebar output (kosong = auto, terminal={})",
        "skip_n_frames": "Skip setiap N frame (default 1)",
        "repeat_video":  "Putar dalam loop preview? (y/N)",
        "export_q":      "Ekspor video ini? (y/N)",
        "try_again_q":   "Proses video lain? (y/N)",
        "yes_keys":      "yY",
    },
    "es": {
        "input_path":    "Arrastra o escribe la ruta del video",
        "enable_color":  "¿Modo TrueColor? (s/N)",
        "output_width":  "Ancho de salida (vacío = auto, terminal={})",
        "skip_n_frames": "Saltar cada N cuadros (default 1)",
        "repeat_video":  "¿Vista previa en loop? (s/N)",
        "export_q":      "¿Exportar a video? (s/N)",
        "try_again_q":   "¿Procesar otro video? (s/N)",
        "yes_keys":      "sySY",
    },
    "en": {
        "input_path":    "Drop or enter video path",
        "enable_color":  "TrueColor mode? (y/N)",
        "output_width":  "Output width (blank = auto, terminal={})",
        "skip_n_frames": "Skip every N frames (default 1)",
        "repeat_video":  "Loop preview? (y/N)",
        "export_q":      "Export to video? (y/N)",
        "try_again_q":   "Process another video? (y/N)",
        "yes_keys":      "yY",
    },
    "fr": {
        "input_path":    "Glissez ou entrez le chemin de la vidéo",
        "enable_color":  "Mode TrueColor? (o/N)",
        "output_width":  "Largeur (vide = auto, terminal={})",
        "skip_n_frames": "Sauter chaque N images (défaut 1)",
        "repeat_video":  "Aperçu en boucle? (o/N)",
        "export_q":      "Exporter en vidéo? (o/N)",
        "try_again_q":   "Traiter une autre vidéo? (o/N)",
        "yes_keys":      "oOyY",
    },
    "pt": {
        "input_path":    "Arraste ou insira o caminho do vídeo",
        "enable_color":  "Modo TrueColor? (s/N)",
        "output_width":  "Largura (vazio = auto, terminal={})",
        "skip_n_frames": "Pular a cada N frames (padrão 1)",
        "repeat_video":  "Loop de preview? (s/N)",
        "export_q":      "Exportar para vídeo? (s/N)",
        "try_again_q":   "Processar outro vídeo? (s/N)",
        "yes_keys":      "sySY",
    },
    "de": {
        "input_path":    "Video-Pfad eingeben oder ziehen",
        "enable_color":  "TrueColor-Modus? (j/N)",
        "output_width":  "Ausgabebreite (leer = auto, Terminal={})",
        "skip_n_frames": "Jeden N-ten Frame überspringen (Standard 1)",
        "repeat_video":  "Vorschau in Schleife? (j/N)",
        "export_q":      "Als Video exportieren? (j/N)",
        "try_again_q":   "Ein weiteres Video verarbeiten? (j/N)",
        "yes_keys":      "jJyY",
    },
}


# ── UI Class ──────────────────────────────────────────────────────────────────

class UI:
    def __init__(self, theme: Theme, lang: str = "en"):
        self.theme = theme
        self.lang  = lang
        self._T    = TRANSLATIONS.get(lang, TRANSLATIONS["en"])

    def t(self, key: str) -> str:
        return self._T.get(key, key)

    def is_yes(self, answer: str) -> bool:
        return answer.strip() in list(self.t("yes_keys"))

    def prompt(self, label: str, icon: str = "»") -> str:
        t = self.theme
        sys.stdout.write(f"  {t.primary}{icon}{RESET} {label}: ")
        sys.stdout.flush()
        return input()

    # ── Startup dashboard ─────────────────────────────────────────────────────
    def show_dashboard(self, sys_info: dict) -> None:
        clear_console()
        t = self.theme
        cols, _ = terminal_size()
        W = min(cols - 2, 55)

        cv_ver  = sys_info.get("opencv",  "?")
        pil_ver = sys_info.get("pillow",  "?")
        py_ver  = sys_info.get("python",  "?")
        threads = sys_info.get("cpu_count", 1)
        ram     = sys_info.get("ram_used_mb", 0)

        print(t.box_top(W, " ASCII STUDIO 2.0 "))
        _row = lambda k, v: print(
            f"  {t.primary}{t.side}{RESET}  "
            f"{t.secondary}{k:<20}{RESET}"
            f"{t.accent}{v}{RESET}"
        )
        print(f"  {t.primary}{t.side}{RESET}")
        _row("Build",   "Stable")
        _row("Engine",  "AVX Renderer")
        _row("Python",  py_ver)
        _row("OpenCV",  cv_ver if cv_ver != "Not installed" else "⚠ Not found")
        _row("Pillow",  pil_ver if pil_ver != "Not installed" else "⚠ Not found")
        _row("Threads", str(threads))
        _row("Memory",  f"{ram} MB" if ram else "N/A")
        print(f"  {t.primary}{t.side}{RESET}")
        print(t.box_bottom(W))
        print()

        # Loading bar animation
        print(f"  {t.muted}Loading...{RESET}")
        sys.stdout.write(HIDE_CURSOR)
        for i in range(1, 41):
            frac = i / 40
            bar  = t.progress_bar(frac, 38)
            pct  = int(frac * 100)
            sys.stdout.write(f"\r  {bar}  {t.accent}{pct:>3}%{RESET}")
            sys.stdout.flush()
            time.sleep(0.025)
        sys.stdout.write(SHOW_CURSOR + "\n\n")

    # ── System detection ──────────────────────────────────────────────────────
    def show_system_check(self, sys_info: dict) -> None:
        t = self.theme
        checks = [
            ("Unicode Support",       sys_info.get("unicode",    False)),
            ("ANSI Colors",           sys_info.get("ansi_colors", False)),
            ("TrueColor (24-bit)",    sys_info.get("true_color",  False)),
            (sys_info.get("terminal", "Terminal"), True),
            ("OpenCV",                sys_info.get("opencv", "") not in ("Not installed", "")),
            ("Pillow",                sys_info.get("pillow", "") not in ("Not installed", "")),
            ("Sound (pygame)",        sys_info.get("pygame") is not None),
        ]
        print(f"  {BOLD}{t.primary}System Check{RESET}")
        for label, ok in checks:
            icon  = f"{t.success}✓{RESET}" if ok else f"{t.muted}✗{RESET}"
            color = t.accent if ok else t.muted
            print(f"  {icon}  {color}{label}{RESET}")
        print()

    # ── Language selector — exact original layout ─────────────────────────────
    def select_language(self) -> str:
        clear_console()
        t = self.theme
        # Original order: Base(Bahasa)=1, Español=2, English=3, Français=4, Português=5, Deutsch=6
        langs = [
            ("1", "① Base (Bahasa)",  "base"),
            ("2", "② Español",        "es"),
            ("3", "③ English",        "en"),
            ("4", "④ Français",       "fr"),
            ("5", "⑤ Português",      "pt"),
            ("6", "⑥ Deutsch",        "de"),
        ]
        print(t.box_top(64, " SELECT LANGUAGE / SELECCIONA TU IDIOMA "))
        for key, label, _ in langs:
            print(f"  {t.primary}{t.side}{RESET}  [{t.secondary}{key}{RESET}] {t.accent}{label:<28}{RESET}  {t.primary}{t.side}{RESET}")
        print(t.box_bottom(64))
        choice = input(f"\n  {t.primary}Select Option (1-6): {RESET}").strip()
        for key, _, code in langs:
            if choice == key:
                self.lang = code
                self._T   = TRANSLATIONS.get(code, TRANSLATIONS["es"])
                return code
        # Default: Español (matches original default)
        self.lang = "es"
        self._T   = TRANSLATIONS["es"]
        return "es"

    # ── Settings menu ─────────────────────────────────────────────────────────
    def settings_menu(self, cfg: dict) -> dict:
        """
        Interactive settings menu.  Returns (possibly modified) cfg.
        Sections: Video, Rendering, Export, Colors, Performance, Language.
        """
        t = self.theme
        while True:
            clear_console()
            print(t.box_top(54, " SETTINGS "))
            sections = [
                ("1", "Video",       "width, skip, loop"),
                ("2", "Rendering",   "color, font_size"),
                ("3", "Export",      "format, bg_color"),
                ("4", "Themes",      "choose visual theme"),
                ("5", "Performance", "fps_limit, threads"),
                ("6", "Language",    "change UI language"),
                ("0", "Back",        "return to main menu"),
            ]
            for key, name, desc in sections:
                print(
                    f"  {t.primary}{t.side}{RESET}  "
                    f"[{t.secondary}{key}{RESET}] {t.accent}{name:<14}{RESET}"
                    f"{t.muted}{desc}{RESET}"
                )
            print(t.box_bottom(54))
            choice = input(f"\n  {t.primary}Select section: {RESET}").strip()

            if choice == "0":
                break
            elif choice == "1":
                cfg = self._settings_video(cfg)
            elif choice == "2":
                cfg = self._settings_rendering(cfg)
            elif choice == "3":
                cfg = self._settings_export(cfg)
            elif choice == "4":
                cfg = self._settings_theme(cfg)
            elif choice == "5":
                cfg = self._settings_perf(cfg)
            elif choice == "6":
                cfg["language"] = self.select_language()
        return cfg

    def _settings_video(self, cfg: dict) -> dict:
        t = self.theme
        clear_console()
        print(f"\n  {BOLD}{t.primary}── Video Settings ──{RESET}\n")
        w = input(f"  Width (current: {cfg.get('width','auto')}, blank=keep): ").strip()
        if w:
            cfg["width"] = int(w) if w.isdigit() else None
        s = input(f"  Skip frames (current: {cfg.get('skip',1)}, blank=keep): ").strip()
        if s and s.isdigit():
            cfg["skip"] = int(s)
        l = input(f"  Loop preview? current={'yes' if cfg.get('loop') else 'no'} (y/n, blank=keep): ").strip().lower()
        if l in ("y", "n"):
            cfg["loop"] = l == "y"
        return cfg

    def _settings_rendering(self, cfg: dict) -> dict:
        t = self.theme
        clear_console()
        print(f"\n  {BOLD}{t.primary}── Rendering Settings ──{RESET}\n")
        c = input(f"  TrueColor? current={'yes' if cfg.get('color') else 'no'} (y/n, blank=keep): ").strip().lower()
        if c in ("y", "n"):
            cfg["color"] = c == "y"
        f = input(f"  Font size (current: {cfg.get('font_size',12)}, blank=keep): ").strip()
        if f and f.isdigit():
            cfg["font_size"] = int(f)
        return cfg

    def _settings_export(self, cfg: dict) -> dict:
        t = self.theme
        clear_console()
        print(f"\n  {BOLD}{t.primary}── Export Settings ──{RESET}\n")
        fmt_map = {"1":"mp4","2":"gif","3":"webm","4":"png_seq","5":"txt","6":"html","7":"ansi"}
        print("  [1] MP4  [2] GIF  [3] WebM  [4] PNG Sequence  [5] TXT  [6] HTML  [7] ANSI")
        c = input(f"  Current: {cfg.get('export','mp4')}, select (blank=keep): ").strip()
        if c in fmt_map:
            cfg["export"] = fmt_map[c]
        bg_map = {"1":[0,0,0],"2":[255,255,255],"3":[0,0,180]}
        print("  Background: [1] Black  [2] White  [3] Blue  [4] Custom hex")
        b = input(f"  Current bg: {cfg.get('bg_color',[0,0,0])}, select (blank=keep): ").strip()
        if b in bg_map:
            cfg["bg_color"] = bg_map[b]
        elif b == "4":
            h = input("  Hex (#RRGGBB): ").strip().lstrip("#")
            try:
                cfg["bg_color"] = [int(h[i:i+2],16) for i in (0,2,4)]
            except Exception:
                pass
        return cfg

    def _settings_theme(self, cfg: dict) -> dict:
        from theme import available_themes
        t = self.theme
        clear_console()
        themes = available_themes()
        print(f"\n  {BOLD}{t.primary}── Themes ──{RESET}\n")
        for i, name in enumerate(themes, 1):
            marker = "▶" if name == cfg.get("theme") else " "
            print(f"  {t.secondary}{marker} [{i}]{RESET} {t.accent}{name.capitalize()}{RESET}")
        c = input(f"\n  Select theme (blank=keep): ").strip()
        if c.isdigit():
            idx = int(c) - 1
            if 0 <= idx < len(themes):
                cfg["theme"] = themes[idx]
                t.reload(themes[idx])
        return cfg

    def _settings_perf(self, cfg: dict) -> dict:
        t = self.theme
        clear_console()
        print(f"\n  {BOLD}{t.primary}── Performance Settings ──{RESET}\n")
        f = input(f"  FPS limit (0=unlimited, current: {cfg.get('fps_limit',0)}, blank=keep): ").strip()
        if f.isdigit():
            cfg["fps_limit"] = int(f)
        s = input(f"  Sound enabled? current={'yes' if cfg.get('sound',True) else 'no'} (y/n, blank=keep): ").strip().lower()
        if s in ("y","n"):
            cfg["sound"] = s == "y"
        return cfg

    # ── Profiles menu ─────────────────────────────────────────────────────────
    def profiles_menu(self, cfg: dict) -> dict:
        import config as cfg_mod
        t = self.theme
        clear_console()
        profiles = cfg_mod.load_profiles()
        print(t.box_top(50, " PROFILES "))
        for i, name in enumerate(profiles, 1):
            print(f"  {t.primary}{t.side}{RESET}  [{t.secondary}{i}{RESET}] {t.accent}{name}{RESET}")
        print(f"  {t.primary}{t.side}{RESET}  [{t.secondary}S{RESET}] {t.muted}Save current as new profile{RESET}")
        print(t.box_bottom(50))
        choice = input(f"\n  {t.primary}Select: {RESET}").strip()
        names  = list(profiles.keys())
        if choice.isdigit() and 1 <= int(choice) <= len(names):
            cfg = cfg_mod.apply_profile(cfg, names[int(choice)-1])
            print(f"  {t.success}✓ Profile '{names[int(choice)-1]}' applied.{RESET}")
            time.sleep(1)
        elif choice.lower() == "s":
            name = input("  Profile name: ").strip()
            if name:
                keys = ["color","width","skip","fps_limit","font_size","export"]
                cfg_mod.save_profile(name, {k: cfg[k] for k in keys if k in cfg})
                print(f"  {t.success}✓ Saved profile '{name}'.{RESET}")
                time.sleep(1)
        return cfg

    # ── Recent files ──────────────────────────────────────────────────────────
    def show_recent(self, recent: list[str]) -> str | None:
        """Display recent files and return selected path or None."""
        if not recent:
            return None
        t = self.theme
        print(f"\n  {BOLD}{t.primary}Recent Files{RESET}")
        for i, p in enumerate(recent[:10], 1):
            print(f"  {t.secondary}[{i}]{RESET} {t.muted}{Path(p).name}{RESET}")
        choice = input(f"  {t.primary}Select recent (blank=skip): {RESET}").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(recent):
                return recent[idx]
        return None

    # ── File info card ────────────────────────────────────────────────────────
    def show_file_info(self, path: str, meta: dict) -> None:
        t  = self.theme
        W  = 58
        name = Path(path).name
        print()
        print(t.box_top(W, " VIDEO INFO "))
        rows = [
            ("File",       name[:40]),
            ("Resolution", f"{meta['width_px']} × {meta['height_px']}"),
            ("Frame Rate", f"{meta['fps']:.2f} FPS"),
            ("Duration",   f"{meta['duration_s']:.1f}s  ({fmt_seconds(meta['duration_s'])})"),
            ("Frames",     str(meta['total_frames'])),
        ]
        size_b = 0
        try:
            size_b = Path(path).stat().st_size
        except OSError:
            pass
        if size_b:
            rows.append(("File Size", fmt_size(size_b)))
        for k, v in rows:
            line = f"  {t.secondary}{k:<14}{RESET}{t.accent}{v}{RESET}"
            print(f"  {t.primary}{t.side}{RESET}{line}")
        print(t.box_bottom(W))
        print()

    # ── Error display ─────────────────────────────────────────────────────────
    def show_error(self, message: str, path: str = "", suggestions: list[str] | None = None) -> None:
        t = self.theme
        print(f"\n  {t.error}✖  {message}{RESET}")
        if path:
            print(f"     {t.muted}{path}{RESET}")
        if suggestions:
            print(f"\n  {t.warning}Suggestions:{RESET}")
            for s in suggestions:
                print(f"    {t.muted}• {s}{RESET}")
        print()

    # ── Export progress screen ────────────────────────────────────────────────
    def export_progress(self, frame: int, total: int, eta_s: float, fmt: str) -> None:
        t     = self.theme
        cols, _ = terminal_size()
        frac  = frame / max(1, total)
        bar   = t.progress_bar(frac, 36)
        pct   = int(frac * 100)
        eta   = fmt_seconds(eta_s)
        sys.stdout.write(
            f"\r  {t.primary}EXPORTING{RESET}  {bar}  "
            f"{t.accent}{pct:>3}%{RESET}  "
            f"{t.secondary}Frame {frame}/{total}{RESET}  "
            f"{t.muted}ETA {eta}  Writing {fmt.upper()}{RESET}  "
        )
        sys.stdout.flush()

    # ── Live perf HUD (single line) ───────────────────────────────────────────
    def perf_hud(self, stats: dict, cols: int, line: int) -> None:
        t = self.theme

        def _fmt(val, suffix: str = "", width: int = 6) -> str:
            """Format a stat value; show N/A if None (psutil not installed)."""
            if val is None:
                return f"{'N/A':<{width}}"
            return f"{val}{suffix}"

        fps   = stats.get("fps",     0)
        cpu   = stats.get("cpu",     None)
        ram   = stats.get("ram_mb",  None)
        frame = stats.get("frame",   0)
        total = stats.get("total",   0)
        drop  = stats.get("dropped", 0)
        ms    = stats.get("frame_ms",0)
        hud   = (
            f"{t.success}FPS {_fmt(fps, '', 6)}{RESET}"
            f"{t.secondary}CPU {_fmt(cpu, '%', 5)}  {RESET}"
            f"{t.primary}RAM {_fmt(ram, 'MB', 6)}  {RESET}"
            f"{t.accent}Frame {frame}/{total}  {RESET}"
            f"{t.muted}Drop {drop}  {ms}ms{RESET}"
        )
        sys.stdout.write(f"\033[{line};1H\033[2K{hud}")
        sys.stdout.flush()

    # ── Finish screen ─────────────────────────────────────────────────────────
    def show_finish(self, frames: int, fps: float, elapsed_s: float, export_path: str = "") -> None:
        clear_console()
        t = self.theme
        W = 50
        export_size = ""
        if export_path and Path(export_path).exists():
            export_size = fmt_size(Path(export_path).stat().st_size)
        print(t.box_top(W, " MISSION COMPLETE "))
        rows = [
            ("Frames",      f"{frames:,}"),
            ("Average FPS", f"{fps:.2f}"),
            ("Elapsed",     fmt_seconds(elapsed_s)),
        ]
        if export_size:
            rows.append(("Export Size", export_size))
        for k, v in rows:
            pad = W - 4 - len(k) - len(v)
            print(
                f"  {t.primary}{t.side}{RESET}  "
                f"{t.secondary}{k}{RESET}"
                f"{' ' * max(1,pad)}"
                f"{t.accent}{v}{RESET}"
            )
        print(f"  {t.primary}{t.side}{RESET}")
        print(f"  {t.primary}{t.side}{RESET}   {BOLD}{t.primary}Thanks for using ASCII STUDIO{RESET}")
        print(f"  {t.primary}{t.side}{RESET}   {t.muted}by Developer Susant{RESET}")
        print(f"  {t.primary}{t.side}{RESET}")
        links = [
            ("GitHub",  "https://github.com/susantedit"),
            ("YouTube", "https://youtube.com/@developersusant"),
        ]
        for label, url in links:
            print(f"  {t.primary}{t.side}{RESET}   {t.muted}{hyperlink(url, label)}{RESET}")
        print(f"  {t.primary}{t.side}{RESET}")
        print(t.box_bottom(W))

    # ── Benchmark results ─────────────────────────────────────────────────────
    def show_benchmark(self, results: dict) -> None:
        t = self.theme
        W = 50
        clear_console()
        print(t.box_top(W, " ASCII BENCHMARK RESULTS "))
        rows = [
            ("Color FPS",       f"{results['color_fps']}"),
            ("Plain FPS",       f"{results['plain_fps']}"),
            ("Color ms/frame",  f"{results['color_ms']} ms"),
            ("Plain ms/frame",  f"{results['plain_ms']} ms"),
            ("Frames Tested",   str(results['frames_tested'])),
            ("Active Threads",  str(results['threads'])),
        ]
        for k, v in rows:
            print(f"  {t.primary}{t.side}{RESET}  {t.secondary}{k:<20}{RESET}{t.accent}{v}{RESET}")
        print(t.box_bottom(W))

    # ── Footer (shown before playback) ───────────────────────────────────────
    def show_footer(self) -> None:
        t = self.theme
        print(f"\n{t.muted}──────────────────────────────────────────────────────────────────────────{RESET}")
        print(f"{t.muted}Developer Susant ASCII Video Engine | Technical Content Studio Portfolio{RESET}")
        print(f"{t.muted}──────────────────────────────────────────────────────────────────────────{RESET}\n")

    # ── Animated spinner ──────────────────────────────────────────────────────
    def animate_loading(self, label: str, duration: float = 1.2) -> None:
        frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
        t      = self.theme
        end    = time.time() + duration
        i      = 0
        sys.stdout.write(HIDE_CURSOR)
        while time.time() < end:
            sys.stdout.write(f"\r  {t.primary}{frames[i % len(frames)]}{RESET} {label}...")
            sys.stdout.flush()
            time.sleep(0.08)
            i += 1
        sys.stdout.write("\r" + " " * 60 + "\r")
        sys.stdout.write(SHOW_CURSOR)

    # ── Interactive help overlay ──────────────────────────────────────────────
    def show_help(self) -> None:
        t = self.theme
        W = 50
        print(t.box_top(W, " CONTROLS "))
        controls = [
            ("Space",  "Pause / Resume"),
            ("R",      "Replay from start"),
            ("S",      "Screenshot (PNG)"),
            ("E",      "Export current video"),
            ("H",      "Toggle this help"),
            ("Q / Ctrl+C", "Quit"),
        ]
        for key, desc in controls:
            print(
                f"  {t.primary}{t.side}{RESET}  "
                f"[{t.secondary}{key:<10}{RESET}] "
                f"{t.accent}{desc}{RESET}"
            )
        print(t.box_bottom(W))
