"""
ASCII Player Video Creator - V5 Official
====================================================
Versión completa con flujo interactivo mejorado.
Basado en el trabajo de @stepanussaruran.

Características:
  - Flujo interactivo: Logo -> Idioma -> Config -> Play -> Export -> Restart
  - Soporte Multi-idioma (ES, EN, FR, PT, DE, Base)
  - Exportación a MP4 con gestión de frames (Conservar o Borrar)
  - Renderizado de alta densidad con paleta extendida
  - Ajuste proporcional automático o manual

Créditos Originales: stepanussaruran
Modificaciones y Flujo: Nicolas Romero (coralgamer)
Licencia: MIT (Open Source)
=====================================================
CHANGELOG:
- Rediseño completo del flujo de usuario.
- Añadido logo de inicio "ASCII Player Video Creator".
- Gestión inteligente de archivos temporales en la exportación.
- Ciclo de reinicio para procesar múltiples videos sin cerrar la app.
- Traducciones actualizadas para el nuevo flujo.
=====================================================
"""

import argparse
import cv2
import os
import sys
import time
import threading
import shutil
import numpy as np
from queue import Queue, Empty
from PIL import Image, ImageDraw, ImageFont

# ── Traducciones / Translations ──────────────────────────────────────────────

TRANSLATIONS = {
    "base": {
        "app_name": "ASCII Player Video Creator",
        "input_path": "Masukkan path video: ",
        "enable_color": "Aktifkan warna karakter? (y/N): ",
        "output_width": "Lebar output (kosongkan untuk Auto, terminal={}): ",
        "skip_n_frames": "Skip setiap N frame (default 1): ",
        "repeat_video": "Putar dalam loop preview? (y/N): ",
        "playback_finished": "Selesai menampilkan video.",
        "export_q": "Apakah Anda ingin mengekspor video ini ke MP4? (y/N): ",
        "export_folder": "Tempelkan path folder untuk proses (temp): ",
        "export_mode_q": "Simpan apa? (1. Hanya MP4 | 2. MP4 + Semua Frame PNG): ",
        "export_bg": "Warna latar belakang (1. Hitam | 2. Putih | 3. Biru | 4. Custom Hex): ",
        "export_start": "Mengekspor... Harap tunggu.",
        "export_done": "Video siap! Lokasi: ",
        "cleaning_temp": "Menghapus folder frame sementara...",
        "try_again_q": "Ingin memproses video lain? (y/N): ",
        "stopped_user": "Berhenti.",
        "error_not_found": "File tidak ditemukan: '{}'",
        "error_open": "Gagal membuka video.",
        "processing_frame": "Frame {}/{}...",
        "yes": "Ya", "no": "Tidak"
    },
    "es": {
        "app_name": "ASCII Player Video Creator",
        "input_path": "Introduce la ruta del video: ",
        "enable_color": "¿Caracteres a color? (s/N): ",
        "output_width": "Ancho de salida (vacío para Auto, terminal={}): ",
        "skip_n_frames": "Saltar cada N cuadros (default 1): ",
        "repeat_video": "¿Previsualizar en loop? (s/N): ",
        "playback_finished": "Visualización terminada.",
        "export_q": "¿Quieres exportarlo como MP4? (s/N): ",
        "export_folder": "Crea una carpeta temporal, copia su ruta y pégala aquí: ",
        "export_mode_q": "¿Qué quieres conservar? (1. Solo video MP4 | 2. Video + Cada Frame PNG): ",
        "export_bg": "Color de fondo (1. Negro | 2. Blanco | 3. Azul | 4. Custom Hex): ",
        "export_start": "Creando video... Por favor espera.",
        "export_done": "¡Video finalizado! Guardado en: ",
        "cleaning_temp": "Eliminando carpeta de frames temporales...",
        "try_again_q": "¿Quieres volver a intentar con un nuevo video? (s/N): ",
        "stopped_user": "Detenido.",
        "error_not_found": "Archivo no encontrado: '{}'",
        "error_open": "No se pudo abrir el video.",
        "processing_frame": "Cuadro {}/{}...",
        "yes": "Sí", "no": "No"
    },
    "en": {
        "app_name": "ASCII Player Video Creator",
        "input_path": "Enter video path: ",
        "enable_color": "Character color? (y/N): ",
        "output_width": "Output width (blank for Auto, terminal={}): ",
        "skip_n_frames": "Skip every N frames (default 1): ",
        "repeat_video": "Preview in loop? (y/N): ",
        "playback_finished": "Playback finished.",
        "export_q": "Do you want to export it as MP4? (y/N): ",
        "export_folder": "Create a temp folder, copy its path and paste it here: ",
        "export_mode_q": "What to keep? (1. Only MP4 video | 2. Video + Each PNG frame): ",
        "export_bg": "Background color (1. Black | 2. White | 3. Blue | 4. Custom Hex): ",
        "export_start": "Creating video... Please wait.",
        "export_done": "Video finished! Saved at: ",
        "cleaning_temp": "Deleting temporary frames folder...",
        "try_again_q": "Do you want to try another video? (y/N): ",
        "stopped_user": "Stopped.",
        "error_not_found": "File not found: '{}'",
        "error_open": "Could not open video.",
        "processing_frame": "Frame {}/{}...",
        "yes": "Yes", "no": "No"
    },
    "fr": {
        "app_name": "ASCII Player Video Creator",
        "input_path": "Entrez le chemin de la vidéo : ",
        "enable_color": "Couleur des caractères ? (o/N) : ",
        "output_width": "Largeur (vide pour Auto, terminal={}) : ",
        "skip_n_frames": "Sauter toutes les N images (défaut 1) : ",
        "repeat_video": "Aperçu en boucle ? (o/N) : ",
        "playback_finished": "Lecture terminée.",
        "export_q": "Voulez-vous exporter en MP4 ? (o/N) : ",
        "export_folder": "Créez un dossier temporaire, copiez son chemin et collez-le ici : ",
        "export_mode_q": "Que garder ? (1. Vidéo MP4 uniquement | 2. Vidéo + Chaque image PNG) : ",
        "export_bg": "Couleur de fond (1. Noir | 2. Blanc | 3. Bleu | 4. Hex personnalisé) : ",
        "export_start": "Création de la vidéo... Veuillez patienter.",
        "export_done": "Vidéo terminée ! Enregistrée sous : ",
        "cleaning_temp": "Suppression du dossier d'images temporaires...",
        "try_again_q": "Voulez-vous essayer une autre vidéo ? (o/N) : ",
        "stopped_user": "Arrêté.",
        "error_not_found": "Fichier non trouvé : '{}'",
        "error_open": "Impossible d'ouvrir la vidéo.",
        "processing_frame": "Image {}/{}...",
        "yes": "Oui", "no": "Non"
    },
    "pt": {
        "app_name": "ASCII Player Video Creator",
        "input_path": "Insira o caminho do vídeo: ",
        "enable_color": "Cor dos caracteres? (s/N): ",
        "output_width": "Largura (vazio para Auto, terminal={}): ",
        "skip_n_frames": "Pular a cada N quadros (padrão 1): ",
        "repeat_video": "Visualizar em loop? (s/N): ",
        "playback_finished": "Reprodução finalizada.",
        "export_q": "Deseja exportar como MP4? (s/N): ",
        "export_folder": "Crie uma pasta temporária, copie o caminho e cole aqui: ",
        "export_mode_q": "O que manter? (1. Apenas vídeo MP4 | 2. Vídeo + Cada frame PNG): ",
        "export_bg": "Cor de fundo (1. Preto | 2. Branco | 3. Azul | 4. Hex personalizado): ",
        "export_start": "Criando vídeo... Por favor, aguarde.",
        "export_done": "Vídeo finalizado! Salvo em: ",
        "cleaning_temp": "Excluindo pasta de frames temporários...",
        "try_again_q": "Deseja tentar outro vídeo? (s/N): ",
        "stopped_user": "Parado.",
        "error_not_found": "Arquivo não encontrado: '{}'",
        "error_open": "Não foi possível abrir o vídeo.",
        "processing_frame": "Frame {}/{}...",
        "yes": "Sim", "no": "Não"
    },
    "de": {
        "app_name": "ASCII Player Video Creator",
        "input_path": "Videopfad eingeben: ",
        "enable_color": "Zeichenfarbe? (j/N): ",
        "output_width": "Ausgabebreite (leer für Auto, Terminal={}): ",
        "skip_n_frames": "Jeden N. Frame überspringen (Standard 1): ",
        "repeat_video": "Vorschau in Schleife? (j/N): ",
        "playback_finished": "Wiedergabe beendet.",
        "export_q": "Möchten Sie als MP4 exportieren? (j/N): ",
        "export_folder": "Temporären Ordner erstellen, Pfad kopieren und hier einfügen: ",
        "export_mode_q": "Was behalten? (1. Nur MP4-Video | 2. Video + Jeder PNG-Frame): ",
        "export_bg": "Hintergrundfarbe (1. Schwarz | 2. Weiß | 3. Blau | 4. Custom Hex): ",
        "export_start": "Video wird erstellt... Bitte warten.",
        "export_done": "Video fertig! Gespeichert unter: ",
        "cleaning_temp": "Temporärer Frame-Ordner wird gelöscht...",
        "try_again_q": "Möchten Sie ein weiteres Video versuchen? (j/N): ",
        "stopped_user": "Gestoppt.",
        "error_not_found": "Datei nicht gefunden: '{}'",
        "error_open": "Video konnte nicht geöffnet werden.",
        "processing_frame": "Frame {}/{} wird verarbeitet...",
        "yes": "Ja", "no": "Nein"
    }
}

