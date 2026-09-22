"""
BitForge — Programmer Calculator (Fast Edition)
================================================
基于 PyQt5 + SiliconUI · 亮/暗双主题 · 表达式模式 · 位工具

运行: python bitforge.py
调试: 设 BITFORGE_DEBUG=1 输出关键路径日志
"""

import os
import re
import sys

from PyQt5.QtCore import (Qt, QRectF, QTimer, QEasingCurve, QVariantAnimation,
                          QEvent, QPoint, QByteArray, QSettings, pyqtSignal)
from PyQt5.QtGui import QColor, QFont, QIcon, QKeyEvent, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QDialog, QFrame, QGraphicsDropShadowEffect, QHBoxLayout,
    QInputDialog, QLineEdit, QMainWindow, QLabel, QMenu, QPushButton, QSizePolicy, QToolTip,
    QVBoxLayout, QWidget,
)

from siui.components.button import SiPushButtonRefactor

# =====================================================================
#  调试日志 (BITFORGE_DEBUG=1 启用)  # TODO: remove
# =====================================================================
DEBUG = os.environ.get("BITFORGE_DEBUG") == "1"

def dlog(*args):
    if DEBUG:
        print("[BitForge]", *args)

def make_app_icon():
    """创建高 DPI 下清晰可辨的 BitForge 单色品牌图标。"""
    pixmap=QPixmap(64,64); pixmap.fill(Qt.transparent)
    painter=QPainter(pixmap); painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen); painter.setBrush(QColor("#53A9FD"))
    painter.drawRoundedRect(QRectF(3,3,58,58),16,16)
    painter.setPen(QColor("#ffffff")); painter.setFont(QFont("Segoe UI",29,QFont.Bold))
    painter.drawText(QRectF(3,0,58,60),Qt.AlignCenter,"B")
    painter.end()
    return QIcon(pixmap)

# =====================================================================
#  数学工具
# =====================================================================
ALL_DIGITS = "0123456789ABCDEF"
BIT_MASKS = {8: 0xFF, 16: 0xFFFF, 32: 0xFFFFFFFF, 64: (1 << 64) - 1}
RADIX_DIGITS = {16: "0123456789ABCDEF", 10: "0123456789", 8: "01234567", 2: "01"}
def clamp(v, b): return v & BIT_MASKS[b]
def to_signed(v, b):
    u = clamp(v, b)
    if b == 64: return u - (1 << 64) if u >= (1 << 63) else u
    h = 1 << (b - 1); return u - (1 << b) if u >= h else u

def rotate_left(v, b, count):
    count %= b; u=clamp(v,b)
    return clamp((u<<count) | (u>>(b-count)),b)

def rotate_right(v, b, count):
    count %= b; u=clamp(v,b)
    return clamp((u>>count) | (u<<(b-count)),b)

