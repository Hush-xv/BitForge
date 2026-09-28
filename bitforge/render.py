"""BitForge 显示模型: 纯计算渲染数据, 由主窗口应用到控件。

compute_display_model 产出 DisplayModel (待显示文本/分组/字号/辅助行 HTML 等);
刷新管线 = 同步自动位宽 -> 计算 DisplayModel -> 与控件上次内容 diff 后应用。
"""
from dataclasses import dataclass
from typing import Optional

from PyQt5.QtGui import QFont, QFontMetrics

from .core import OP_SYMBOLS, clamp, to_signed
from .theme import C

GROUP_GAP = 4   # DisplayText 字节/半字节组间距 (像素)


def make_display_font(size):
    """主显示字体: 等宽粗体, 数字宽度稳定不抖动。"""
    f = QFont("Consolas", size, QFont.Bold)
    f.setHintingPreference(QFont.PreferNoHinting)
    return f


def display_groups(radix, text):
    """HEX/BIN 按半字节/字节分组的 (prefix, groups); 其余进制返回 None。"""
    if radix not in (2, 16): return None
    prefix, digits = text[:2], text[2:]
    if (radix == 16 and len(digits) > 8) or (radix == 2 and len(digits) > 32):
        return None
    step = 4 if radix == 2 else 2
    groups = []
    while digits:
        groups.append(digits[-step:]); digits = digits[:-step]
    return prefix, tuple(reversed(groups))


def group_display(radix, text):
    groups = display_groups(radix, text)
    if groups is None: return text
    prefix, parts = groups
    return prefix + " ".join(parts)


_FM_CACHE = {}   # 字号 -> QFontMetrics (Consolas 等宽粗体固定, 每次刷新省去重复构建)

def _metrics(size):
    fm = _FM_CACHE.get(size)
    if fm is None:
        fm = QFontMetrics(make_display_font(size))
        _FM_CACHE[size] = fm
    return fm


def font_size_for(text, groups, available):
    """在 available 像素宽度内能放下的最大显示字号。"""
    for size in (34, 32, 30, 28, 26, 24, 22, 20, 18, 16, 14):
        metrics = _metrics(size)
        if groups:
            prefix, gs = groups
            width = metrics.horizontalAdvance(prefix) + sum(metrics.horizontalAdvance(g) for g in gs)
            width += GROUP_GAP * (len(gs) - 1)
        else:
            width = metrics.horizontalAdvance(text)
        if width <= available:
            return size
    return 14


def aux_text(name, st, pad):
    """辅助行纯文本 (DEC/HEX/OCT/BIN), st 为 CalculatorState。"""
    u = clamp(st.value, st.bit_width)
    if name == "DEC": return str(u if not st.signed else to_signed(u, st.bit_width))
    if name == "HEX": return "0x" + st.format_radix(u, 16, pad)
    if name == "OCT": return f"0o{u:o}"
    return "0b" + st.format_radix(u, 2, pad)


@dataclass
class DisplayModel:
    """一次显示刷新所需的全部待渲染数据。"""
    raw: str                    # 未分组显示文本 (复制/工具提示用)
    visual: str                 # 分组后文本 (非 HEX/BIN 等于 raw)
    groups: Optional[tuple]     # (prefix, groups) 或 None
    font_size: int
    negative: bool              # DEC 有符号负数 → 红色
    aux: dict                   # name -> 辅助行 HTML
    expr: str                   # 显示区左下角待定表达式文本
    rgb: Optional[int]          # HEX 模式低 24 位; 其余进制 None
    le_preview: Optional[str]   # Little Endian 预览; 原始字节序 None


def compute_display_model(st, *, pad_display, byte_order, available_width):
    """由计算状态计算待渲染数据。纯计算, 不触碰控件。"""
    u = clamp(st.value, st.bit_width)
    t = st.format_radix(st.value, st.radix, pad_display and st.radix in (2, 16))
    if st.radix == 16: t = "0x" + t
    elif st.radix == 8: t = "0o" + t
    elif st.radix == 2: t = "0b" + t
    elif not st.signed: t = str(u)   # DEC 无符号
    groups = display_groups(st.radix, t)
    visual = t if groups is None else groups[0] + " ".join(groups[1])
    aux = {}
    for name in ("DEC", "HEX", "OCT", "BIN"):
        active = {"HEX": 16, "DEC": 10, "OCT": 8, "BIN": 2}[name] == st.radix
        name_color = C["rad_on"] if active else C["sub"]
        value_color = C["title"] if active else C["aux_fg"]
        aux[name] = (f"<span style='color:{name_color};font-size:9px;font-weight:700'>{name}</span>"
                     f"&nbsp;&nbsp;"
                     f"<span style='color:{value_color};font-weight:600;font-family:Consolas,monospace'>{aux_text(name, st, pad_display)}</span>")
    if st.pending is not None:
        expr = f"{st.pending['lhs']} {OP_SYMBOLS[st.pending['op']]}"
    else:
        expr = ""
    le = None
    if byte_order == "little":
        le = "0x" + u.to_bytes(st.bit_width // 8, "big")[::-1].hex().upper()
    return DisplayModel(
        raw=t, visual=visual, groups=groups,
        font_size=font_size_for(t, groups, available_width),
        negative=(st.signed and st.radix == 10 and to_signed(u, st.bit_width) < 0),
        aux=aux, expr=expr,
        rgb=(u & 0xFFFFFF) if st.radix == 16 else None,
        le_preview=le)
