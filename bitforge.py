"""
BitForge — Programmer Calculator (Fast Edition)
================================================
基于 PyQt5 + SiliconUI · 亮色主题 · 无主题切换 · 无图标加载

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
        elif op=="<<": value=left<<right
        elif op==">>": value=left>>right
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
#  亮色主题配色 (单主题，无切换)
# =====================================================================
C = {
    "win":     "#f0f2f5",  # 窗口背景
    "dsp_bg":  "#ffffff",  # 显示区背景
    "dsp_fg":  "#101216",  # 显示文字
    "dsp_neg": "#d01020",  # 负数
    "aux_bg":  "#f6f7fa",
    "aux_fg":  "#3a3d48",
    "title":   "#181a20",
    "sub":     "#687080",
    "ver":     "#a0a8b8",
    "hint":    "#98a0b0",
    "tb_bg":   "#ffffff",
    "tb_bdr":  "#d8dce4",
    "rad_on":  "#6e40c9",
    "rad_off": "#8890a0",
    "num_bg":  "#e8ecf2",
    "num_fg":  "#181a20",
    "dim_bg":  "#dfe3ea",
    "dim_fg":  "#b4bac6",
    "toast_bg": "#3a2a5e",
    "toast_fg": "#ffffff",
    "op_bg":   "#dce8ff",
    "op_fg":   "#2050b0",
    "bit_bg":  "#efe8ff",
    "bit_fg":  "#6020a0",
    "eq_bg":   "#6838c8",
    "eq_fg":   "#ffffff",
    "ac_bg":   "#ffe8e6",
    "ac_fg":   "#c02030",
    "bs_bg":   "#fff0e0",
    "bs_fg":   "#c06020",
    "bit_on":  "#8040c0",
    "bit_off": "#a8acb8",
}
LIGHT_C = C.copy()
DARK_C = {**LIGHT_C,
    "win":"#171a20", "dsp_bg":"#20242c", "dsp_fg":"#f3f5f8", "dsp_neg":"#ff7b7b",
    "aux_bg":"#292f3a", "aux_fg":"#d9dee7", "title":"#f3f5f8", "sub":"#aab3c2",
    "ver":"#7f8a9b", "hint":"#8590a1", "tb_bg":"#20242c", "tb_bdr":"#3d4655",
    "rad_on":"#9b72e8", "rad_off":"#aab3c2", "num_bg":"#303744", "num_fg":"#f3f5f8",
    "dim_bg":"#272d37", "dim_fg":"#687487", "toast_bg":"#b99aff", "toast_fg":"#1d172b",
    "op_bg":"#273b5b", "op_fg":"#b8d4ff", "bit_bg":"#3a2e55", "bit_fg":"#d5c1ff",
    "eq_bg":"#9b72e8", "ac_bg":"#4a2c34", "ac_fg":"#ffb8c0", "bs_bg":"#4a392b",
    "bs_fg":"#ffd09b", "bit_on":"#aa7dff", "bit_off":"#687487",
}
BH = 2    # border_height
BR = 9    # border_radius
IR = 7    # inner_radius

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
        "bs":   ("op_bg","op_fg"),
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
        self._tip=self.TIPS.get(text,"")
        self.setText(text)
        from siui.gui import SiFont
        self.setFont(SiFont.getFont(size=15))
        self.setMinimumSize(58, 46)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
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
            # 待定运算高亮: 主色填充
            sd.button_color = QColor(C["rad_on"]); sd.text_color = QColor("#ffffff")
            sd.hover_color = QColor(255, 255, 255, 55)
        else:
            k = self._k
            sd.button_color = QColor(C[k[0]]); sd.text_color = QColor(C[k[1]])
            # 增强悬停效果
            sd.hover_color = QColor(255, 255, 255, 55) if self._k == ("eq_bg", "eq_fg") else QColor(0, 0, 0, 55)
        self.update()

    def set_active(self, a: bool):
        if a != self._active: self._active = a; self._paint()

    def enterEvent(self,e):
        super().enterEvent(e)
        if self._tip:
            QToolTip.showText(e.globalPos(),self._tip,self)

    def leaveEvent(self,e):
        super().leaveEvent(e)
        QToolTip.hideText()

    def set_dimmed(self, d: bool):
        if d != self._dim: self._dim = d; self._paint()


# =====================================================================
#  Bit 指示器 (带位号标签)
#  - QPixmap 缓存消除鼠标滑动卡顿
#  - 标签样式: 位号显示在位内部
# =====================================================================
class BitGlow(QWidget):
    valueChanged = pyqtSignal(object)
    M=8; GAP=3; GGAP=12

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value=0; self._bits=32; self.setFixedHeight(46)
        self._cache=None; self._bw_cache=None; self._dirty=True
        self._font=QFont("Consolas",9); self._mask=0

    def set_val(self,value,bits):
        if self._value==value and self._bits==bits: return
        self._value=value; self._bits=bits
        self.setFixedHeight(82 if bits>32 else 46)
        self._dirty=True; self.update()

    def set_mask(self,m):
        if self._mask==m: return
        self._mask=m; self._dirty=True; self.update()

    def resizeEvent(self,e):
        self._dirty=True; super().resizeEvent(e)

    def mouseReleaseEvent(self,e):
        x,y=e.x(),e.y()
        w=max(self.width(),1); m=self.M; gap=self.GAP; ggap=self.GGAP
        cols=32 if self._bits>32 else self._bits
        grps=cols//8; tw=w-2*m
        bw=(tw-(grps-1)*ggap-(cols-grps)*gap)/cols; bw=max(bw,7)
        self._bw_cache=bw

        if self._bits>32:
            mid=self.height()//2
            if y<2 or y>self.height()-8: return
            if y<mid:
                if y<12 or y>12+(mid-18): return
                bit_off=32
            else:
                ly=mid+2+10
                if y<ly or y>ly+(mid-18): return
                bit_off=0
        else:
            if y<14 or y>14+2+(self.height()-18): return
            bit_off=0

        grp_total=8*bw+7*gap+ggap; rel_x=x-m
        if rel_x<0: return
        gi=int(rel_x//grp_total); inner_x=rel_x-gi*grp_total
        bi=min(int(inner_x//(bw+gap)),7)
        bit_pos=(self._bits-1 if self._bits<=32 else 31)-(gi*8+bi)+bit_off
        if bit_pos<0 or bit_pos>=self._bits: return
        if e.button()==Qt.RightButton:
            self.valueChanged.emit(self._value & ~(1<<bit_pos))
        else:
            self.valueChanged.emit(self._value ^ (1<<bit_pos))

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
                            # 外层光晕 (纯色半透明，无渐变)
                            p.setBrush(QColor(140,80,200,40)); p.setPen(Qt.NoPen)
                            p.drawRoundedRect(r.adjusted(-2,-2,2,2),4,4)
                            p.setBrush(QColor(C["bit_on"])); p.setPen(Qt.NoPen)
                            p.drawRoundedRect(r,3,3)
                            p.setPen(QColor("#ffffff")); p.drawText(r,Qt.AlignCenter,txt)
                        else:
                            p.setBrush(QColor("#e6e9f1")); p.setPen(Qt.NoPen)
                            p.drawRoundedRect(r,3,3)
                            p.setPen(QColor(C["bit_off"])); p.drawText(r,Qt.AlignCenter,txt)
                        if self._mask and (self._mask>>bit_idx)&1:
                            p.setPen(QColor("#e09030")); p.setBrush(Qt.NoBrush)
                            p.drawRoundedRect(r.adjusted(0,0,0,0),3,3)
                        x+=bw+gap; bit_idx-=1
                    x+=ggap-gap
            # 分隔线 + 位范围标注 (置于分隔线下方空隙)
            p.setPen(QColor("#d8dce4")); p.drawLine(m,mid-1,w-m,mid-1)
            p.setPen(QColor("#8890a0")); p.setFont(QFont("Consolas",7))
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
                        # 外层光晕 (纯色半透明，无渐变)
                        p.setBrush(QColor(140,80,200,40)); p.setPen(Qt.NoPen)
                        p.drawRoundedRect(r.adjusted(-2,-2,2,2),4,4)
                        p.setBrush(QColor(C["bit_on"])); p.setPen(Qt.NoPen)
                        p.drawRoundedRect(r,3,3)
                        p.setPen(QColor("#ffffff")); p.drawText(r,Qt.AlignCenter,txt)
                    else:
                        p.setPen(QColor(C["bit_off"])); p.drawText(r,Qt.AlignCenter,txt)
                    if self._mask and (self._mask>>bit_idx)&1:
                        p.setPen(QColor("#e09030")); p.setBrush(Qt.NoBrush)
                        p.drawRoundedRect(r.adjusted(0,0,0,0),3,3)
                    x+=bw+gap; bit_idx-=1
                x+=ggap-gap
        p.setFont(self._font); p.end(); self._dirty=False


# =====================================================================
#  主窗口
# =====================================================================
class BitForge(QMainWindow):
    APP = "BitForge"; VER = "v1.5.0"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{self.APP} · Programmer Calculator")
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__),"bitforge.ico")))
        self.setMinimumSize(540, 660); self.resize(560, 700)
        self.setFocusPolicy(Qt.StrongFocus)
        self._value=0; self._entry="0"; self._radix=10; self._bit_width=8
        self._new_entry=True; self._signed=False; self._locked=False; self._pending=None; self._error=False
        self._lock_style_state=None   # 上次刷新时的锁定状态 (样式 guard)
        self._aux_last={}             # 辅助行上次 HTML (setText guard)
        self._expr_last=""            # 表达式行上次文本
        self._display_value="0"       # 未分组的显示值，供复制和右键菜单使用
        self._display_font_size=None
        self._persist=True            # 关闭时写 QSettings (测试可关闭)
        self._history=[]              # 最近结果 (最新在前, 上限 10)
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
        self._build_ui(); self._refresh_display()
        self._apply_pin(self._pinned)
        g=self._settings.value("win/geometry")
        if g:
            try: self.restoreGeometry(QByteArray.fromBase64(g.encode()))
            except Exception: pass

    HINT = "KB  0-9 A-F  + - * / % & | ^ ~  Enter  Esc  Ctrl+C/V  F1 帮助"

    def _ani_set_text(self,val):
        self._display.setText(f"{val:.0f}")
        self._ani_running=True
        if val>=0: self._display.setTextColor(C["dsp_fg"])

    def _toast(self,msg):
        self._toast_lb.setText(msg)
        self._toast_lb.adjustSize()
        d=self._display.mapTo(self.centralWidget(),QPoint(0,0))
        self._toast_lb.move(d.x()+self._display.width()-self._toast_lb.width()-18, d.y()+8)
        self._toast_lb.raise_()
        self._toast_lb.show()
        self._toast_timer.start(1600)

    # ===== 窗口样式 =====
    def _set_style(self):
        self.setStyleSheet(f"QMainWindow{{background:{C['win']};}}")

    # ===== 构建 UI =====
    def _build_ui(self):
        from siui.components.label import SiLabelRefactor
        from siui.gui import SiFont
        cw=QWidget(self); self.setCentralWidget(cw)
        v=QVBoxLayout(cw); v.setContentsMargins(18,12,18,16); v.setSpacing(8)

        # 标题栏
        h=QWidget(); hl=QHBoxLayout(h); hl.setContentsMargins(0,0,0,0)
        self._title_label=SiLabelRefactor(self)
        self._title_label.setText(f"<b>{self.APP}</b>  <span style='color:{C['sub']};font-weight:400'>Programmer</span>")
        self._title_label.setFont(SiFont.getFont(size=14)); self._title_label.setTextColor(C["title"])
        hl.addWidget(self._title_label); hl.addStretch()
        self._version_label=SiLabelRefactor(self); self._version_label.setText(self.VER)
        self._version_label.setFont(SiFont.getFont(size=10)); self._version_label.setTextColor(C["ver"]); hl.addWidget(self._version_label)
        self._version_label.setCursor(Qt.PointingHandCursor)
        self._version_label.mouseReleaseEvent = lambda e: self._show_about() if e.button()==Qt.LeftButton else None
        self._help_btn=QPushButton("?")
        self._help_btn.setFixedSize(24,24); self._help_btn.setFont(self._si_font(12))
        self._help_btn.setToolTip("快捷键与操作说明 (F1)")
        self._help_btn.setStyleSheet(f"QPushButton{{background:transparent;color:{C['rad_off']};border:none;border-radius:5px;font-weight:600;}}QPushButton:hover{{background:{C['aux_bg']};color:{C['title']};}}")
        self._help_btn.clicked.connect(self._show_help)
        hl.addWidget(self._help_btn)
        self._theme_btn=QPushButton("◐")
        self._theme_btn.setFixedSize(24,24); self._theme_btn.setFont(self._si_font(12))
        self._theme_btn.setToolTip("切换亮色 / 深色主题")
        self._theme_btn.setStyleSheet(f"QPushButton{{background:transparent;color:{C['rad_off']};border:none;border-radius:5px;}}QPushButton:hover{{background:{C['aux_bg']};color:{C['title']};}}")
        self._theme_btn.clicked.connect(self._show_theme_menu)
        hl.addWidget(self._theme_btn)
        v.addWidget(h)

        # 进制栏
        tb=QWidget(); tbl=QHBoxLayout(tb); tbl.setContentsMargins(0,0,0,0)
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
        tbl.addSpacing(7)
        tbl.addWidget(self._vsep())
        tbl.addSpacing(7)
        from siui.components.widgets.line_edit import SiLineEdit
        self._mask_le=SiLineEdit(self)
        self._mask_le.lineEdit().setPlaceholderText("Mask")
        self._mask_le.lineEdit().setToolTip("支持 0x、0b、0o、十进制或无前缀十六进制")
        self._mask_le.setFixedWidth(86)
        self._mask_le.lineEdit().textChanged.connect(self._on_mask_changed)
        tbl.addWidget(self._mask_le)
        v.addWidget(tb)

        # 显示
        self._display=SiLabelRefactor(self); self._display.setMinimumHeight(92)
        self._display.setBackgroundColor(C["dsp_bg"]); self._display.setBorderRadius(16)
        self._display.setAlignment(Qt.AlignRight|Qt.AlignBottom)
        self._display.setFont(SiFont.getFont(size=34)); self._display.setTextColor(C["dsp_fg"])
        self._display.setText("0"); self._display.setContentsMargins(16,12,16,12); v.addWidget(self._display)
        dsp_shadow=QGraphicsDropShadowEffect(self)
        dsp_shadow.setBlurRadius(18); dsp_shadow.setOffset(0,3); dsp_shadow.setColor(QColor(80,90,120,55))
        self._display.setGraphicsEffect(dsp_shadow)
        rf_shadow=QGraphicsDropShadowEffect(self)
        rf_shadow.setBlurRadius(10); rf_shadow.setOffset(0,2); rf_shadow.setColor(QColor(80,90,120,35))
        rf.setGraphicsEffect(rf_shadow)
        # 显示区左下角: 当前 pending 表达式 (如 "123 +")
        self._expr_label=QLabel(self._display)
        self._expr_label.setStyleSheet(f"color:{C['sub']};font-size:13px;font-weight:600;")
        self._expr_label.setAlignment(Qt.AlignLeft|Qt.AlignBottom)
        self._expr_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._display.installEventFilter(self)
        self._display.setContextMenuPolicy(Qt.CustomContextMenu)
        self._display.customContextMenuRequested.connect(self._show_display_menu)

        # 独立表达式栏：不改变传统按键计算状态
        expr_bar=QWidget(); expr_l=QHBoxLayout(expr_bar); expr_l.setContentsMargins(2,0,2,0); expr_l.setSpacing(6)
        expr_tag=QLabel("Expr"); expr_tag.setStyleSheet(f"color:{C['rad_on']};font-size:10px;font-weight:600;")
        self._expression_input=QLineEdit(self)
        self._expression_input.setPlaceholderText("(0x20 << 3) | 0x07")
        self._expression_input.setClearButtonEnabled(True)
        self._expression_input.setToolTip("支持括号、0x/0b/0o 和 + - * / % & | ^ ~ << >>")
        self._expression_input.setStyleSheet(f"QLineEdit{{background:{C['aux_bg']};color:{C['title']};border:1px solid {C['tb_bdr']};border-radius:7px;padding:4px 8px;}}QLineEdit:focus{{border-color:{C['rad_on']};}}")
        self._expression_input.returnPressed.connect(self._evaluate_expression)
        expr_go=QPushButton("="); expr_go.setFixedSize(30,26); expr_go.clicked.connect(self._evaluate_expression)
        expr_go.setToolTip("计算表达式")
        expr_l.addWidget(expr_tag); expr_l.addWidget(self._expression_input,1); expr_l.addWidget(expr_go)
        v.addWidget(expr_bar)

        # Bit
        self._bit_indicator=BitGlow(self); v.addWidget(self._bit_indicator)
        self._bit_indicator.valueChanged.connect(self._on_bit_click)

        # 辅助 — 2×2 多进制同步显示 (点击复制对应进制值)
        self._aux_labels={}
        aw=QWidget(); al=QVBoxLayout(aw); al.setContentsMargins(0,0,0,0); al.setSpacing(5)
        for row_nm in (("DEC","HEX"),("OCT","BIN")):
            rw=QWidget(); rl=QHBoxLayout(rw); rl.setContentsMargins(0,0,0,0); rl.setSpacing(6)
            for nm in row_nm:
                lb=QLabel(self)
                lb.setTextFormat(Qt.RichText)
                lb.setStyleSheet(f"background:{C['aux_bg']};border-radius:8px;padding:0 12px 0 12px;")
                fsize=10 if nm=="BIN" else 12
                lb.setFont(SiFont.getFont(size=fsize))
                lb.setMinimumHeight(30); lb.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
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
        grid=QWidget(); gl=QVBoxLayout(grid); gl.setContentsMargins(0,0,0,0); gl.setSpacing(5)
        for rd in rows:
            rw=QWidget(); rl=QHBoxLayout(rw); rl.setContentsMargins(0,0,0,0); rl.setSpacing(5)
            for txt,sty,cb in rd:
                btn=BFButton(txt,sty,self); btn.clicked.connect(cb)
                rl.addWidget(btn); self._buttons.append(btn)
                if txt in "0123456789ABCDEF": self._digit_btns[txt]=btn
                if txt in OP_TXT: self._op_btns[OP_TXT[txt]]=btn
            gl.addWidget(rw)
        v.addWidget(grid,1)

        # 提示
        self._hint_label=SiLabelRefactor(self)
        self._hint_label.setText(self.HINT)
        self._hint_label.setFont(SiFont.getFont(size=10)); self._hint_label.setTextColor(C["hint"])
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
    def _vsep(self):
        w=QWidget(); w.setFixedSize(1,16)
        w.setStyleSheet(f"background:{C['tb_bdr']};")
        return w

    def eventFilter(self,obj,ev):
        if obj is self._display and ev.type()==QEvent.Resize:
            m=self._display.contentsMargins()
            self._expr_label.setGeometry(m.left(), 0,
                self._display.width()-m.left()-m.right(), self._display.height()-6)
        return super().eventFilter(obj,ev)

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

    def _show_theme_menu(self):
        m=QMenu(self)
        light=m.addAction("亮色主题")
        dark=m.addAction("深色主题")
        act=m.exec_(self._theme_btn.mapToGlobal(self._theme_btn.rect().bottomLeft()))
        if act==light: self._set_theme("light")
        elif act==dark: self._set_theme("dark")

    def _set_theme(self,theme):
        if theme==self._theme: return
        expression=self._expression_input.text()
        self._theme=theme; self._apply_theme_colors(); self._set_style()
        old=self.takeCentralWidget()
        if old is not None: old.deleteLater()
        self._aux_last={}; self._expr_last=""; self._lock_style_state=None; self._display_font_size=None
        self._build_ui(); self._expression_input.setText(expression); self._refresh_display()
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
        m=QMenu(self)
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
        if on: return (f"QPushButton{{background:{C['rad_on']};color:#fff;border:none;"
                       f"border-radius:7px;font-weight:600;}}"
                       f"QPushButton:hover{{background:{C['rad_on']};}}")
        return (f"QPushButton{{background:transparent;color:{C['rad_off']};border:none;"
                f"border-radius:7px;font-weight:600;}}"
                f"QPushButton:hover{{color:{C['title']};}}")

    @staticmethod
    def _lock_btn_style(checked):
        if checked:
            return (f"QPushButton{{background:{C['rad_on']};color:#fff;border:none;"
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
        m=QMenu(self)
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
        ti=QLabel("<b style='font-size:20px;color:#6e40c9;'>BitForge</b>")
        ti.setAlignment(Qt.AlignCenter)
        l.addWidget(ti)
        vl=QLabel(f"v{self.VER}" if not self.VER.startswith("v") else self.VER)
        vl.setAlignment(Qt.AlignCenter); vl.setStyleSheet(f"font-size:13px;color:{C['sub']};margin-bottom:8px;")
        l.addWidget(vl)
        for t in ["Programmer Calculator",""]:
            lb=QLabel(t); lb.setAlignment(Qt.AlignCenter); lb.setStyleSheet(f"font-size:12px;color:{C['sub']};")
            l.addWidget(lb)
        gl=QLabel("<a href='#' style='color:#6e40c9;font-size:13px;text-decoration:none;'>github.com/Hush-xv/BitForge</a>")
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
        title=QLabel("<b style='font-size:18px;color:#6e40c9;'>快速使用</b>")
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
        if on: return (f"QPushButton{{background:{C['rad_on']};color:#fff;border:none;border-radius:7px;}}"
                       f"QPushButton:hover{{background:{C['rad_on']};}}")
        return (f"QPushButton{{background:transparent;color:{C['rad_off']};border:none;border-radius:7px;}}"
                f"QPushButton:hover{{color:{C['title']};}}")

    # ===== 复制 / 粘贴 / 历史 =====
    def _copy_text(self,text,label):
        QApplication.clipboard().setText(text)
        self._toast(f"已复制 {label} {text}")
        dlog("copy", label, text)

    def _copy_current(self):
        self._copy_text(self._display_value,"当前值")

    def _copy_radix(self,name):
        self._copy_text(self._aux_value(name),name)

    def _set_error(self,message):
        self._error=True; self._pending=None; self._last_op=None
        self._value_anim.stop(); self._ani_running=False
        self._set_active_op(None)
        self._display.setText("Error"); self._display.setTextColor(C["dsp_neg"])
        self._toast(message)
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
            self._toast("无法识别剪贴板数值")
            dlog("paste parse failed:", text)
            return
        self._load_value(v)
        self._toast(f"已粘贴 {text}")
        dlog("paste", text, "->", hex(self._value))

    def _evaluate_expression(self):
        text=self._expression_input.text().strip()
        bits=self._bit_width if self._locked else 64
        try: value=evaluate_expression(text,bits)
        except ValueError as exc:
            self._toast(f"表达式错误：{exc}")
            dlog("expression failed:", text, exc)
            return
        if self._error: self._error=False
        if not self._locked: self._bit_width=self._calc_bw(value)
        self._value=clamp(value,self._bit_width); self._entry=self._format_entry(self._value)
        self._new_entry=True; self._pending=None; self._last_op=None
        self._set_active_op(None); self._remember(self._value); self._refresh_display()
        self._toast("表达式已计算")
        dlog("expression", text, "->", hex(self._value), "bits", self._bit_width)

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
        m=QMenu(self)
        acts=[]
        for v in self._history:
            acts.append(m.addAction(f"{v}   0x{v:X}"))
        m.addSeparator()
        a_clr=m.addAction("清空历史")
        act=m.exec_(self._hist_btn.mapToGlobal(self._hist_btn.rect().bottomLeft()))
        if act is None: return
        if act==a_clr:
            self._history=[]; self._toast("历史已清空")
        else:
            self._load_value(self._history[acts.index(act)])
            self._toast(f"已载入 0x{self._value:X}")

    def _show_tools(self):
        m=QMenu(self)
        a_rol=m.addAction("循环左移  ROL")
        a_ror=m.addAction("循环右移  ROR")
        a_swap=m.addAction("字节交换  Byte Swap")
        m.addSeparator()
        a_extract=m.addAction("提取位域…")
        a_write=m.addAction("写入位域…")
        sign_menu=m.addMenu("符号扩展")
        sign_actions={b:sign_menu.addAction(f"从 {b} bit 扩展")
                      for b in (8,16,32) if b<self._bit_width}
        act=m.exec_(self._tools_btn.mapToGlobal(self._tools_btn.rect().bottomLeft()))
        if act==a_rol: self._apply_operator("rol")
        elif act==a_ror: self._apply_operator("ror")
        elif act==a_swap: self._apply_tool_value(byte_swap(self._value,self._bit_width),"字节交换")
        elif act==a_extract: self._extract_field()
        elif act==a_write: self._write_field()
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
        self._toast(f"{label} · {self._bit_width}b")
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
        if op=="lsh": return l<<r
        if op=="rsh": return l>>r
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
        self._display.setTextColor(C["dsp_neg"] if (s<0 and self._radix==10 and self._signed) else C["dsp_fg"])
        self._bit_indicator.set_val(self._value,self._bit_width)
        bw_text=f"{self._bit_width}b"
        if self._bit_width_lb.text()!=bw_text: self._bit_width_lb.setText(bw_text)
        # 位宽标签/锁按钮样式 — 仅锁定状态变化时刷新, 避免每次按键重刷样式表
        if self._locked != self._lock_style_state:
            self._lock_style_state=self._locked
            self._lock_btn.setChecked(self._locked)
            self._lock_btn.setStyleSheet(self._lock_btn_style(self._locked))
            self._bit_width_lb.setStyleSheet(f"color:{C['rad_on'] if self._locked else C['sub']};padding:0 6px 0 2px;")
        # 多进制辅助行 — 内容不变时跳过 setText, 避免富文本重复解析
        for name in ("DEC","HEX","OCT","BIN"):
            html=(f"<span style='color:{C['rad_on']};font-size:9px;font-weight:600'>{name}</span>"
                  f"&nbsp;&nbsp;"
                  f"<span style='color:{C['title']};font-weight:600'>{self._aux_value(name)}</span>")
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

    def _on_bit_click(self,v):
        if self._error: self._error=False
        self._value=clamp(v,64); self._entry=self._format_entry(self._value); self._pending=None
        self._set_active_op(None)
        dlog("bit click ->", hex(self._value))
        self._refresh_display()

    def _on_mask_changed(self,text):
        if not text.strip():
            self._bit_indicator.set_mask(0)
            return
        t=text.strip()
        try:
            if t[:2].lower()=="0x": m=int(t,16)
            elif t[:2].lower()=="0b": m=int(t,2)
            elif t[:2].lower()=="0o": m=int(t,8)
            elif any(c in "abcdefABCDEF" for c in t): m=int(t,16)
            else: m=int(t,10)
            self._bit_indicator.set_mask(clamp(m,64))
        except ValueError:
            dlog("mask parse failed:", text)
            self._toast("掩码格式: 0x / 0b / 0o / 十进制")

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
    w=BitForge(); w.show()
    # 确保应用图标
    ico=QIcon(os.path.join(os.path.dirname(__file__),"bitforge.ico"))
    app.setWindowIcon(ico)
    # 立即释放图标包内存 (~50MB, 5410 个 SVG)
    from siui.core import SiGlobal
    if hasattr(SiGlobal.siui,'iconpack') and hasattr(SiGlobal.siui.iconpack,'clear'):
        SiGlobal.siui.iconpack.clear()
    sys.exit(app.exec_())
if __name__=="__main__": main()