# Global current language
T = TRANSLATIONS["es"]

def select_language():
    global T
    clear_console()
    print(f"\n{C_BOLD}{C_CYAN}" + "═" * 60 + f"{RESET_COLOR}")
    print(f"  {C_BOLD}SELECT YOUR LANGUAGE / SELECCIONA TU IDIOMA{RESET_COLOR}")
    print(f"{C_CYAN}" + "═" * 60 + f"{RESET_COLOR}")
    print(f"\n  1. Base (Bahasa)   2. Español   3. English")
    print(f"  4. Français        5. Português 6. Deutsch")
    
    choice = input(f"\n  Choice (1-6): ").strip()
    lang_map = {"1": "base", "2": "es", "3": "en", "4": "fr", "5": "pt", "6": "de"}
    T = TRANSLATIONS.get(lang_map.get(choice), TRANSLATIONS["es"])

def show_logo():
    clear_console()
    logo = f"""
{C_CYAN}    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║   {C_BOLD}{C_GREEN} █████╗ ███████╗ ██████╗██╗██╗     ██████╗ ██╗      █████╗  {C_CYAN}║
    ║   {C_BOLD}{C_GREEN}██╔══██╗██╔════╝██╔════╝██║██║     ██╔══██╗██║     ██╔══██╗ {C_CYAN}║
    ║   {C_BOLD}{C_GREEN}███████║███████╗██║     ██║██║     ██████╔╝██║     ███████║ {C_CYAN}║
    ║   {C_BOLD}{C_GREEN}██╔══██║╚════██║██║     ██║██║     ██╔═══╝ ██║     ██╔══██║ {C_CYAN}║
    ║   {C_BOLD}{C_GREEN}██║  ██║███████║╚██████╗██║██║     ██║     ███████╗██║  ██║ {C_CYAN}║
    ║   {C_BOLD}{C_GREEN}╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝╚═╝     ╚═╝     ╚══════╝╚═╝  ╚═╝ {C_CYAN}║
    ║                                                          ║
    ║              {C_BOLD}{C_YELLOW}V I D E O    C R E A T O R{C_CYAN}                  ║
    ╚══════════════════════════════════════════════════════════╝{RESET_COLOR}
    Contributors: Stepanussaruran, Nicolas Romero (CoralGamer).
    """
    print(logo)
    time.sleep(5)

