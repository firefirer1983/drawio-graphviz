import logging
from typing import TypeVar, Union
logger = logging.getLogger(__name__)

# Dots Per Inch
DEFAULT_DPI = 96
GRAPHVIZ_DEFAULT_DPI = 72

DEFAULT_PADDING = 0


def position_paddiing(pos: Union[str, float]) -> int:
    """+4 pixel on 1 side"""
    return int(float(pos) + DEFAULT_PADDING)


def size_padding(size: Union[str, float]) -> int:
    """+4 pixel for each side"""
    return int(float(size) + 2 * DEFAULT_PADDING)


def inch2pixel(size: Union[float, str]) -> int:
    return int(float(size) * DEFAULT_DPI)


def dpi72todpi96(pixels: Union[float, str]) -> int:
    # pixel * 96 / 72
    if isinstance(pixels, str):
        pixels = float(pixels)
    return int(pixels * 4) // 3


def json_dapi72to96(dotfile: dict, to_digit: bool = True) -> dict:
    result = dict()

    def _convert(k: str, v: str):
        if k in ("bb", "pos"):
            res = []
            for x in v.split(","):
                try:
                    n = int(dpi72todpi96(x))
                except (ValueError, TypeError):
                    continue
                res.append(n)
            if not to_digit:
                res = ",".join(res)
            logger.info(f"{k}: {v} -> {res}")
            return res
        if k in ("width", "height"):
            res = inch2pixel(v)
            if not to_digit:
               res = str(res)
            logger.info(f"{k}: {v} -> {res}")
            return res
        return v

    def _walker(k: str, dat: Union[int, str, list, dict]) -> Union[int, str, list, dict]:
        if isinstance(dat, str):
            return _convert(k, dat)
        elif isinstance(dat, int):
            return dat
        elif isinstance(dat, list):
            res = list()
            for m in dat:
                ret = _walker(k, m)
                res.append(ret)
            return res
        else:
            res = dict()
            for k, v in dat.items():
                res[k] = _walker(k, v)
        return res

    for k, v in dotfile.items():
        result[k] = _walker(k, v)
    return result
