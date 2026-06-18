"""
plugin_loader.py  –  ASCII Studio 2.0
Discovers and loads plugin modules from the plugins/ directory.

Each plugin can expose:
  render(frame, width) -> str          custom ASCII renderer
  export(frames, fps, output_path)     custom export format
  THEME = { ... }                      custom theme dict
  PLUGIN_NAME, PLUGIN_VERSION, ...     metadata
"""

import sys
import importlib.util
from pathlib import Path
from typing import Callable

PLUGINS_DIR = Path(__file__).parent / "plugins"

# Registries populated at load time
renderers: dict[str, Callable]  = {}   # name -> render(frame, width) -> str
exporters: dict[str, Callable]  = {}   # name -> export(frames, fps, path)
themes:    dict[str, dict]      = {}   # name -> theme dict
_loaded:   list[str]            = []   # module names successfully loaded
_errors:   list[str]            = []   # (module, error) pairs


def load_all() -> None:
    """
    Import every .py file in plugins/ (except __init__ and README).
    Safe: import errors are caught and stored in _errors.
    """
    if not PLUGINS_DIR.exists():
        return

    for path in sorted(PLUGINS_DIR.glob("*.py")):
        if path.stem.startswith("_"):
            continue
        _load_one(path)


def _load_one(path: Path) -> None:
    mod_name = f"_plugin_{path.stem}"
    try:
        spec   = importlib.util.spec_from_file_location(mod_name, path)
        module = importlib.util.module_from_spec(spec)           # type: ignore
        sys.modules[mod_name] = module
        spec.loader.exec_module(module)                          # type: ignore

        name = getattr(module, "PLUGIN_NAME", path.stem)

        if callable(getattr(module, "render", None)):
            renderers[name] = module.render

        if callable(getattr(module, "export", None)):
            exporters[name] = module.export

        theme_data = getattr(module, "THEME", None)
        if isinstance(theme_data, dict):
            themes[name] = theme_data

        _loaded.append(name)

    except Exception as exc:
        _errors.append(f"{path.name}: {exc}")


def summary() -> str:
    """Return a human-readable load summary for the startup dashboard."""
    lines = [f"  Plugins loaded: {len(_loaded)}"]
    for n in _loaded:
        tags = []
        if n in renderers: tags.append("renderer")
        if n in exporters: tags.append("exporter")
        if n in themes:    tags.append("theme")
        lines.append(f"    ✓ {n}  ({', '.join(tags) or 'metadata only'})")
    for e in _errors:
        lines.append(f"    ✗ {e}")
    return "\n".join(lines)
