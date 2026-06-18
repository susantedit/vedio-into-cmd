# ASCII Studio 2.0 – Plugin System

Place `.py` files here to extend ASCII Studio with custom renderers, filters,
export formats, or themes.

## Plugin Interface

A plugin is a Python module that exposes one or more of the following:

```python
# Custom renderer
def render(frame: np.ndarray, width: int) -> str:
    """Convert a BGR frame to an ASCII string."""
    ...

# Custom export format
def export(frames: list, fps: float, output_path: str) -> None:
    """Write frames to a custom format."""
    ...

# Custom theme (dict matching themes/*.json schema)
THEME = { "name": "MyTheme", "primary": [255,0,0], ... }
```

Plugins are automatically discovered on startup.