def byte_swap(v, b):
    return int.from_bytes(clamp(v,b).to_bytes(b//8,"big")[::-1],"big")

def extract_field(v, b, start, width):
    if start<0 or width<=0 or start+width>b: raise ValueError("field out of range")
    return (clamp(v,b)>>start) & ((1<<width)-1)

def write_field(v, b, start, width, field_value):
    if start<0 or width<=0 or start+width>b: raise ValueError("field out of range")
    mask=(1<<width)-1
    return (clamp(v,b) & ~(mask<<start)) | ((field_value & mask)<<start)

_EXPR_TOKEN=re.compile(r"\s*(0[xX][0-9a-fA-F]+|0[bB][01]+|0[oO][0-7]+|\d+|<<|>>|AND|OR|XOR|NOT|[()+\-*/%&|^~])",re.I)
_EXPR_PRECEDENCE={"|":1,"OR":1,"^":2,"XOR":2,"&":3,"AND":3,
                  "<<":4,">>":4,"+":5,"-":5,"*":6,"/":6,"%":6}

def evaluate_expression(text, b=64):
    """Evaluate a bounded programmer-calculator expression without Python eval."""
    tokens=[]; pos=0
    while pos<len(text):
        m=_EXPR_TOKEN.match(text,pos)
        if not m:
            if text[pos:].strip(): raise ValueError(f"无法识别：{text[pos:]}")
            break
        token=m.group(1); tokens.append(token.upper() if token.isalpha() else token); pos=m.end()
    if not tokens: raise ValueError("请输入表达式")
    index=0

    def binary(op,left,right):
        if op in ("|","OR"): value=left|right
        elif op in ("^","XOR"): value=left^right
        elif op in ("&","AND"): value=left&right
        elif op=="<<":
            if right<0: raise ValueError("移位量不能为负")
            value=0 if right>=b else left<<right
        elif op==">>":
            if right<0: raise ValueError("移位量不能为负")
            value=0 if right>=b else left>>right
        elif op=="+": value=left+right
        elif op=="-": value=left-right
        elif op=="*": value=left*right
        elif op=="/":
            if right==0: raise ValueError("除数不能为 0")
            value=left//right
        elif op=="%":
            if right==0: raise ValueError("除数不能为 0")
            value=left%right
        return clamp(value,b)

    def parse_prefix():
        nonlocal index
        if index>=len(tokens): raise ValueError("表达式不完整")
        token=tokens[index]; index+=1
        if token=="(":
            value=parse_expression(1)
            if index>=len(tokens) or tokens[index]!=")": raise ValueError("缺少右括号")
            index+=1; return value
        if token in ("~","NOT","+","-"):
            value=parse_prefix()
            if token in ("~","NOT"): return clamp(~value,b)
            return value if token=="+" else clamp(-value,b)
        try:
            return clamp(int(token,0) if token.lower().startswith(("0x","0b","0o")) else int(token,10),b)
        except ValueError:
            raise ValueError(f"期望数值，得到 {token}")

    def parse_expression(min_precedence):
        nonlocal index
        left=parse_prefix()
        while index<len(tokens):
            op=tokens[index]; precedence=_EXPR_PRECEDENCE.get(op,0)
            if precedence<min_precedence: break
            index+=1
            right=parse_expression(precedence+1)
            left=binary(op,left,right)
        return left

    value=parse_expression(1)
    if index!=len(tokens): raise ValueError(f"意外标记：{tokens[index]}")
    return value

# =====================================================================
#  主题配色 (LIGHT_C / DARK_C, _set_theme 切换)
# =====================================================================
C = {
    "win":"#F0F2F5", "dsp_bg":"#FFFFFF", "dsp_fg":"#101216", "dsp_neg":"#FF6D7F",
    "aux_bg":"#F6F7FA", "aux_fg":"#3A3D48", "title":"#181A20", "sub":"#687080",
    "ver":"#8D96A6", "hint":"#98A0B0", "tb_bg":"#FFFFFF", "tb_bdr":"#D4D4D4",
    "rad_on":"#AF92FB", "rad_off":"#8890A0", "num_bg":"#D4D4D4", "num_fg":"#181A20",
    "dim_bg":"#E1E3E6", "dim_fg":"#A8AEB8", "toast_bg":"#53A9FD", "toast_fg":"#102C46",
    "success":"#58C667", "warning":"#FFB45B", "lock":"#E8D836",
    "op_bg":"#DDEEFD", "op_fg":"#1D6FBE", "op_active":"#2D7FD6",
    "bit_bg":"#EFEAFD", "bit_fg":"#6B4FD8", "eq_bg":"#AF92FB", "eq_fg":"#261A3E",
    "ac_bg":"#FF6D7F", "ac_fg":"#4A1019", "bs_bg":"#FFDDE1", "bs_fg":"#B8323F",
    "bit_on":"#AF92FB", "bit_on_fg":"#261A3E", "bit_off":"#7A8290",
}
LIGHT_C = C.copy()
DARK_C = {**LIGHT_C,
    "win":"#171A20", "dsp_bg":"#20242C", "dsp_fg":"#F3F5F8", "dsp_neg":"#FF6D7F",
    "aux_bg":"#292F3A", "aux_fg":"#D9DEE7", "title":"#F3F5F8", "sub":"#AAB3C2",
    "ver":"#7F8A9B", "hint":"#8590A1", "tb_bg":"#20242C", "tb_bdr":"#454E5D",
    "rad_on":"#AF92FB", "rad_off":"#AAB3C2", "num_bg":"#3A414C", "num_fg":"#F3F5F8",
    "dim_bg":"#272D37", "dim_fg":"#687487", "toast_bg":"#53A9FD", "toast_fg":"#102C46",
    "op_bg":"#1E3448", "op_fg":"#8FC5F5", "op_active":"#53A9FD",
    "bit_bg":"#32294B", "bit_fg":"#CFBBFF", "eq_bg":"#AF92FB", "eq_fg":"#261A3E",
    "ac_bg":"#6A3540", "ac_fg":"#FFE7EA", "bs_bg":"#5A2F35", "bs_fg":"#FFB9C1",
    "bit_on":"#AF92FB", "bit_on_fg":"#261A3E", "bit_off":"#687487",
}
BH = 0    # border_height：取消透明底边，避免下圆角被截断
BR = 12   # border_radius：增强按键四角的视觉辨识
IR = 12   # inner_radius

# =====================================================================
#  按钮
# =====================================================================
class BFButton(SiPushButtonRefactor):
    STYLES = {
        "d":    ("num_bg","num_fg"),
        "op":   ("op_bg","op_fg"),
        "bit":  ("bit_bg","bit_fg"),
        "eq":   ("eq_bg","eq_fg"),
        "ac":   ("ac_bg","ac_fg"),
        "bs":   ("bs_bg","bs_fg"),
    }
    DIMS  = {"d": ("dim_bg","dim_fg")}
    TIPS = {"AC":"全部清除","⌫":"退格","%":"取模","/":"除以","NOT":"按位取反",
            "AND":"按位与","OR":"按位或","XOR":"按位异或","<<":"左移",">>":"右移"}

    def __init__(self, text, style="d", parent=None):
        super().__init__(parent)
        self._sty = style
        self._k = self.STYLES[style]
        self._dim = False
        self._active = False
        self._hover = False
        self._pressed = False
        self._tip=self.TIPS.get(text,"")
        self.setText(text)
        self.setAccessibleName(f"计算器按键 {text}")
        self.setAccessibleDescription(self._tip or f"输入 {text}")
        if self._tip: self.setToolTip(self._tip)
        self.setFocusPolicy(Qt.StrongFocus)
        from siui.gui import SiFont
        self.setFont(SiFont.getFont(size=15))
        self.setMinimumWidth(58); self.setFixedHeight(42)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._paint()

    def _paint(self):
        sd = self.style_data
        sd.background_color = QColor(0, 0, 0, 0)
        sd.idle_color = QColor(0, 0, 0, 0)
        sd.border_radius = BR; sd.border_inner_radius = IR; sd.border_height = BH
        if self._dim:
            k = self.DIMS.get(self._sty, self._k)
            sd.button_color = QColor(C[k[0]]); sd.text_color = QColor(C[k[1]])
            sd.hover_color = QColor(0, 0, 0, 20)
        elif self._active:
            # 待定运算高亮: 主题蓝深一档填充, 白字保证对比
            sd.button_color = QColor(C["op_active"]); sd.text_color = QColor("#FFFFFF")
            sd.hover_color = QColor(255, 255, 255, 45)
        else:
            k = self._k
            sd.button_color = QColor(C[k[0]]); sd.text_color = QColor(C[k[1]])
            # 增强悬停效果
            sd.hover_color = QColor(255, 255, 255, 55) if self._k == ("eq_bg", "eq_fg") else QColor(0, 0, 0, 55)
        self.update()

    def set_active(self, a: bool):
        if a != self._active: self._active = a; self._paint()

    def paintEvent(self,e):
        """单层圆角绘制，避免 SiUI 底边裁剪造成按键缺角。"""
        rect=QRectF(self.rect()).adjusted(1,1,-1,-1)
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        color=QColor(self.style_data.button_color)
        if self._pressed: color=color.darker(112)
        elif self._hover and not self._dim: color=color.lighter(106)
        p.setPen(Qt.NoPen); p.setBrush(color)
        p.drawRoundedRect(rect,BR,BR)
        if self.hasFocus():
            p.setPen(QColor(C["rad_on"])); p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(rect.adjusted(1,1,-1,-1),BR-2,BR-2)
        p.setPen(self.style_data.text_color); p.setFont(self.font())
        p.drawText(self.rect(),Qt.AlignCenter,self.text())
        p.end()

    def enterEvent(self,e):
        self._hover=True; self.update()
        super().enterEvent(e)
        if self._tip:
            QToolTip.showText(e.globalPos(),self._tip,self)

    def leaveEvent(self,e):
        self._hover=False; self._pressed=False; self.update()
        super().leaveEvent(e)
        QToolTip.hideText()

    def mousePressEvent(self,e):
        self._pressed=True; self.update()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self,e):
        self._pressed=False; self.update()
        super().mouseReleaseEvent(e)

    def set_dimmed(self, d: bool):
        if d != self._dim: self._dim = d; self._paint()


# =====================================================================
#  Bit 指示器 (带位号标签)
#  - QPixmap 缓存消除鼠标滑动卡顿
#  - 标签样式: 位号显示在位内部
# =====================================================================
class BitGlow(QWidget):
    valueChanged = pyqtSignal(object)
    selectionChanged = pyqtSignal(object)
    M=8; GAP=3; GGAP=12

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value=0; self._bits=32; self.setFixedHeight(46)
        self._cache=None; self._bw_cache=None; self._dirty=True
        self._font=QFont("Consolas",9); self._mask=0
        self._sel=None; self._anchor=None   # 位域选择: (lo,hi) 闭区间 / 拖拽锚点
        self.setMouseTracking(True)

    def set_val(self,value,bits):
        if self._value==value and self._bits==bits: return
        self._value=value; self._bits=bits
        if self._sel is not None and self._sel[1]>=bits: self.clear_selection()
        self.setFixedHeight(82 if bits>32 else 46)
        self._dirty=True; self.update()

    def set_mask(self,m):
        if self._mask==m: return
        self._mask=m; self._dirty=True; self.update()

    def resizeEvent(self,e):
        self._dirty=True; super().resizeEvent(e)

    def _bit_at(self,x,y):
        w=max(self.width(),1); m=self.M; gap=self.GAP; ggap=self.GGAP
        cols=32 if self._bits>32 else self._bits
        grps=cols//8; tw=w-2*m
        bw=(tw-(grps-1)*ggap-(cols-grps)*gap)/cols; bw=max(bw,7)
        self._bw_cache=bw

        if self._bits>32:
            mid=self.height()//2
            if y<2 or y>self.height()-8: return None
            if y<mid:
                if y<12 or y>12+(mid-18): return None
                bit_off=32
            else:
                ly=mid+2+10
                if y<ly or y>ly+(mid-18): return None
                bit_off=0
        else:
            if y<14 or y>14+2+(self.height()-18): return None
            bit_off=0

        grp_total=8*bw+7*gap+ggap; rel_x=x-m
        if rel_x<0: return None
        gi=int(rel_x//grp_total); inner_x=rel_x-gi*grp_total
        bi=min(int(inner_x//(bw+gap)),7)
        bit_pos=(self._bits-1 if self._bits<=32 else 31)-(gi*8+bi)+bit_off
        return bit_pos if 0<=bit_pos<self._bits else None

    def mousePressEvent(self,e):
        bit_pos=self._bit_at(e.x(),e.y())
        if bit_pos is None: return
        if e.button()==Qt.LeftButton and e.modifiers() & Qt.ShiftModifier:
            # Shift+左键: 开始位域选择 (普通左键仍是翻转)
            self._anchor=bit_pos
            self._sel_apply(bit_pos,bit_pos)
            return
        super().mousePressEvent(e)

    def _sel_apply(self,lo,hi):
        lo,hi=min(lo,hi),max(lo,hi)
        self._sel=(lo,hi)
        self.selectionChanged.emit(self._sel)
        self._dirty=True; self.update()

    def clear_selection(self):
        if self._sel is None: return
        self._sel=None; self._anchor=None
        self.selectionChanged.emit(None)
        self._dirty=True; self.update()

    def _field_value(self):
        lo,hi=self._sel
        return (self._value>>lo)&((1<<(hi-lo+1))-1)

    def mouseReleaseEvent(self,e):
        bit_pos=self._bit_at(e.x(),e.y())
        if self._anchor is not None:
            # 拖拽选择结束; 释放未落在格子上时保留最后区间
            if bit_pos is not None: self._sel_apply(self._anchor,bit_pos)
            self._anchor=None
            return
        if bit_pos is None: return
        if e.button()==Qt.RightButton:
            self.valueChanged.emit(self._value & ~(1<<bit_pos))
        else:
            self.valueChanged.emit(self._value ^ (1<<bit_pos))

    def mouseMoveEvent(self,e):
        bit_pos=self._bit_at(e.x(),e.y())
        if bit_pos is None: return
        if self._anchor is not None:
            # 拖拽中: 实时更新区间并显示位域值
            self._sel_apply(self._anchor,bit_pos)
            lo,hi=self._sel; v=self._field_value()
            QToolTip.showText(e.globalPos(),f"bit {hi}:{lo} = 0x{v:X} ({v})",self)
            return
        value=(self._value>>bit_pos)&1
        masked=" · Mask" if (self._mask>>bit_pos)&1 else ""
        QToolTip.showText(e.globalPos(),f"Bit {bit_pos} = {value}{masked}",self)

    def leaveEvent(self,e):
        QToolTip.hideText()
        super().leaveEvent(e)

    def paintEvent(self,e):
        if self._dirty or self._cache is None:
            self._rebuild()
        p=QPainter(self); p.drawPixmap(0,0,self._cache)

    def _rebuild(self):
        w=max(self.width(),1); h=self.height()
        self._cache=QPixmap(w,h); self._cache.fill(Qt.transparent)
        p=QPainter(self._cache); p.setRenderHint(QPainter.Antialiasing)
        u=clamp(self._value,self._bits); s=bin(u)[2:].zfill(self._bits)
        m=self.M; gap=self.GAP; ggap=self.GGAP

        if self._bits > 32:
            half=self._bits//2; mid=h//2
            for row_idx,(seg,y_off,bo) in enumerate([
                (s[:half],2,half),(s[half:],mid+2,0)]):
                tw=w-2*m; gs=[seg[i:i+8] for i in range(0,half,8)]
                bw=(tw-(len(gs)-1)*ggap-(half-len(gs))*gap)/half; bw=max(bw,7)
                if row_idx==0: self._bw_cache=bw
                pt=8 if bw>=12 else(7 if bw>=9 else 6)
                p.setFont(QFont("Consolas",pt))
                x=m; bit_idx=half-1+bo
                bh=mid-18  # bit rect height per row
                for g in gs:
                    for ch in g:
                        r=QRectF(x,y_off+10,bw,bh); txt=f"{bit_idx:>2d}"
                        if ch=="1":
                            # 外层光晕 (纯色半透明, 内收不越位号区)
                            glow=QColor(C["bit_on"]); glow.setAlpha(30); p.setBrush(glow); p.setPen(Qt.NoPen)
                            p.drawRoundedRect(r.adjusted(-1,-1,1,1),3,3)
                            p.setBrush(QColor(C["bit_on"])); p.setPen(Qt.NoPen)
                            p.drawRoundedRect(r,3,3)
                            p.setPen(QColor(C["bit_on_fg"])); p.drawText(r,Qt.AlignCenter,txt)
                        else:
                            p.setBrush(QColor(C["aux_bg"])); p.setPen(Qt.NoPen)
                            p.drawRoundedRect(r,3,3)
                            p.setPen(QColor(C["bit_off"])); p.drawText(r,Qt.AlignCenter,txt)
                        if self._mask and (self._mask>>bit_idx)&1:
                            p.setPen(QColor(C["warning"])); p.setBrush(Qt.NoBrush)
                            p.drawRoundedRect(r.adjusted(0,0,0,0),3,3)
                        if self._sel and self._sel[0]<=bit_idx<=self._sel[1]:
                            sel_fill=QColor(C["op_active"]); sel_fill.setAlpha(46)
                            p.setBrush(sel_fill); p.setPen(QColor(C["op_active"]))
                            p.drawRoundedRect(r,3,3)
                        x+=bw+gap; bit_idx-=1
                    x+=ggap-gap
            # 分隔线 + 位范围标注 (置于分隔线下方空隙)
            p.setPen(QColor(C["tb_bdr"])); p.drawLine(m,mid-1,w-m,mid-1)
            p.setPen(QColor(C["sub"])); p.setFont(QFont("Consolas",7))
            p.drawText(QRectF(m,2,30,9),Qt.AlignLeft|Qt.AlignVCenter,"63")
            p.drawText(QRectF(w-m-30,2,30,9),Qt.AlignRight|Qt.AlignVCenter,"32")
            p.drawText(QRectF(m,mid+2,30,9),Qt.AlignLeft|Qt.AlignVCenter,"31")
            p.drawText(QRectF(w-m-30,mid+2,30,9),Qt.AlignRight|Qt.AlignVCenter,"0")
        else:
            gs=[s[i:i+8] for i in range(0,self._bits,8)]
            tw=w-2*m
            bw=(tw-(len(gs)-1)*ggap-(self._bits-len(gs))*gap)/self._bits; bw=max(bw,7)
            self._bw_cache=bw
            pt=8 if bw>=12 else(7 if bw>=9 else 6)
            p.setFont(QFont("Consolas",pt))
            x=m; y=14; bit_idx=self._bits-1
            for g in gs:
                for ch in g:
                    txt=f"{bit_idx:>2d}"; r=QRectF(x,y+2,bw,h-18)
                    if ch=="1":
                        # 外层光晕 (纯色半透明, 内收不越位号区)
                        glow=QColor(C["bit_on"]); glow.setAlpha(30); p.setBrush(glow); p.setPen(Qt.NoPen)
                        p.drawRoundedRect(r.adjusted(-1,-1,1,1),3,3)
                        p.setBrush(QColor(C["bit_on"])); p.setPen(Qt.NoPen)
                        p.drawRoundedRect(r,3,3)
                        p.setPen(QColor(C["bit_on_fg"])); p.drawText(r,Qt.AlignCenter,txt)
                    else:
                        p.setBrush(QColor(C["aux_bg"])); p.setPen(Qt.NoPen)
                        p.drawRoundedRect(r,3,3)
                        p.setPen(QColor(C["bit_off"])); p.drawText(r,Qt.AlignCenter,txt)
                    if self._mask and (self._mask>>bit_idx)&1:
                        p.setPen(QColor(C["warning"])); p.setBrush(Qt.NoBrush)
                        p.drawRoundedRect(r.adjusted(0,0,0,0),3,3)
                    if self._sel and self._sel[0]<=bit_idx<=self._sel[1]:
                        sel_fill=QColor(C["op_active"]); sel_fill.setAlpha(46)
                        p.setBrush(sel_fill); p.setPen(QColor(C["op_active"]))
                        p.drawRoundedRect(r,3,3)
                    x+=bw+gap; bit_idx-=1
                x+=ggap-gap
        p.setFont(self._font); p.end(); self._dirty=False


# =====================================================================
#  主窗口
# =====================================================================
class BitForge(QMainWindow):
    APP = "BitForge"; VER = "v1.6.0"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{self.APP} · Programmer Calculator")
        self._app_icon=make_app_icon()
        self.setWindowIcon(self._app_icon)
        self.setMinimumSize(540, 720); self.resize(560, 720)
        self.setFocusPolicy(Qt.StrongFocus)
        self._value=0; self._entry="0"; self._radix=10; self._bit_width=8
        self._new_entry=True; self._signed=False; self._locked=False; self._pending=None; self._error=False
        self._lock_style_state=None   # 上次刷新时的锁定状态 (样式 guard)
        self._aux_last={}             # 辅助行上次 HTML (setText guard)
        self._expr_last=""            # 表达式行上次文本
        self._meta_last=""            # 显示区顶部状态行缓存
        self._display_value="0"       # 未分组的显示值，供复制和右键菜单使用
        self._display_font_size=None
        self._sel_value=None          # 当前选中位域的值 (点击 SEL 标签复制)
        self._persist=True            # 关闭时写 QSettings (测试可关闭)
        self._history=[]              # 最近结果 (最新在前, 上限 10)
        self._expression_history=[]   # 最近表达式（最新在前，上限 5）
        self._last_op=None            # 连按 = 重复上次运算
        self._settings=QSettings("BitForge","BitForge")
        self._restore_settings()
        self._apply_theme_colors()
        self._set_style()
        self._toast_timer=QTimer(self); self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(lambda: self._toast_lb.hide())
        self._value_anim=QVariantAnimation(self)
        self._value_anim.setDuration(120)
        self._value_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._value_anim.valueChanged.connect(self._ani_set_text)
        self._ani_last=""; self._ani_running=False
        self._value_anim.finished.connect(lambda: setattr(self,'_ani_running',False))
        self._build_ui(); self._update_layout_density(); self._refresh_display()
        self._apply_pin(self._pinned)
        g=self._settings.value("win/geometry")
        if g:
            try: self.restoreGeometry(QByteArray.fromBase64(g.encode()))
            except Exception: pass

    HINT = "KB  0-9 A-F  + - * / % & | ^ ~  Enter  Esc  Ctrl+C/V  F1 帮助"

    def _ani_set_text(self,val):
        self._display.setText(f"{val:.0f}")
        self._ani_running=True
        if val>=0: self._set_display_color(C["dsp_fg"])

    def _toast(self,msg,kind="info"):
        colors={
            "info":(C["toast_bg"],C["toast_fg"]),
            "success":(C["success"],"#10351D"),
            "warning":(C["warning"],"#4A2A00"),
            "error":(C["dsp_neg"],"#4A1019"),
        }
        bg,fg=colors.get(kind,colors["info"])
        self._toast_lb.setStyleSheet(f"background:{bg};color:{fg};border-radius:14px;padding:5px 16px 6px 16px;font-size:12px;font-weight:700;")
        self._toast_lb.setText(msg)
        self._toast_lb.adjustSize()
        d=self._toolbar.mapTo(self.centralWidget(),QPoint(0,0))
        self._toast_lb.move(d.x()+self._toolbar.width()-self._toast_lb.width()-10, d.y()+4)
        self._toast_lb.raise_()
        self._toast_lb.show()
        self._toast_timer.start(1600)
        dlog("toast", kind, msg)

    def _menu(self):
        m=QMenu(self)
        m.setStyleSheet(f"QMenu{{background:{C['dsp_bg']};color:{C['title']};border:1px solid {C['tb_bdr']};border-radius:10px;padding:6px;}}"
                        f"QMenu::item{{padding:7px 26px 7px 12px;border-radius:6px;}}"
                        f"QMenu::item:selected{{background:{C['aux_bg']};color:{C['rad_on']};}}"
                        f"QMenu::separator{{height:1px;background:{C['tb_bdr']};margin:5px 8px;}}")
        return m

    # ===== 窗口样式 =====
    def _set_style(self):
        self.setStyleSheet(f"QMainWindow{{background:{C['win']};}}")

    def _set_display_color(self,color):
        self._display.setTextColor(color)
        self._display.setStyleSheet(f"background:transparent;color:{color};border:none;")

    # ===== 构建 UI =====
    def _build_ui(self):
        from siui.components.label import SiLabelRefactor
        from siui.gui import SiFont
        cw=QWidget(self); self.setCentralWidget(cw)
        v=QVBoxLayout(cw); v.setContentsMargins(18,12,18,16); v.setSpacing(8)
        self._root_layout=v
        self._compact_layout=None

        # 进制栏
        tb=QFrame(); tb.setObjectName("calcToolbar")
        self._toolbar=tb
        tb.setStyleSheet(f"QFrame#calcToolbar{{background:{C['tb_bg']};border:1px solid {C['tb_bdr']};border-radius:12px;}}")
        tbl=QHBoxLayout(tb); tbl.setContentsMargins(8,5,8,5); tbl.setSpacing(4)
        self._radix_buttons={}; rf=QFrame()
        rf.setStyleSheet(f"QFrame{{background:{C['tb_bg']};border-radius:10px;border:1px solid {C['tb_bdr']};}}")
        rl=QHBoxLayout(rf); rl.setContentsMargins(3,3,3,3); rl.setSpacing(0)
        for lb,r in [("HEX",16),("DEC",10),("OCT",8),("BIN",2)]:
            b=QPushButton(lb); b.setCheckable(True); b.setChecked(r==self._radix)
            b.setFont(self._si_font(10)); b.setFixedHeight(24); b.setMinimumWidth(44)
            b.setStyleSheet(self._radix_btn_style(r==self._radix))
            b.clicked.connect(lambda _,rr=r: self._rad(rr))
            rl.addWidget(b); self._radix_buttons[r]=b
        tbl.addWidget(rf,1)
        tbl.addSpacing(8)
        self._sign_btn=QPushButton("\u00b1")
        self._sign_btn.setFont(self._si_font(14))
        self._sign_btn.setFixedSize(34,26)
        self._sign_btn.setCheckable(True)
        self._sign_btn.setStyleSheet(self._sign_style(False))
        self._sign_btn.clicked.connect(self._toggle_sign)
        tbl.addWidget(self._sign_btn)
        self._lock_btn=QPushButton("\U0001f512")
        self._lock_btn.setFont(self._si_font(10))
        self._lock_btn.setFixedSize(30,26)
        self._lock_btn.setCheckable(True)
        self._lock_btn.setToolTip("锁定当前位宽")
        self._lock_btn.setStyleSheet(self._lock_btn_style(False))
        self._lock_btn.clicked.connect(self._toggle_lock)
        tbl.addWidget(self._lock_btn)
        self._pin_btn=QPushButton("\U0001f4cc")
        self._pin_btn.setFont(self._si_font(10))
        self._pin_btn.setFixedSize(30,26)
        self._pin_btn.setCheckable(True)
        self._pin_btn.setToolTip("窗口置顶")
        self._pin_btn.setStyleSheet(self._lock_btn_style(False))
        self._pin_btn.clicked.connect(self._toggle_pin)
        tbl.addWidget(self._pin_btn)
        self._hist_btn=QPushButton("\u23f1")
        self._hist_btn.setFont(self._si_font(10))
        self._hist_btn.setFixedSize(30,26)
        self._hist_btn.setToolTip("历史结果")
        self._hist_btn.setStyleSheet(self._lock_btn_style(False))
        self._hist_btn.clicked.connect(self._show_history)
        tbl.addWidget(self._hist_btn)
        self._tools_btn=QPushButton("工具")
        self._tools_btn.setFont(self._si_font(9)); self._tools_btn.setFixedSize(38,26)
        self._tools_btn.setToolTip("位操作工具")
        self._tools_btn.setStyleSheet(self._lock_btn_style(False))
        self._tools_btn.clicked.connect(self._show_tools)
        tbl.addWidget(self._tools_btn)
        tbl.addSpacing(7)
        tbl.addWidget(self._vsep())
        tbl.addSpacing(7)
        self._bw_up=QPushButton("+")
        self._bw_up.setFont(self._si_font(12))
        self._bw_up.setFixedSize(24,26)
        self._bw_up.setStyleSheet(f"QPushButton{{background:transparent;color:{C['rad_off']};border:none;border-radius:5px;}}QPushButton:hover{{color:{C['title']};}}")
        self._bw_up.clicked.connect(self._step_bw_up)
        tbl.addWidget(self._bw_up)
        self._bw_dn=QPushButton("\u2212")
        self._bw_dn.setFont(self._si_font(12))
        self._bw_dn.setFixedSize(24,26)
        self._bw_dn.setStyleSheet(f"QPushButton{{background:transparent;color:{C['rad_off']};border:none;border-radius:5px;}}QPushButton:hover{{color:{C['title']};}}")
        self._bw_dn.clicked.connect(self._step_bw_dn)
        tbl.addWidget(self._bw_dn)
        self._bit_width_lb=QLabel("8b")
        self._bit_width_lb.setFont(self._si_font(9))
        self._bit_width_lb.setStyleSheet(f"color:{C['sub']};padding:0 6px 0 2px;")
        self._bit_width_lb.setAlignment(Qt.AlignCenter)
        self._bit_width_lb.setCursor(Qt.PointingHandCursor)
        self._bit_width_lb.setToolTip("点击选择位宽；+/- 微调并锁定")
        self._bit_width_lb.mouseReleaseEvent = lambda e: self._show_bit_width_menu() if e.button()==Qt.LeftButton else None
        tbl.addWidget(self._bit_width_lb)
        v.addWidget(tb)

        # 显示
        self._display_card=QFrame(); self._display_card.setObjectName("displayCard")
        self._display_card.setStyleSheet(f"QFrame#displayCard{{background:{C['dsp_bg']};border:1px solid {C['tb_bdr']};border-radius:18px;}}")
        display_layout=QVBoxLayout(self._display_card); display_layout.setContentsMargins(0,0,0,0)
        self._display=SiLabelRefactor(self); self._display.setFixedHeight(84)
        self._display.setBackgroundColor(C["dsp_bg"]); self._display.setBorderRadius(18)
        self._display.setAlignment(Qt.AlignRight|Qt.AlignBottom)
        self._display.setFont(SiFont.getFont(size=34)); self._display.setTextColor(C["dsp_fg"])
        self._display.setText("0"); self._display.setContentsMargins(18,12,18,10)
        self._set_display_color(C["dsp_fg"])
        display_layout.addWidget(self._display); v.addWidget(self._display_card)
        dsp_shadow=QGraphicsDropShadowEffect(self)
        dsp_shadow.setBlurRadius(18); dsp_shadow.setOffset(0,3); dsp_shadow.setColor(QColor(80,90,120,55))
        self._display_card.setGraphicsEffect(dsp_shadow)
        rf_shadow=QGraphicsDropShadowEffect(self)
        rf_shadow.setBlurRadius(10); rf_shadow.setOffset(0,2); rf_shadow.setColor(QColor(80,90,120,35))
        rf.setGraphicsEffect(rf_shadow)
        # 显示区左下角: 当前 pending 表达式 (如 "123 +")
        self._expr_label=QLabel(self._display)
        self._expr_label.setStyleSheet(f"color:{C['sub']};font-size:13px;font-weight:600;")
        self._expr_label.setAlignment(Qt.AlignLeft|Qt.AlignBottom)
        self._expr_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._display_meta_label=QLabel(self._display)
        self._display_meta_label.setStyleSheet(f"color:{C['rad_on']};font-size:10px;font-weight:700;letter-spacing:0.4px;")
        self._display_meta_label.setAlignment(Qt.AlignLeft|Qt.AlignTop)
        self._display_meta_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._display.installEventFilter(self)
        self._display.setContextMenuPolicy(Qt.CustomContextMenu)
        self._display.customContextMenuRequested.connect(self._show_display_menu)

        # 独立表达式栏：不改变传统按键计算状态
        expr_bar=QFrame(); expr_bar.setObjectName("expressionBar")
        expr_bar.setStyleSheet(f"QFrame#expressionBar{{background:{C['aux_bg']};border:1px solid {C['tb_bdr']};border-radius:9px;}}")
        expr_l=QHBoxLayout(expr_bar); expr_l.setContentsMargins(10,4,6,4); expr_l.setSpacing(7)
        expr_tag=QLabel("EXPR"); expr_tag.setStyleSheet(f"color:{C['rad_on']};font-size:10px;font-weight:700;letter-spacing:0.8px;")
        self._expression_input=QLineEdit(self)
        self._expression_input.setPlaceholderText("(0x20 << 3) | 0x07")
        self._expression_input.setClearButtonEnabled(True)
        self._expression_input.setToolTip("支持括号、0x/0b/0o 和 + - * / % & | ^ ~ << >>")
        self._expression_input.setStyleSheet(f"QLineEdit{{background:transparent;color:{C['title']};border:none;padding:4px 3px;font-family:Consolas,'Courier New',monospace;}}QLineEdit:focus{{color:{C['title']};}}")
        self._expression_input.returnPressed.connect(self._evaluate_expression)
        self._expression_input.setContextMenuPolicy(Qt.CustomContextMenu)
        self._expression_input.customContextMenuRequested.connect(self._show_expression_menu)
        expr_go=QPushButton("="); expr_go.setFixedSize(32,28); expr_go.clicked.connect(self._evaluate_expression)
        expr_go.setToolTip("计算表达式")
        expr_go.setStyleSheet(f"QPushButton{{background:{C['eq_bg']};color:{C['eq_fg']};border:none;border-radius:8px;font-weight:700;font-size:14px;}}QPushButton:hover{{background:{C['rad_on']};}}")
        expr_l.addWidget(expr_tag); expr_l.addWidget(self._expression_input,1); expr_l.addWidget(expr_go)
        v.addWidget(expr_bar)

        # Bit 与掩码：原生输入框随主题着色，并保留清除操作。
        bit_head=QWidget(); bit_head_l=QHBoxLayout(bit_head); bit_head_l.setContentsMargins(2,2,2,0); bit_head_l.setSpacing(7)
        bit_title=QLabel("BIT MAP"); bit_title.setStyleSheet(f"color:{C['sub']};font-size:10px;font-weight:700;letter-spacing:0.8px;")
        mask_title=QLabel("MASK"); mask_title.setStyleSheet(f"color:{C['sub']};font-size:10px;font-weight:700;letter-spacing:0.8px;")
        self._mask_state_label=QLabel("OFF")
        self._mask_state_label.setFixedWidth(28); self._mask_state_label.setAlignment(Qt.AlignCenter)
        self._mask_le=QLineEdit(self)
        self._mask_le.setPlaceholderText("0x…")
        self._mask_le.setClearButtonEnabled(True)
        self._mask_le.setFixedWidth(154)
        self._mask_le.setToolTip("支持 0x、0b、0o、十进制或无前缀十六进制")
        self._mask_le.textChanged.connect(self._on_mask_changed)
        self._set_mask_feedback("off")
        bit_head_l.addWidget(bit_title)
        self._sel_label=QLabel(self)
        self._sel_label.setStyleSheet(f"background:{C['aux_bg']};border:1px solid {C['op_active']};border-radius:8px;padding:2px 10px;color:{C['title']};font-family:Consolas;font-size:11px;font-weight:600;")
        self._sel_label.setCursor(Qt.PointingHandCursor)
        self._sel_label.setToolTip("Shift+拖拽 bit 选择位域; 点击复制其值 (AC 清除)")
        self._sel_label.hide()
        self._sel_label.mouseReleaseEvent = lambda e: self._copy_text(f"0x{self._sel_value:X}","选中位域") if self._sel_value is not None and e.button()==Qt.LeftButton else None
        bit_head_l.addWidget(self._sel_label)
        bit_head_l.addStretch(); bit_head_l.addWidget(mask_title); bit_head_l.addWidget(self._mask_state_label); bit_head_l.addWidget(self._mask_le)
        v.addWidget(bit_head)

        # Bit
        self._bit_indicator=BitGlow(self); v.addWidget(self._bit_indicator)
        self._bit_indicator.valueChanged.connect(self._on_bit_click)
        self._bit_indicator.selectionChanged.connect(self._on_selection_changed)

        # 辅助 — 2×2 多进制同步显示 (点击复制对应进制值)
        self._aux_labels={}
        aw=QWidget(); al=QVBoxLayout(aw); al.setContentsMargins(0,0,0,0); al.setSpacing(5)
        for row_nm in (("DEC","HEX"),("OCT","BIN")):
            rw=QWidget(); rl=QHBoxLayout(rw); rl.setContentsMargins(0,0,0,0); rl.setSpacing(6)
            for nm in row_nm:
                lb=QLabel(self)
                lb.setTextFormat(Qt.RichText)
                lb.setStyleSheet(f"background:{C['aux_bg']};border:1px solid {C['tb_bdr']};border-radius:9px;padding:0 12px 0 12px;")
                fsize=10 if nm=="BIN" else 12
                lb.setFont(SiFont.getFont(size=fsize))
                lb.setMinimumHeight(34); lb.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
                lb.setToolTip("点击复制")
                lb.setCursor(Qt.PointingHandCursor)
                lb.mouseReleaseEvent = lambda e, name=nm: self._copy_radix(name) if e.button()==Qt.LeftButton else None
                rl.addWidget(lb); self._aux_labels[nm]=lb
            al.addWidget(rw)
        v.addWidget(aw)

        # 按钮
        rows=[
            [("AC","ac",lambda: self._clear_all()),("⌫","bs",lambda: self._backspace()),
             ("%","op",lambda: self._apply_operator("mod")),("/","op",lambda: self._apply_operator("div")),
             ("NOT","bit",lambda: self._apply_operator("not"))],
            [("7","d",lambda: self._input_digit("7")),("8","d",lambda: self._input_digit("8")),
             ("9","d",lambda: self._input_digit("9")),("*","op",lambda: self._apply_operator("mul")),
             ("AND","bit",lambda: self._apply_operator("and"))],
            [("4","d",lambda: self._input_digit("4")),("5","d",lambda: self._input_digit("5")),
             ("6","d",lambda: self._input_digit("6")),("-","op",lambda: self._apply_operator("sub")),
             ("OR","bit",lambda: self._apply_operator("or"))],
            [("1","d",lambda: self._input_digit("1")),("2","d",lambda: self._input_digit("2")),
             ("3","d",lambda: self._input_digit("3")),("+","op",lambda: self._apply_operator("add")),
             ("XOR","bit",lambda: self._apply_operator("xor"))],
            [("0","d",lambda: self._input_digit("0")),("A","d",lambda: self._input_digit("A")),
             ("B","d",lambda: self._input_digit("B")),("=","eq",lambda: self._equals()),
             ("<<","bit",lambda: self._apply_operator("lsh"))],
            [("C","d",lambda: self._input_digit("C")),("D","d",lambda: self._input_digit("D")),
             ("E","d",lambda: self._input_digit("E")),("F","d",lambda: self._input_digit("F")),
             (">>","bit",lambda: self._apply_operator("rsh"))],
        ]
        self._buttons=[]; self._digit_btns={}; self._op_btns={}
        OP_TXT={"+":"add","-":"sub","*":"mul","/":"div","%":"mod","NOT":"not",
                "AND":"and","OR":"or","XOR":"xor","<<":"lsh",">>":"rsh"}
        grid=QWidget(); self._keypad_grid=grid
        grid.setFixedHeight(6*42+5*5); grid.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        gl=QVBoxLayout(grid); gl.setContentsMargins(0,0,0,0); gl.setSpacing(5)
        for rd in rows:
            rw=QWidget(); rl=QHBoxLayout(rw); rl.setContentsMargins(0,0,0,0); rl.setSpacing(5)
            for txt,sty,cb in rd:
                btn=BFButton(txt,sty,self); btn.clicked.connect(cb)
                rl.addWidget(btn); self._buttons.append(btn)
                if txt in "0123456789ABCDEF": self._digit_btns[txt]=btn
                if txt in OP_TXT: self._op_btns[OP_TXT[txt]]=btn
            gl.addWidget(rw)
        v.addWidget(grid)

        # 提示 (键帽样式, 随主题着色)
        self._hint_label=SiLabelRefactor(self)
        self._hint_label.setTextFormat(Qt.RichText)
        self._hint_label.setText(self._hint_html())
        self._hint_label.setFont(SiFont.getFont(size=10)); self._hint_label.setTextColor(C["hint"])
        self._hint_label.setStyleSheet(f"color:{C['hint']};")
        self._hint_label.setAlignment(Qt.AlignCenter); self._hint_label.setFixedHeight(18)
        v.addWidget(self._hint_label)

        # 浮动 toast 胶囊 (显示区右上角, 自动消失)
        self._toast_lb=QLabel(cw)
        self._toast_lb.setStyleSheet(f"background:{C['toast_bg']};color:{C['toast_fg']};border-radius:14px;padding:5px 16px 6px 16px;font-size:12px;font-weight:600;")
        self._toast_lb.setAlignment(Qt.AlignCenter)
        self._toast_lb.hide()

        # 初始进制状态
        self._refresh_radix_buttons()

    # ===== 工具 =====
    def _hint_html(self,compact=False):
        """底部快捷键提示: 键帽样式, 随主题着色。"""
        kb=lambda t:(f"<span style='background:{C['aux_bg']};color:{C['title']};"
                     f"font-weight:600;'>&nbsp;{t}&nbsp;</span>")
        plain=lambda t:f"<span style='color:{C['hint']}'>{t}</span>"
        sep=plain("  ·  ")
        if compact:
            return (kb("F1")+plain(" 帮助 ")+sep+
                    kb("F2")+plain(" 表达式 ")+sep+
                    kb("Ctrl+C/V"))
        return (kb("F1")+plain(" 帮助 ")+sep+
                kb("F2")+plain(" 表达式 ")+sep+
                kb("Ctrl+C")+plain(" 复制 ")+sep+
                kb("Ctrl+V")+plain(" 粘贴 ")+sep+
                plain("Enter 求值 · Esc 清空"))

    def _vsep(self):
        w=QWidget(); w.setFixedSize(1,16)
        w.setStyleSheet(f"background:{C['tb_bdr']};")
        return w

    def eventFilter(self,obj,ev):
        if obj is self._display and ev.type()==QEvent.Resize:
            m=self._display.contentsMargins()
            self._display_meta_label.setGeometry(m.left(), 5,
                self._display.width()-m.left()-m.right(), 18)
            self._expr_label.setGeometry(m.left(), 0,
                self._display.width()-m.left()-m.right(), self._display.height()-3)
        return super().eventFilter(obj,ev)

    def resizeEvent(self,e):
        if not all(hasattr(self,name) for name in ("_root_layout","_tools_btn","_mask_le","_hint_label")):
            return super().resizeEvent(e)
        self._update_layout_density()
        super().resizeEvent(e)

    def _update_layout_density(self):
        compact=self.width()<620
        if compact!=getattr(self,"_compact_layout",None):
            self._compact_layout=compact
            self._root_layout.setContentsMargins(12 if compact else 18,10,12 if compact else 18,14)
            self._tools_btn.setText("⋯" if compact else "工具")
            self._tools_btn.setFixedWidth(28 if compact else 38)
            self._mask_le.setFixedWidth(118 if compact else 154)
            self._hint_label.setText(self._hint_html(compact))
            self._aux_last={}
            dlog("layout", "compact" if compact else "regular", "width", self.width())

    # ===== 设置记忆 =====
    def _restore_settings(self):
        s=self._settings
        self._theme=s.value("ui/theme","light")
        if self._theme not in ("light","dark"): self._theme="light"
        self._radix=s.value("calc/radix",10,type=int)
        if self._radix not in RADIX_DIGITS: self._radix=10
        self._signed=s.value("calc/signed",False,type=bool)
        self._locked=s.value("calc/locked",False,type=bool)
        self._bit_width=s.value("calc/bit_width",8,type=int)
        if self._bit_width not in BIT_MASKS: self._bit_width=8
        self._pinned=s.value("win/pinned",False,type=bool)

    def _apply_theme_colors(self):
        C.clear(); C.update(DARK_C if self._theme=="dark" else LIGHT_C)

    def _set_theme(self,theme):
        if theme==self._theme: return
        expression=self._expression_input.text()
        mask=self._mask_le.text()
        self._theme=theme; self._apply_theme_colors(); self._set_style()
        old=self.takeCentralWidget()
        if old is not None: old.deleteLater()
        self._aux_last={}; self._expr_last=""; self._meta_last=""; self._lock_style_state=None; self._display_font_size=None
        self._build_ui(); self._expression_input.setText(expression); self._mask_le.setText(mask)
        self._update_layout_density(); self._refresh_display()
        if self._error:
            # 错误态换主题后重绘 Error, 避免显示回流为默认 0
            self._display.setText("Error"); self._set_display_color(C["dsp_neg"])
        self._toast("深色主题" if theme=="dark" else "亮色主题")
        dlog("theme set:", theme)

    def closeEvent(self,e):
        if self._persist:
            s=self._settings
            s.setValue("ui/theme",self._theme)
            s.setValue("calc/radix",self._radix)
            s.setValue("calc/signed",self._signed)
            s.setValue("calc/locked",self._locked)
            s.setValue("calc/bit_width",self._bit_width)
            s.setValue("win/pinned",self._pinned)
            s.setValue("win/geometry",bytes(self.saveGeometry().toBase64()).decode())
        super().closeEvent(e)

    def _toggle_pin(self):
        self._pinned=self._pin_btn.isChecked()
        self._pin_btn.setStyleSheet(self._lock_btn_style(self._pinned))
        self._apply_pin(self._pinned)
        self._toast("已置顶" if self._pinned else "取消置顶")

    def _apply_pin(self,on):
        flag=Qt.WindowStaysOnTopHint
        if bool(self.windowFlags() & flag)!=on:
            self.setWindowFlag(flag,on)
            if self.isVisible(): self.show()

    def _show_display_menu(self,pos):
        if self._error:
            # 错误态没有可复制的数值, 防止把字面 "Error" 复制走
            self._toast("错误状态无可复制值","warning")
            return
        m=self._menu()
        cur=self._display_value
        a_cur=m.addAction(f"复制  {cur}")
        m.addSeparator()
        a_hex=m.addAction(f"HEX   {self._aux_value('HEX')}")
        a_dec=m.addAction(f"DEC   {self._aux_value('DEC')}")
        a_oct=m.addAction(f"OCT   {self._aux_value('OCT')}")
        a_bin=m.addAction(f"BIN   {self._aux_value('BIN')}")
        act=m.exec_(self._display.mapToGlobal(pos))
        if act is None: return
        if act==a_cur: self._copy_text(cur,"当前值")
        elif act==a_hex: self._copy_radix("HEX")
        elif act==a_dec: self._copy_radix("DEC")
        elif act==a_oct: self._copy_radix("OCT")
        elif act==a_bin: self._copy_radix("BIN")

    def _si_font(self,s):
        try:
            from siui.gui import SiFont
            return SiFont.getFont(size=s)
        except: f=QFont("Segoe UI",s); f.setHintingPreference(QFont.PreferNoHinting); return f

    def _radix_btn_style(self,on):
        if on: return (f"QPushButton{{background:{C['rad_on']};color:{C['eq_fg']};border:none;"
                       f"border-radius:7px;font-weight:600;}}"
                       f"QPushButton:hover{{background:{C['rad_on']};}}")
        return (f"QPushButton{{background:transparent;color:{C['rad_off']};border:none;"
                f"border-radius:7px;font-weight:600;}}"
                f"QPushButton:hover{{color:{C['title']};}}")

    @staticmethod
    def _lock_btn_style(checked):
        if checked:
            return (f"QPushButton{{background:{C['lock']};color:#3A3200;border:none;"
                    f"border-radius:5px;font-size:12px;}}")
        return (f"QPushButton{{background:transparent;color:{C['rad_off']};border:none;"
                f"border-radius:5px;font-size:12px;}}"
                f"QPushButton:hover{{color:{C['title']};}}"
                f"QPushButton:checked{{color:{C['rad_on']};}}")

    def _refresh_radix_buttons(self):
        for r,b in self._radix_buttons.items(): b.setStyleSheet(self._radix_btn_style(r==self._radix))
        valid=RADIX_DIGITS[self._radix]
        for ch,btn in self._digit_btns.items(): btn.set_dimmed(ch not in valid)

    def _toggle_sign(self):
        self._signed=not self._signed
        self._sign_btn.setChecked(self._signed)
        self._sign_btn.setStyleSheet(self._sign_style(self._signed))
        self._refresh_display()
        self._toast("有符号" if self._signed else "无符号")

    def _toggle_lock(self):
        self._locked=self._lock_btn.isChecked()
        self._lock_btn.setToolTip("位宽已锁定" if self._locked else "锁定当前位宽")
        self._lock_btn.setStyleSheet(self._lock_btn_style(self._locked))
        self._toast("位宽已锁定" if self._locked else "位宽自动")

    def _step_bw_up(self):
        for b in (16,32,64):
            if self._bit_width<b:
                self._bit_width=b; self._locked=True; self._lock_btn.setChecked(True)
                self._lock_btn.setToolTip("位宽已锁定")
                self._refresh_display(); self._toast(f"位宽 {b}b"); return

    def _step_bw_dn(self):
        for b in (32,16,8):
            if self._bit_width>b:
                self._bit_width=b; self._locked=True; self._lock_btn.setChecked(True)
                self._lock_btn.setToolTip("位宽已锁定")
                self._refresh_display(); self._toast(f"位宽 {b}b"); return

    def _show_bit_width_menu(self):
        m=self._menu()
        acts={b:m.addAction(f"{b} bit") for b in BIT_MASKS}
        act=m.exec_(self._bit_width_lb.mapToGlobal(self._bit_width_lb.rect().bottomLeft()))
        if act is not None:
            self._set_bit_width(next(b for b,a in acts.items() if a==act))

    def _set_bit_width(self,b):
        if b not in BIT_MASKS:
            dlog("bit width rejected:", b)
            return
        self._bit_width=b; self._locked=True
        self._lock_btn.setChecked(True); self._lock_btn.setToolTip("位宽已锁定")
        self._value_anim.stop(); self._ani_running=False; self._ani_last=""
        self._entry=self._format_entry(self._value)
        self._refresh_display(); self._toast(f"位宽锁定为 {b}b")
        dlog("bit width set:", b)

    def _show_about(self):
        d=QDialog(self)
        d.setWindowTitle("关于 BitForge")
        d.setFixedSize(380,280)
        d.setStyleSheet(f"QDialog{{background:{C['dsp_bg']}}}")
        l=QVBoxLayout(d); l.setContentsMargins(24,20,24,20)
        ti=QLabel(f"<b style='font-size:20px;color:{C['op_active']};'>BitForge</b>")
        ti.setAlignment(Qt.AlignCenter)
        l.addWidget(ti)
        vl=QLabel(f"v{self.VER}" if not self.VER.startswith("v") else self.VER)
        vl.setAlignment(Qt.AlignCenter); vl.setStyleSheet(f"font-size:13px;color:{C['sub']};margin-bottom:8px;")
        l.addWidget(vl)
        for t in ["Programmer Calculator",""]:
            lb=QLabel(t); lb.setAlignment(Qt.AlignCenter); lb.setStyleSheet(f"font-size:12px;color:{C['sub']};")
            l.addWidget(lb)
        gl=QLabel(f"<a href='#' style='color:{C['op_active']};font-size:13px;text-decoration:none;'>github.com/Hush-xv/BitForge</a>")
        gl.setAlignment(Qt.AlignCenter); gl.setCursor(Qt.PointingHandCursor)
        gl.linkActivated.connect(lambda: __import__('webbrowser').open("https://github.com/Hush-xv/BitForge"))
        l.addWidget(gl); l.addStretch()
        l.addWidget(QLabel("Built with PyQt5 + SiliconUI",alignment=Qt.AlignCenter,styleSheet=f"font-size:11px;color:{C['hint']};"))
        d.exec_()

    def _show_help(self):
        d=QDialog(self)
        d.setWindowTitle("BitForge 使用说明")
        d.setFixedSize(430,330)
        d.setStyleSheet(f"QDialog{{background:{C['dsp_bg']};}}")
        l=QVBoxLayout(d); l.setContentsMargins(24,20,24,20); l.setSpacing(10)
        title=QLabel(f"<b style='font-size:18px;color:{C['op_active']};'>快速使用</b>")
        title.setAlignment(Qt.AlignCenter); l.addWidget(title)
        text=("<b>输入：</b>0–9，HEX 模式可输入 A–F；Ctrl+V 自动识别常见进制。<br>"
              "<b>运算：</b>+ − × ÷ %、AND / OR / XOR、~、&lt;&lt; / &gt;&gt;。<br>"
              "<b>位宽：</b>点击位宽标签直接选择；+ / − 调整并自动锁定。<br>"
              "<b>位操作：</b>左键切换位，右键清零；“工具”提供循环移位、字节交换与位域操作。<br>"
              "<b>结果：</b>点击辅助进制行复制；历史按钮可重新载入结果。<br>"
              "<b>表达式：</b>支持括号、进制前缀及全部常用位运算，使用当前锁定位宽。<br>"
              "<b>快捷键：</b>Enter =，Esc 清空，Ctrl+C 复制，F1 帮助，F2 定位表达式栏。")
        body=QLabel(text); body.setWordWrap(True); body.setStyleSheet(f"font-size:12px;color:{C['aux_fg']};line-height:1.6;")
        l.addWidget(body); l.addStretch()
        close=QPushButton("关闭"); close.clicked.connect(d.accept); close.setFixedHeight(30)
        l.addWidget(close)
        d.exec_()

    @staticmethod
    def _sign_style(on):
        if on: return (f"QPushButton{{background:{C['op_active']};color:{C['op_fg']};border:none;border-radius:7px;}}"
                       f"QPushButton:hover{{background:{C['op_active']};}}")
        return (f"QPushButton{{background:transparent;color:{C['rad_off']};border:none;border-radius:7px;}}"
                f"QPushButton:hover{{color:{C['title']};}}")

    # ===== 复制 / 粘贴 / 历史 =====
    def _copy_text(self,text,label):
        QApplication.clipboard().setText(text)
        self._toast(f"已复制 {label} {text}","success")
        dlog("copy", label, text)

    def _copy_current(self):
        self._copy_text(self._display_value,"当前值")

    def _copy_radix(self,name):
        self._copy_text(self._aux_value(name),name)

    def _set_error(self,message):
        self._error=True; self._pending=None; self._last_op=None
        self._value_anim.stop(); self._ani_running=False
        self._set_active_op(None)
        self._display.setText("Error"); self._set_display_color(C["dsp_neg"])
        self._toast(message,"error")
        dlog("calculation error:", message)

    def _paste(self):
        text=QApplication.clipboard().text().strip()
        for ch in (",","_"," "): text=text.replace(ch,"")
        if not text: return
        try:
            low=text.lower()
            if low.startswith("0x"): v=int(text[2:],16)
            elif low.startswith("0b"): v=int(text[2:],2)
            elif low.startswith("0o"): v=int(text[2:],8)
            elif low.endswith("h") and low[:-1] and all(c in "0123456789abcdef" for c in low[:-1]):
                v=int(low[:-1],16)
            elif text[1:] and any(c in "abcdefABCDEF" for c in text[1:]): v=int(text,16)
            else: v=int(text,10)
        except ValueError:
            self._toast("无法识别剪贴板数值","warning")
            dlog("paste parse failed:", text)
            return
        self._load_value(v)
        self._toast(f"已粘贴 {text}","success")
        dlog("paste", text, "->", hex(self._value))

    def _evaluate_expression(self):
        text=self._expression_input.text().strip()
        bits=self._bit_width if self._locked else 64
        try: value=evaluate_expression(text,bits)
        except ValueError as exc:
            self._toast(f"表达式错误：{exc}","error")
            dlog("expression failed:", text, exc)
            return
        if self._error: self._error=False
        if not self._locked: self._bit_width=self._calc_bw(value)
        self._value=clamp(value,self._bit_width); self._entry=self._format_entry(self._value)
        self._new_entry=True; self._pending=None; self._last_op=None
        self._set_active_op(None); self._remember(self._value); self._refresh_display()
        self._remember_expression(text)
        self._toast("表达式已计算","success")
        dlog("expression", text, "->", hex(self._value), "bits", self._bit_width)

    def _remember_expression(self,text):
        if text in self._expression_history: self._expression_history.remove(text)
        self._expression_history.insert(0,text)
        del self._expression_history[5:]
        dlog("expression history", len(self._expression_history), text)

    def _show_expression_menu(self,pos):
        m=self._expression_input.createStandardContextMenu()
        m.setStyleSheet(self._menu().styleSheet())
        if self._expression_history:
            m.addSeparator()
            actions=[m.addAction(f"最近：{text}") for text in self._expression_history]
            a_clear=m.addAction("清除表达式历史")
        else:
            actions=[]; a_clear=None
        act=m.exec_(self._expression_input.mapToGlobal(pos))
        if act in actions:
            self._expression_input.setText(self._expression_history[actions.index(act)])
            self._expression_input.setFocus()
            self._toast("已载入最近表达式")
        elif act==a_clear:
            self._expression_history=[]
            self._toast("表达式历史已清除","success")

    def _load_value(self,v):
        if self._error: self._clear_all()
        self._value=clamp(v,64)
        self._entry=self._format_entry(self._value)
        self._new_entry=False
        self._pending=None
        self._set_active_op(None)
        self._refresh_display()

    def _remember(self,v):
        if not self._history or self._history[0]!=v:
            self._history.insert(0,v)
            del self._history[10:]

    def _show_history(self):
        if not self._history:
            self._toast("暂无历史")
            return
        m=self._menu()
        acts=[]
        for v in self._history:
            acts.append(m.addAction(f"{v}   0x{v:X}"))
        m.addSeparator()
        a_clr=m.addAction("清空历史")
        act=m.exec_(self._hist_btn.mapToGlobal(self._hist_btn.rect().bottomLeft()))
        if act is None: return
        if act==a_clr:
            self._history=[]; self._toast("历史已清空","success")
        else:
            self._load_value(self._history[acts.index(act)])
            self._toast(f"已载入 0x{self._value:X}","success")

    def _show_tools(self):
        m=self._menu()
        state=m.addAction(f"当前：{self._bit_width} bit · {'深色' if self._theme=='dark' else '亮色'}主题")
        state.setEnabled(False)
        m.addSeparator()
        a_ones=m.addAction(f"当前 {self._bit_width} bit 全置 1")
        a_zero=m.addAction("当前位宽清零")
        a_invert=m.addAction("当前位宽取反")
        m.addSeparator()
        a_rol=m.addAction("循环左移  ROL")
        a_ror=m.addAction("循环右移  ROR")
        a_swap=m.addAction("字节交换  Byte Swap")
        m.addSeparator()
        a_extract=m.addAction("提取位域…")
        a_write=m.addAction("写入位域…")
        sign_menu=m.addMenu("符号扩展")
        sign_actions={b:sign_menu.addAction(f"从 {b} bit 扩展")
                      for b in (8,16,32) if b<self._bit_width}
        m.addSeparator()
        appearance=m.addMenu("外观")
        a_light=appearance.addAction("亮色主题")
        a_dark=appearance.addAction("深色主题")
        m.addSeparator()
        a_help=m.addAction("帮助  F1")
        a_about=m.addAction(f"关于 BitForge  {self.VER}")
        act=m.exec_(self._tools_btn.mapToGlobal(self._tools_btn.rect().bottomLeft()))
        if act==a_ones: self._apply_tool_value(BIT_MASKS[self._bit_width],"全置 1")
        elif act==a_zero: self._apply_tool_value(0,"清零")
        elif act==a_invert: self._apply_tool_value(~self._value,"按位取反")
        elif act==a_rol: self._apply_tool_value(rotate_left(self._value,self._bit_width,1),"循环左移 1 位")
        elif act==a_ror: self._apply_tool_value(rotate_right(self._value,self._bit_width,1),"循环右移 1 位")
        elif act==a_swap: self._apply_tool_value(byte_swap(self._value,self._bit_width),"字节交换")
        elif act==a_extract: self._extract_field()
        elif act==a_write: self._write_field()
        elif act==a_light: self._set_theme("light")
        elif act==a_dark: self._set_theme("dark")
        elif act==a_help: self._show_help()
        elif act==a_about: self._show_about()
        else:
            for b,a in sign_actions.items():
                if act==a:
                    self._apply_tool_value(clamp(to_signed(self._value,b),self._bit_width),f"{b}b 符号扩展")
                    break

    def _apply_tool_value(self,value,label):
        if self._error: self._error=False
        self._value=clamp(value,64); self._locked=True; self._new_entry=True
        self._entry=self._format_entry(self._value); self._pending=None; self._last_op=None
        self._set_active_op(None); self._remember(self._value); self._refresh_display()
        self._toast(f"{label} · {self._bit_width}b","success")
        dlog("tool", label, "->", hex(self._value), "bits", self._bit_width)

    def _field_range(self):
        start,ok=QInputDialog.getInt(self,"位域起始位","起始位（LSB = 0）：",0,0,self._bit_width-1)
        if not ok: return None
        width,ok=QInputDialog.getInt(self,"位域长度","长度：",1,1,self._bit_width-start)
        return (start,width) if ok else None

    def _extract_field(self):
        field=self._field_range()
        if field is None: return
        start,width=field
        self._apply_tool_value(extract_field(self._value,self._bit_width,start,width),f"提取 bit {start}:{start+width-1}")

    def _write_field(self):
        field=self._field_range()
        if field is None: return
        text,ok=QInputDialog.getText(self,"写入位域","值（支持 0x / 0b / 0o）：")
        if not ok: return
        try: value=int(text.strip().replace("_",""),0)
        except ValueError:
            self._toast("位域值格式无效")
            dlog("field write parse failed:", text)
            return
        start,width=field
        self._apply_tool_value(write_field(self._value,self._bit_width,start,width,value),f"写入 bit {start}:{start+width-1}")

    def _set_active_op(self,op):
        for name,btn in self._op_btns.items():
            btn.set_active(name==op)

    # ===== 计算逻辑 =====
    def _rad(self,r):
        if self._radix==r or self._error: return
        self._radix=r; self._new_entry=False; self._entry=self._format_entry(self._value); self._refresh_radix_buttons(); self._refresh_display()

    def _input_digit(self,d):
        if self._error: self._clear_all()
        if d not in RADIX_DIGITS.get(self._radix,""):
            dlog("digit rejected:", d, "radix:", self._radix); return
        mx={2:self._bit_width,8:22,10:20,16:16}[self._radix]
        if self._new_entry:
            self._entry=d; self._new_entry=False
            self._set_active_op(None)   # 开始输入新操作数, 熄灭运算符高亮
        elif self._entry=="0":
            self._entry=d   # 前导零不叠加
        else:
            if len(self._entry)>=mx:
                self._toast("当前位宽已达输入上限")
                dlog("input max length:", self._entry, "radix:", self._radix); return
            self._entry+=d
        try: self._value=clamp(int(self._entry,self._radix),64)
        except ValueError:
            dlog("int parse failed:", self._entry, "radix:", self._radix); return
        self._refresh_display()

    def _clear_all(self):
        self._value=0; self._entry="0"; self._pending=None; self._new_entry=True; self._bit_width=8; self._locked=False; self._lock_btn.setChecked(False); self._error=False; self._value_anim.stop(); self._ani_running=False; self._ani_last=""; self._last_op=None
        self._set_active_op(None)
        self._bit_indicator.clear_selection()
        self._refresh_display()

    def _backspace(self):
        if self._error: self._clear_all(); return
        if self._new_entry: return
        if len(self._entry)<=1: self._entry="0"; self._new_entry=True
        else: self._entry=self._entry[:-1]
        try: v=int(self._entry,self._radix) if self._entry else 0; self._value=clamp(v,64)
        except ValueError:
            dlog("backspace parse failed:", self._entry, "radix:", self._radix); return
        self._refresh_display()

    def _apply_operator(self,op):
        if self._error: self._clear_all(); return
        if op=="not":
            # 待定运算存在时 NOT 作用于等待中的操作数, 保留待定关系
            if self._pending is not None and self._new_entry:
                self._pending["lhs"]=clamp(~self._pending["lhs"],64)
                self._value=self._pending["lhs"]
                self._refresh_display(); return
            self._value=clamp(~self._value,64); self._entry=self._format_entry(self._value); self._new_entry=True; self._pending=None; self._refresh_display(); return
        # 尚未输入第二个操作数 → 替换运算符, 不提前计算
        if self._pending is not None and self._new_entry:
            self._pending={"op":op,"lhs":self._pending["lhs"],"bits":self._bit_width}
            self._set_active_op(op)
            self._refresh_display(); return
        if self._pending is not None: self._evaluate()
        self._pending={"op":op,"lhs":self._value,"bits":self._bit_width}; self._new_entry=True
        self._set_active_op(op)
        self._refresh_display()

    def _equals(self):
        if self._error: return
        if self._pending is not None:
            self._last_op={"op":self._pending["op"],"rhs":self._value,
                           "bits":self._pending.get("bits",self._bit_width)}
            self._evaluate()
            if not self._error: self._remember(self._value)
            self._new_entry=True
            self._set_active_op(None)
            self._refresh_display(); return
        if self._last_op is not None:
            # 连按 =: 重复上次运算 (结果 op rhs)
            try:
                r=self._compute(self._last_op["op"],self._value,self._last_op["rhs"],
                                self._last_op.get("bits",self._bit_width))
            except (ZeroDivisionError,ValueError):
                self._set_error("除数不能为 0")
                return
            self._value=clamp(r,64); self._entry=self._format_entry(self._value)
            self._remember(self._value)
            self._new_entry=True
            self._set_active_op(None)
            self._refresh_display()

    def _evaluate(self):
        if self._pending is None: return
        op,lhs,rhs=self._pending["op"],self._pending["lhs"],self._value
        bits=self._pending.get("bits",self._bit_width)
        try: r=self._compute(op,lhs,rhs,bits)
        except (ZeroDivisionError,ValueError):
            self._set_error("除数不能为 0" if op in ("div","mod") and rhs==0 else "计算失败")
            return
        if op in ("rol","ror"):
            self._bit_width=bits; self._locked=True
        self._value=clamp(r,64); self._entry=self._format_entry(self._value); self._pending=None

    @staticmethod
    def _compute(op,l,r,b=64):
        if op=="add": return l+r
        if op=="sub": return l-r
        if op=="mul": return l*r
        if op=="div":
            if r==0: raise ZeroDivisionError()
            return l//r
        if op=="mod":
            if r==0: raise ZeroDivisionError()
            return l%r
        if op=="and": return l&r
        if op=="or":  return l|r
        if op=="xor": return l^r
        if op=="lsh":
            return 0 if r>=64 else l<<r   # r 超出 64 位空间一律为 0, 防止无界分配
        if op=="rsh":
            return 0 if r>=64 else l>>r
        if op=="rol": return rotate_left(l,b,r)
        if op=="ror": return rotate_right(l,b,r)
        return l

    def _format_entry(self,v):
        u=clamp(v,self._bit_width)
        if self._radix==16: return format(u,"X")
        if self._radix==8:  return format(u,"o")
        if self._radix==2:  return format(u,"b")
        return str(to_signed(u,self._bit_width))

    def _calc_bw(self,v):
        if self._locked: return self._bit_width
        if self._signed and v<0:
            for b in (8,16,32,64):
                if v >= -(1<<(b-1)):
                    return b
        if v==0: return 8
        n=v.bit_length()
        if n<=8: return 8
        if n<=16: return 16
        if n<=32: return 32
        return 64

    def _aux_value(self, name):
        u=clamp(self._value,self._bit_width)
        if name=="DEC": return str(u if not self._signed else to_signed(u,self._bit_width))
        if name=="HEX": return f"0x{u:X}"
        if name=="OCT": return f"0o{u:o}"
        return f"0b{u:b}"

    def _group_display(self,text):
        if self._radix not in (2,16): return text
        prefix,digits=text[:2],text[2:]
        step=4 if self._radix==2 else 2
        groups=[]
        while digits:
            groups.append(digits[-step:]); digits=digits[:-step]
        return prefix+" ".join(reversed(groups))

    def _refresh_display(self):
        if self._error: return
        self._bit_width=self._calc_bw(self._value); u=clamp(self._value,self._bit_width); t=self._format_entry(self._value)
        if self._radix==16: t="0x"+t
        elif self._radix==8: t="0o"+t
        elif self._radix==2: t="0b"+t
        elif not self._signed: t=str(u)  # DEC 无符号
        raw=t; visual=self._group_display(raw)
        # 数值滚动动画 (仅 DEC、操作结果、值变幅 > 9)
        if self._radix==10 and self._new_entry and t!=self._ani_last:
            try:
                ov=int(self._ani_last); nv=int(t)
                if abs(nv-ov)>=10 and abs(nv-ov)<50000:
                    self._value_anim.stop()
                    self._value_anim.setStartValue(float(ov))
                    self._value_anim.setEndValue(float(nv))
                    self._value_anim.start()
            except: pass
        self._ani_last=t
        if not self._ani_running:
            self._display.setText(visual)
        self._display_value=raw
        font_size=34 if len(visual)<=16 else (26 if len(visual)<=24 else (20 if len(visual)<=42 else 16))
        if font_size!=self._display_font_size:
            self._display_font_size=font_size; self._display.setFont(self._si_font(font_size))
        self._display.setToolTip(f"完整值：{raw}\n右键可按进制复制")
        s=to_signed(u,self._bit_width)
        self._set_display_color(C["dsp_neg"] if (s<0 and self._radix==10 and self._signed) else C["dsp_fg"])
        self._bit_indicator.set_val(self._value,self._bit_width)
        bw_text=f"{self._bit_width}b"
        if self._bit_width_lb.text()!=bw_text: self._bit_width_lb.setText(bw_text)
        radix_name={16:"HEX",10:"DEC",8:"OCT",2:"BIN"}[self._radix]
        state="SIGNED" if self._signed else "UNSIGNED"
        width_state="LOCKED" if self._locked else "AUTO"
        sep=f"<span style='color:{C['hint']}'> · </span>"
        meta=(f"<span>{radix_name}</span>{sep}"
              f"<span>{self._bit_width} BIT</span>{sep}"
              f"<span>{state}</span>{sep}"
              f"<span style='color:{C['lock'] if self._locked else C['rad_on']}'>{width_state}</span>")
        if meta!=self._meta_last:
            self._meta_last=meta
            self._display_meta_label.setText(meta)
        # 位宽标签/锁按钮样式 — 仅锁定状态变化时刷新, 避免每次按键重刷样式表
        if self._locked != self._lock_style_state:
            self._lock_style_state=self._locked
            self._lock_btn.setChecked(self._locked)
            self._lock_btn.setStyleSheet(self._lock_btn_style(self._locked))
            self._bit_width_lb.setStyleSheet(f"color:{C['lock'] if self._locked else C['sub']};padding:0 6px 0 2px;")
        # 多进制辅助行 — 内容不变时跳过 setText, 避免富文本重复解析
        for name in ("DEC","HEX","OCT","BIN"):
            active={"HEX":16,"DEC":10,"OCT":8,"BIN":2}[name]==self._radix
            name_color=C["rad_on"] if active else C["sub"]
            value_color=C["title"] if active else C["aux_fg"]
            html=(f"<span style='color:{name_color};font-size:9px;font-weight:700'>{name}</span>"
                  f"&nbsp;&nbsp;"
                  f"<span style='color:{value_color};font-weight:{'700' if active else '600'}'>{self._aux_value(name)}</span>")
            if self._aux_last.get(name)!=html:
                self._aux_last[name]=html
                self._aux_labels[name].setText(html)
        # 显示区左下角 pending 表达式
        if self._pending is not None:
            sym={"add":"+","sub":"\u2212","mul":"\u00d7","div":"\u00f7","mod":"%",
                 "and":"AND","or":"OR","xor":"XOR","lsh":"<<","rsh":">>",
                 "rol":"ROL","ror":"ROR"}[self._pending["op"]]
            expr=f"{self._pending['lhs']} {sym}"
        else:
            expr=""
        if expr!=self._expr_last:
            self._expr_last=expr
            self._expr_label.setText(expr)
        # 位域选择标签 — 值随当前数值实时更新
        if self._bit_indicator._sel is not None:
            v=(self._value>>self._bit_indicator._sel[0])&((1<<(self._bit_indicator._sel[1]-self._bit_indicator._sel[0]+1))-1)
            if v!=self._sel_value:
                self._sel_value=v
                lo,hi=self._bit_indicator._sel
                self._sel_label.setText(f"SEL {hi}:{lo} = 0x{v:X} · {v}")

    def _on_bit_click(self,v):
        if self._error: self._error=False
        self._value=clamp(v,64); self._entry=self._format_entry(self._value); self._pending=None
        self._set_active_op(None)
        dlog("bit click ->", hex(self._value))
        self._refresh_display()

    def _set_mask_feedback(self,state,detail=""):
        le=self._mask_le
        if state=="active":
            color=C["warning"]
            state_text="ON"
        elif state=="error":
            color=C["dsp_neg"]
            state_text="ERR"
        else:
            color=C["tb_bdr"]
            state_text="OFF"
        le.setStyleSheet(f"QLineEdit{{min-height:24px;border:1px solid {color};border-radius:6px;padding:1px 24px 1px 8px;color:{C['title']};background:{C['aux_bg']};font-family:Consolas;}}QLineEdit:focus{{border-color:{C['rad_on']};background:{C['dsp_bg']};}}")
        self._mask_state_label.setText(state_text)
        self._mask_state_label.setStyleSheet(f"color:{color};font-size:9px;font-weight:700;")
        le.setToolTip(detail or "支持 0x、0b、0o、十进制或无前缀十六进制")

    def _on_selection_changed(self,sel):
        """BitGlow 位域选择变化 → 更新 SEL 标签 (点击可复制)。"""
        if sel is None:
            self._sel_value=None; self._sel_label.hide(); return
        lo,hi=sel
        self._sel_value=(self._value>>lo)&((1<<(hi-lo+1))-1)
        self._sel_label.setText(f"SEL {hi}:{lo} = 0x{self._sel_value:X} · {self._sel_value}")
        self._sel_label.show()

    def _on_mask_changed(self,text):
        if not text.strip():
            self._bit_indicator.set_mask(0)
            self._set_mask_feedback("off")
            return
        t=text.strip()
        try:
            if t[:2].lower()=="0x": m=int(t,16)
            elif t[:2].lower()=="0b": m=int(t,2)
            elif t[:2].lower()=="0o": m=int(t,8)
            elif any(c in "abcdefABCDEF" for c in t): m=int(t,16)
            else: m=int(t,10)
            self._bit_indicator.set_mask(clamp(m,64))
            self._set_mask_feedback("active",f"Mask active: 0x{clamp(m,64):X}")
            dlog("mask active:",hex(clamp(m,64)))
        except ValueError:
            dlog("mask parse failed:", text)
            self._set_mask_feedback("error","掩码格式: 0x / 0b / 0o / 十进制")
            self._toast("掩码格式: 0x / 0b / 0o / 十进制","warning")

    # ===== 键盘 =====
    def keyPressEvent(self,e:QKeyEvent):
        k,tx=e.key(),e.text()
        if k==Qt.Key_C and e.modifiers() & Qt.ControlModifier: self._copy_current(); return
        if k==Qt.Key_V and e.modifiers() & Qt.ControlModifier: self._paste(); return
        if tx in "0123456789": self._input_digit(tx); return
        if tx.lower() in "abcdef" and self._radix==16: self._input_digit(tx.upper()); return
        om={Qt.Key_Plus:"add",Qt.Key_Minus:"sub",Qt.Key_Asterisk:"mul",
            Qt.Key_Slash:"div",Qt.Key_Percent:"mod",
            Qt.Key_Ampersand:"and",Qt.Key_Bar:"or",Qt.Key_AsciiCircum:"xor"}
        if k in om: self._apply_operator(om[k]); return
        if k in (Qt.Key_Enter,Qt.Key_Return) or tx=="=": self._equals(); return
        if k==Qt.Key_Backspace: self._backspace(); return
        if k in (Qt.Key_Escape,Qt.Key_Delete): self._clear_all(); return
        if k==Qt.Key_AsciiTilde: self._apply_operator("not"); return
        if k==Qt.Key_Less: self._apply_operator("lsh"); return
        if k==Qt.Key_Greater: self._apply_operator("rsh"); return
        if k==Qt.Key_F1: self._show_help(); return
        if k==Qt.Key_F2: self._expression_input.setFocus(); return
        super().keyPressEvent(e)


# =====================================================================
def main():
    app=QApplication(sys.argv); app.setApplicationName("BitForge")
    app.setWindowIcon(make_app_icon())
    w=BitForge(); w.show()
    # 立即释放图标包内存 (~50MB, 5410 个 SVG)
    from siui.core import SiGlobal
    if hasattr(SiGlobal.siui,'iconpack') and hasattr(SiGlobal.siui.iconpack,'clear'):
        SiGlobal.siui.iconpack.clear()
    sys.exit(app.exec_())
if __name__=="__main__": main()