# ── Conjunto de caracteres extendido ──────────────────────────────────────────
ASCII_CHARS = " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczmwqpdbkhao*#MW&8%B@$0QSXGZJKPHDAUYTRENVLCF"
_CHARS_ARRAY = np.array(list(ASCII_CHARS))

# ── Códigos de Escape ANSI ───────────────────────────────────────────────────
CURSOR_HOME  = "\033[H"
CLEAR_SCREEN = "\033[2J"
HIDE_CURSOR  = "\033[?25l"
SHOW_CURSOR  = "\033[?25h"
RESET_COLOR  = "\033[0m"

# ── Colores ───────────────────────────────────────────────────────────────────
C_CYAN   = "\033[96m"
C_GREEN  = "\033[92m"
C_YELLOW = "\033[111111193m"
C_RED    = "\033[91m"
C_GRAY   = "\033[90m"
C_BOLD   = "\033[1m"

def clear_console():
    if os.name == "nt": os.system("cls")
    else: os.system("clear")

def enable_ansi_windows() -> None:
    if os.name == "nt":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception: pass

def get_video_info(cap: cv2.VideoCapture) -> dict:
    return {
        "fps"          : cap.get(cv2.CAP_PROP_FPS),
        "total_frames" : int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "width_px"     : int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height_px"    : int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "duration_s"   : cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(cap.get(cv2.CAP_PROP_FPS), 1),
    }

# ── Conversión y Renderizado ──────────────────────────────────────────────────

def frame_to_ascii_nocolor(frame, width: int) -> str:
    height = max(1, int(frame.shape[0] * width / frame.shape[1] / 2))
    resized = cv2.resize(frame, (width, height))
    gray    = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    n_chars = len(ASCII_CHARS) - 1
    lines = []
    for row in gray:
        line = "".join(ASCII_CHARS[int(p / 255.0 * n_chars)] for p in row)
        lines.append(line)
    return "\n".join(lines)

