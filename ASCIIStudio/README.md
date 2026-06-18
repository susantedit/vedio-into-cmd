# ASCII Studio 2.0

A professional terminal ASCII video player and exporter by **Developer Susant**.

```
 █████╗ ███████╗ ██████╗██╗██╗    ███████╗████████╗██╗   ██╗██████╗ ██╗ ██████╗
██╔══██╗██╔════╝██╔════╝██║██║    ██╔════╝╚══██╔══╝██║   ██║██╔══██╗██║██╔═══██╗
███████║███████╗██║     ██║██║    ███████╗   ██║   ██║   ██║██║  ██║██║██║   ██║
...
```

## Features
- **Startup Dashboard** – build info, dependency versions, animated loading bar
- **System Detection** – Unicode, ANSI, TrueColor, OpenCV HW decode, pygame
- **Settings Menu** – Video / Rendering / Export / Themes / Performance / Language
- **7 Themes** – Gold, Cyberpunk, Dracula, Ocean, Matrix, Nord, Solarized
- **Live Performance HUD** – FPS, CPU, RAM, frame counter, dropped frames
- **Rich Export** – MP4, GIF, WebM, PNG sequence, TXT, HTML, ANSI
- **Recent Files** – auto-remembers last 10 videos
- **Profiles** – Cinema, Fast, Ultra, GitHub Demo (saveable)
- **Benchmark Mode** – synthetic frame conversion speed test
- **Sound Support** – plays original audio via pygame
- **Drag & Drop** – paste or drag paths with quotes stripped automatically
- **Plugin System** – drop `.py` files in `plugins/` to extend
- **Config File** – `ascii_studio.json` persists all settings
- **Interactive Help** – press `H` during playback

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

## Project Structure

```
ASCIIStudio/
├── main.py         Entry point, main loop
├── engine.py       ASCII conversion kernels (numpy/OpenCV)
├── renderer.py     Multi-threaded real-time playback
├── exporter.py     Multi-format export (MP4/GIF/HTML/…)
├── ui.py           All terminal UI components
├── theme.py        Theme loader + ANSI helpers
├── config.py       Settings persistence (ascii_studio.json)
├── utils.py        Terminal detection, perf monitor, helpers
├── themes/         JSON theme files
├── plugins/        User-created extension modules
├── assets/         Logo, banner, icon
├── requirements.txt
└── README.md
```

## Export Formats

| Format       | Description                          |
|--------------|--------------------------------------|
| `mp4`        | H.264 video with ASCII frames        |
| `gif`        | Looping GIF (GitHub-ready)           |
| `webm`       | VP8 web video                        |
| `png_seq`    | Individual PNG frames                |
| `txt`        | Raw ASCII text per frame             |
| `html`       | Self-contained animated HTML page    |
| `ansi`       | ANSI escape sequence animation file  |

## Keyboard Shortcuts (during playback)

| Key       | Action              |
|-----------|---------------------|
| `H`       | Toggle help         |
| `Q`       | Quit                |
| `Ctrl+C`  | Stop playback       |

---

Made with ❤ by [Developer Susant](https://github.com/susantedit)
