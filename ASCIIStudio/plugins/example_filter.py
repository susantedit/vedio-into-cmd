"""
example_filter.py  –  ASCII Studio Plugin Example
Demonstrates a custom render filter that inverts brightness.

Drop .py files in this folder and they are auto-loaded at startup.
"""

import numpy as np


# Plugin metadata (optional but recommended)
PLUGIN_NAME    = "Invert Filter"
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR  = "Your Name"


def render(frame: np.ndarray, width: int) -> str:
    """
    Custom renderer: inverts the frame brightness before ASCII conversion.
    Signature must match: (frame: np.ndarray, width: int) -> str
    """
    import cv2
    inverted = 255 - frame
    height = max(1, int(inverted.shape[0] * width / inverted.shape[1] / 2))
    resized = cv2.resize(inverted, (width, height))
    gray    = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    chars   = " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczmwqpdbkhao*#MW&8%B@$0QSXGZJKPHDAUYTRENVLCF"
    n       = len(chars) - 1
    lines   = ["".join(chars[int(p / 255.0 * n)] for p in row) for row in gray]
    return "\n".join(lines)