def frame_to_ascii_color(frame, width: int) -> tuple:
    height = max(1, int(frame.shape[0] * width / frame.shape[1] / 2))
    resized     = cv2.resize(frame, (width, height))
    resized_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    brightness   = 0.299 * resized_rgb[:,:,0] + 0.587 * resized_rgb[:,:,1] + 0.114 * resized_rgb[:,:,2]
    char_indices = np.clip((brightness / 255.0 * (len(ASCII_CHARS) - 1)).astype(np.int32), 0, len(ASCII_CHARS) - 1)
    return _CHARS_ARRAY[char_indices], resized_rgb

def ascii_to_image(char_map, rgb_map, bg_color, font_size=10):
    h, w = char_map.shape
    char_w, char_h = font_size * 0.6, font_size
    img = Image.new("RGB", (int(w * char_w), int(h * char_h)), bg_color)
    draw = ImageDraw.Draw(img)
    try: font = ImageFont.truetype("consola.ttf", font_size)
    except:
        try: font = ImageFont.truetype("cour.ttf", font_size)
        except: font = ImageFont.load_default()
    for y in range(h):
        for x in range(w):
            color = tuple(rgb_map[y, x]) if rgb_map is not None else (255, 255, 255)
            draw.text((x * char_w, y * char_h), char_map[y, x], fill=color, font=font)
    return img

# ── Flujo de Exportación ──────────────────────────────────────────────────────

def export_flow(video_path, use_color, width):
    clear_console()
    print(f"\n  {C_BOLD}{C_GREEN}» EXPORTACIÓN A MP4 «{RESET_COLOR}")
    folder = input(f"\n  {T['export_folder']}").strip().strip('"')
    if not folder: return
    
    keep_mode = input(f"\n  {T['export_mode_q']}").strip()
    bg_choice = input(f"\n  {T['export_bg']}").strip()
    
    bg_color = (0, 0, 0)
    if bg_choice == "2": bg_color = (255, 255, 255)
    elif bg_choice == "3": bg_color = (0, 0, 255)
    elif bg_choice == "4":
        hex_c = input("  Hex (#RRGGBB): ").strip().lstrip("#")
        bg_color = tuple(int(hex_c[i:i+2], 16) for i in (0, 2, 4))
    
    temp_dir = os.path.join(folder, "temp_ascii_frames")
    if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    
    cap = cv2.VideoCapture(video_path)
    info = get_video_info(cap)
    fps = info["fps"] if info["fps"] > 0 else 30.0
    # Use actual frame count from reading, not CAP_PROP_FRAME_COUNT which can be inaccurate
    total_estimated = info["total_frames"]
    
    print(f"\n  {C_YELLOW}{T['export_start']}{RESET_COLOR}")
    
    saved_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        saved_count += 1
        if use_color:
            char_map, rgb_map = frame_to_ascii_color(frame, width)
        else:
            txt = frame_to_ascii_nocolor(frame, width)
            char_map = np.array([list(l) for l in txt.split("\n")])
            rgb_map = None
        img = ascii_to_image(char_map, rgb_map, bg_color)
        img.save(os.path.join(temp_dir, f"f_{saved_count:05d}.png"))
        if saved_count % 10 == 0:
            sys.stdout.write(f"\r  {T['processing_frame'].format(saved_count, total_estimated)}")
            sys.stdout.flush()
    
    cap.release()
    output_v = os.path.join(folder, "ASCII_Player_Output.mp4")
    sample = cv2.imread(os.path.join(temp_dir, "f_00001.png"))
    out = cv2.VideoWriter(output_v, cv2.VideoWriter_fourcc(*'mp4v'), fps, (sample.shape[1], sample.shape[0]))
    for i in range(1, saved_count + 1):
        frame_img = cv2.imread(os.path.join(temp_dir, f"f_{i:05d}.png"))
        if frame_img is not None:
            out.write(frame_img)
    out.release()
    
    if keep_mode == "1":
        print(f"\n  {C_GRAY}{T['cleaning_temp']}{RESET_COLOR}")
        shutil.rmtree(temp_dir)
        
    print(f"\n{C_GREEN}{T['export_done']}{RESET_COLOR}{output_v}")

# ── Motor de Reproducción ─────────────────────────────────────────────────────

