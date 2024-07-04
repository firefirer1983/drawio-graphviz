from typing import Union

# Dots Per Inch
DEFAULT_DPI = 72

DEFAULT_PADDING = 0


def position_paddiing(pos: Union[str, float]) -> int:
    """+4 pixel on 1 side"""
    return int(float(pos) + DEFAULT_PADDING)


def size_padding(size: Union[str, float]) -> int:
    """+4 pixel for each side"""
    return int(float(size) + 2 * DEFAULT_PADDING)


def inch2pixel(size: Union[float, str]) -> int:
    return int(float(size) * DEFAULT_DPI)
