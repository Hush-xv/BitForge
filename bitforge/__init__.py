"""BitForge — Programmer Calculator 包。

兼容层: 保持原单文件 bitforge.py 的全部公开导入接口
(测试与外部脚本 `from bitforge import X` 不受影响)。
"""
from .core import (ALL_DIGITS, BIT_MASKS, DEBUG, OP_SYMBOLS, RADIX_DIGITS,
                   byte_swap, clamp, dec_group, dlog, ellipsize, evaluate_expression,
                   extract_field, parse_number, rotate_left, rotate_right,
                   to_signed, write_field)
from .theme import BH, BR, C, DARK_C, IR, LIGHT_C
from .widgets import BFButton, BitGlow, DisplayText, make_app_icon
from .main_window import BitForge
from .app import main

__all__ = [
    "ALL_DIGITS", "BIT_MASKS", "DEBUG", "OP_SYMBOLS", "RADIX_DIGITS",
    "byte_swap", "clamp", "dec_group", "dlog", "ellipsize", "evaluate_expression",
    "extract_field", "parse_number", "rotate_left", "rotate_right", "to_signed", "write_field",
    "BH", "BR", "C", "DARK_C", "IR", "LIGHT_C",
    "BFButton", "BitForge", "BitGlow", "DisplayText", "make_app_icon", "main",
]