def play_engine(video_path, width, use_color, skip, loop):
    cap = cv2.VideoCapture(video_path)
    info = get_video_info(cap); fps = info["fps"] if info["fps"]>0 else 30.0
    delay = (1.0 / fps) * skip; video_ar = info["width_px"] / info["height_px"]
    
    while True:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        q = Queue(maxsize=10); stop = threading.Event()
        def _dec():
            idx = 0
            while not stop.is_set():
                ret, f = cap.read()
                if not ret: break
                if skip>1 and idx%skip!=0: idx+=1; continue
                idx+=1
                while not stop.is_set():
                    try: q.put(f, timeout=0.1); break
                    except: pass
            q.put(None)
        t = threading.Thread(target=_dec, daemon=True); t.start()
        sys.stdout.write(HIDE_CURSOR + CLEAR_SCREEN); sys.stdout.flush()
        f_cnt = 0; tot = max(1, info["total_frames"] // skip)
        try:
            while True:
                ts = time.perf_counter()
                f = q.get(timeout=2.0)
                if f is None: break
                f_cnt += 1
                try: ts_cols, ts_lines = os.get_terminal_size().columns, os.get_terminal_size().lines
                except: ts_cols, ts_lines = 80, 24
                if width is None:
                    avail_h = max(1, ts_lines - 2)
                    w_from_h = int(avail_h * video_ar * 2.0)
                    cur_w = min(ts_cols, w_from_h)
                else: cur_w = width
                
                if use_color:
                    cmap, rgb = frame_to_ascii_color(f, cur_w)
                    art = "\n".join(["".join([f"\033[38;2;{r};{g};{b}m{c}" for c, (r,g,b) in zip(row, rgb_row)]) + RESET_COLOR for row, rgb_row in zip(cmap, rgb)])
                else: art = frame_to_ascii_nocolor(f, cur_w)
                
                sys.stdout.write(CURSOR_HOME + art)
                bar_l = max(10, ts_cols - 45); filled = int(bar_l * (f_cnt/tot))
                bar = "█" * filled + "░" * (bar_l - filled)
                sys.stdout.write(f"\033[{ts_lines};1H{C_GRAY}[{bar}] {f_cnt}/{tot} | Ctrl+C {RESET_COLOR}")
                sys.stdout.flush()
                elap = time.perf_counter() - ts
                if delay - elap > 0: time.sleep(delay - elap)
        except KeyboardInterrupt: stop.set(); break
        finally: stop.set(); t.join(timeout=1.0)
        if not loop: break
    cap.release(); sys.stdout.write(SHOW_CURSOR + RESET_COLOR + f"\n\n{T['playback_finished']}\n")

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    enable_ansi_windows()
    show_logo()
    select_language()
    
    while True:
        show_logo()
        print(f"  {C_BOLD}{C_YELLOW}» {T['app_name']} «{RESET_COLOR}\n")
        vid = input(f"  {C_BOLD}{C_GREEN}»{RESET_COLOR} {T['input_path']}").strip().strip('"')
        if not vid or not os.path.exists(vid):
            print(f"  {C_RED}{T['error_not_found'].format(vid)}{RESET_COLOR}"); time.sleep(2); continue
            
        color_in = input(f"  {C_BOLD}{C_GREEN}»{RESET_COLOR} {T['enable_color']}").strip().lower()
        use_color = color_in in ["s", "y", "o", "j"]
        
        try: ts_cols = os.get_terminal_size().columns
        except: ts_cols = 80
        w_in = input(f"  {C_BOLD}{C_GREEN}»{RESET_COLOR} {T['output_width'].format(ts_cols)}").strip()
        width = int(w_in) if w_in else None
        
        s_in = input(f"  {C_BOLD}{C_GREEN}»{RESET_COLOR} {T['skip_n_frames']}").strip()
        skip = int(s_in) if s_in else 1
        
        loop_in = input(f"  {C_BOLD}{C_GREEN}»{RESET_COLOR} {T['repeat_video']}").strip().lower()
        loop = loop_in in ["s", "y", "o", "j"]
        
        # Playback
        try: play_engine(vid, width, use_color, skip, loop)
        except KeyboardInterrupt: pass
        
        # Export
        exp_in = input(f"\n  {C_BOLD}{C_YELLOW}»{RESET_COLOR} {T['export_q']}").strip().lower()
        if exp_in in ["s", "y", "o", "j"]:
            export_flow(vid, use_color, width if width else 120)
            
        retry = input(f"\n  {C_BOLD}{C_CYAN}»{RESET_COLOR} {T['try_again_q']}").strip().lower()
        if retry not in ["s", "y", "o", "j"]: break

    clear_console()
    print("\n  Thanks for using ASCII Player Video Creator!\n Follow us on tiktok! @stepanusputra16 & @coralgameryt")

if __name__ == "__main__":
    main()
