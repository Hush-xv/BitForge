"""
BitForge v1.2 — Programmer Calculator
======================================
基于 PyQt5 + SiliconUI。
暗色/亮色主题 · 高对比度显示 · QMenu 设置 · Fluent UI 图标

运行: python bitforge.py
"""

import sys
from PyQt5.QtCore import Qt, QRectF, QPoint
from PyQt5.QtGui import (
    QColor, QFont, QKeyEvent, QPainter, QRadialGradient,
    QPixmap,
)
from PyQt5.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QMainWindow,
    QMenu, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)
from PyQt5.QtSvg import QSvgRenderer

from siui.components.button import SiPushButtonRefactor
from siui.components.label import SiLabelRefactor
from siui.core import SiGlobal
from siui.gui import SiFont

# =====================================================================
BIT_MASKS = {8: 0xFF, 16: 0xFFFF, 32: 0xFFFFFFFF, 64: (1 << 64) - 1}
def clamp(v, b): return v & BIT_MASKS[b] if b != 64 else v & BIT_MASKS[64]
def to_signed(v, b):
    u = clamp(v, b)
    if b == 64: return u - (1 << 64) if u >= (1 << 63) else u
    h = 1 << (b - 1); return u - (1 << b) if u >= h else u

# =====================================================================
#  主题系统 — 暗色文字全面提亮到 #FFFFFF 级别
# =====================================================================
class AppTheme:
    DARK = {
        "name": "Dark",
        "window_bg":      "#0e1117",
        "display_bg":     "#10141c",
        "display_text":   "#FFFFFF",
        "display_neg":    "#ff6b6b",
        "aux_bg":         "#10141c",
        "aux_text":       "#d4d8e0",
        "title_text":     "#e8ecf2",
        "title_sub":      "#808898",
        "ver_text":       "#505868",
        "hint_text":      "#3b4252",
        "toolbar_bg":     "#0d1117",
        "toolbar_border": "#1f2430",
        "toggle_on_bw":   "#282c38",
        "toggle_bw_text": "#d8dce4",
        "toggle_dim":     "#686e7a",
        "toggle_rad_on":  "#6e40c9",
        "toggle_rad_text":"#ffffff",
        "digit_bg":       "#232834",
        "digit_fg":       "#FFFFFF",
        "op_bg":          "#0a1428",
        "op_fg":          "#80c0ff",
        "bit_bg":         "#1a142e",
        "bit_fg":         "#e0c0ff",
        "eq_bg":          "#6e40c9",
        "eq_fg":          "#ffffff",
        "ac_bg":          "#1c0e0d",
        "ac_fg":          "#ff8080",
        "bs_bg":          "#1c160e",
        "bs_fg":          "#f0b060",
        "func_bg":        "#0d1e1b",
        "func_fg":        "#60e090",
        "bit_on":         "#d090f0",
        "bit_off":        "#1e1c25",
        "bit_glow":       QColor(210, 150, 240, 75),
        "menu_bg":        "#191d28",
        "menu_border":    "#2a3040",
        "menu_text":      "#d8dce4",
        "menu_dim":       "#687080",
        "menu_acc":       "#90b0ff",
        "btn_h":          3,
        "btn_r":          10,
        "btn_ir":         8,
    }
    BRIGHT = {
        "name": "Light",
        "window_bg":      "#f0f2f5",
        "display_bg":     "#ffffff",
        "display_text":   "#101216",
        "display_neg":    "#d01020",
        "aux_bg":         "#f6f7fa",
        "aux_text":       "#3a3d48",
        "title_text":     "#181a20",
        "title_sub":      "#687080",
        "ver_text":       "#a0a8b8",
        "hint_text":      "#98a0b0",
        "toolbar_bg":     "#ffffff",
        "toolbar_border": "#d8dce4",
        "toggle_on_bw":   "#e4e8f0",
        "toggle_bw_text": "#282c38",
        "toggle_dim":     "#8890a0",
        "toggle_rad_on":  "#6e40c9",
        "toggle_rad_text":"#ffffff",
        "digit_bg":       "#e8ecf2",
        "digit_fg":       "#181a20",
        "op_bg":          "#dce8ff",
        "op_fg":          "#2050b0",
        "bit_bg":         "#efe8ff",
        "bit_fg":         "#6020a0",
        "eq_bg":          "#6838c8",
        "eq_fg":          "#ffffff",
        "ac_bg":          "#ffe8e6",
        "ac_fg":          "#c02030",
        "bs_bg":          "#fff0e0",
        "bs_fg":          "#c06020",
        "func_bg":        "#e0ffe8",
        "func_fg":        "#108030",
        "bit_on":         "#8040c0",
        "bit_off":        "#d0d4dc",
        "bit_glow":       QColor(140, 80, 200, 50),
        "menu_bg":        "#ffffff",
        "menu_border":    "#d4d8e0",
        "menu_text":      "#282c38",
        "menu_dim":       "#98a0b0",
        "menu_acc":       "#4058d0",
        "btn_h":          2,
        "btn_r":          9,
        "btn_ir":         7,
    }

# =====================================================================
#  BitForge 按钮
# =====================================================================
class BFButton(SiPushButtonRefactor):
    STYLES = {
        "digit":("digit_bg","digit_fg"), "op":("op_bg","op_fg"),
        "bit":("bit_bg","bit_fg"), "eq":("eq_bg","eq_fg"),
        "ac":("ac_bg","ac_fg"), "bs":("bs_bg","bs_fg"),
        "func":("func_bg","func_fg"),
    }
    def __init__(self, text, style="digit", icon_name="", parent=None):
        super().__init__(parent)
        self._keys = self.STYLES.get(style, ("digit_bg","digit_fg"))
        self.setText(text)
        self.setFont(SiFont.getFont(size=15))
        self.setMinimumSize(58, 46)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._iname = icon_name
    def apply_theme(self, t):
        bg, fg = QColor(t[self._keys[0]]), QColor(t[self._keys[1]])
        sd = self.style_data
        sd.button_color = bg; sd.text_color = fg
        sd.background_color = QColor(0, 0, 0, 0)
        sd.border_radius = t["btn_r"]
        sd.border_inner_radius = t["btn_ir"]
        sd.border_height = t["btn_h"]
        if self._iname:
            try:
                svg = SiGlobal.siui.iconpack.getByteArray(self._iname, t["bit_fg"])
                self.setSvgIcon(bytes(svg))
            except Exception: pass

# =====================================================================
#  Bit 指示器
# =====================================================================
class BitGlowIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._v=0; self._b=32; self._on="#d090f0"; self._off="#1e1c25"
        self._glow=QColor(210,150,240,75); self.setFixedHeight(28)
    def set_val(self,v,b): self._v=v; self._b=b; self.update()
    def set_theme(self,t):
        self._on=t["bit_on"]; self._off=t["bit_off"]; self._glow=t["bit_glow"]; self.update()
    def paintEvent(self,e):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        u=clamp(self._v,self._b); s=bin(u)[2:].zfill(self._b)
        m=8; gap=3; ggap=12; tw=self.width()-2*m
        gs=[s[i:i+8] for i in range(0,self._b,8)]
        bw=(tw-(len(gs)-1)*ggap-(self._b-len(gs))*gap)/self._b; bw=max(bw,7)
        f=QFont("Consolas",9); p.setFont(f); x=m
        for g in gs:
            for ch in g:
                r=QRectF(x,4,bw,self.height()-8)
                if ch=="1":
                    gl=QRadialGradient(r.center().x(),r.center().y(),bw*1.1)
                    gl.setColorAt(0,self._glow)
                    gl.setColorAt(0.5,QColor(self._glow.red(),self._glow.green(),self._glow.blue(),self._glow.alpha()//3))
                    gl.setColorAt(1,Qt.transparent)
                    p.setBrush(gl); p.setPen(Qt.NoPen)
                    p.drawRoundedRect(r.adjusted(-3,-3,3,3),5,5)
                    p.setBrush(QColor(self._on)); p.setPen(Qt.NoPen)
                    p.drawRoundedRect(r,3,3)
                    p.setPen(QColor("#0e0c14"))
                    p.drawText(r,Qt.AlignCenter,"1")
                else:
                    p.setPen(QColor(self._off)); p.drawText(r,Qt.AlignCenter,"0")
                x+=bw+gap
            x+=ggap-gap

# =====================================================================
#  主窗口
# =====================================================================
class BitForge(QMainWindow):
    APP = "BitForge"; VER = "v1.3"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{self.APP} . Programmer Calculator")
        self.setMinimumSize(540, 660); self.resize(560, 700)
        self.setFocusPolicy(Qt.StrongFocus)
        self._t = AppTheme.DARK
        self._v=0; self._dsp="0"; self._rad=10; self._bw=32
        self._new=True; self._pend=None; self._err=False
        self._build(); self._apply_theme(); self._render()

    # ===== UI =====

    def _build(self):
        cw=QWidget(self); self.setCentralWidget(cw)
        v=QVBoxLayout(cw); v.setContentsMargins(16,10,16,14); v.setSpacing(7)

        # 标题栏
        h=QWidget(); hl=QHBoxLayout(h); hl.setContentsMargins(0,0,0,0); hl.setSpacing(8)
        try:
            self._ico=SiLabelRefactor(self); self._ico.setFixedSize(24,24)
            svg=SiGlobal.siui.iconpack.getByteArray("ic_fluent_calculator_filled","#d2a8ff")
            px=QPixmap(24,24); px.fill(Qt.transparent)
            pp=QPainter(px); QSvgRenderer(bytes(svg)).render(pp); pp.end()
            self._ico.setPixmap(px); hl.addWidget(self._ico)
        except: pass
        self._ttl=SiLabelRefactor(self)
        self._ttl.setText(f"<b>{self.APP}</b>  <span style='color:#808898;font-weight:400'>Programmer</span>")
        self._ttl.setFont(SiFont.getFont(size=14)); self._ttl.setTextColor("#e8ecf2"); hl.addWidget(self._ttl)
        hl.addStretch()
        self._ver=SiLabelRefactor(self); self._ver.setText(self.VER)
        self._ver.setFont(SiFont.getFont(size=10)); self._ver.setTextColor("#505868"); hl.addWidget(self._ver)

        # 齿轮按钮 — 纯文本，无图标依赖
        self._gear=QPushButton("⚙"); self._gear.setFixedSize(30,30)
        self._gear.setFont(QFont("Segoe UI",14))
        self._gear.setStyleSheet("QPushButton{background:transparent;color:#8a90a0;border:none;}"
                                  "QPushButton:hover{color:#c0c8d8;}")
        self._gear.clicked.connect(self._menu_settings)
        hl.addWidget(self._gear)
        v.addWidget(h)

        # 工具栏
        tb=QWidget(); tbl=QHBoxLayout(tb); tbl.setContentsMargins(0,0,0,0); tbl.setSpacing(6)
        self._rad_btns={}
        self._rdf=rdf=QFrame(); rdf.setObjectName("rdf")
        rdl=QHBoxLayout(rdf); rdl.setContentsMargins(3,3,3,3); rdl.setSpacing(0)
        for lb,r in [("HEX",16),("DEC",10),("OCT",8)]:
            b=QPushButton(lb); b.setCheckable(True); b.setChecked(r==10)
            b.setFont(self._mf(10)); b.setFixedHeight(24); b.setMinimumWidth(44)
            b.clicked.connect(lambda _,rr=r: self._on_radix(rr))
            rdl.addWidget(b); self._rad_btns[r]=b
        tbl.addWidget(rdf,1); v.addWidget(tb)

        # 显示 (用 _dsp_lbl 以免与字符串 _dsp 冲突)
        self._dsp_lbl=SiLabelRefactor(self); self._dsp_lbl.setMinimumHeight(100)
        self._dsp_lbl.setBackgroundColor("#10141c"); self._dsp_lbl.setBorderRadius(16)
        self._dsp_lbl.setAlignment(Qt.AlignRight|Qt.AlignBottom)
        self._dsp_lbl.setFont(SiFont.getFont(size=34)); self._dsp_lbl.setTextColor("#FFFFFF")
        self._dsp_lbl.setText("0"); self._dsp_lbl.setContentsMargins(16,12,16,12); v.addWidget(self._dsp_lbl)

        # Bit指示器
        self._bits=BitGlowIndicator(self); self._bits.setObjectName("bits"); v.addWidget(self._bits)

        # 辅助
        self._aux={}
        aw=QWidget(); al=QHBoxLayout(aw); al.setContentsMargins(0,0,0,0); al.setSpacing(5)
        for nm in ("DEC","HEX","OCT"):
            lb=SiLabelRefactor(self); lb.setBackgroundColor("#10141c"); lb.setBorderRadius(8)
            lb.setFont(SiFont.getFont(size=12)); lb.setTextColor("#d4d8e0")
            lb.setMinimumHeight(30); lb.setAlignment(Qt.AlignCenter)
            al.addWidget(lb); self._aux[nm]=lb
        v.addWidget(aw)

        # 按钮
        rows=[
            [("AC","ac","",lambda: self._on_clear()),
             ("⌫","bs","",lambda: self._on_bs()),
             ("%","op","",lambda: self._on_op("mod")),
             ("/","op","",lambda: self._on_op("div")),
             ("NOT","bit","ic_fluent_arrow_sync_filled",lambda: self._on_op("not"))],
            [("7","d","",lambda: self._on_digit("7")),
             ("8","d","",lambda: self._on_digit("8")),
             ("9","d","",lambda: self._on_digit("9")),
             ("*","op","",lambda: self._on_op("mul")),
             ("AND","bit","ic_fluent_math_symbols_filled",lambda: self._on_op("and"))],
            [("4","d","",lambda: self._on_digit("4")),
             ("5","d","",lambda: self._on_digit("5")),
             ("6","d","",lambda: self._on_digit("6")),
             ("-","op","",lambda: self._on_op("sub")),
             ("OR","bit","ic_fluent_braces_filled",lambda: self._on_op("or"))],
            [("1","d","",lambda: self._on_digit("1")),
             ("2","d","",lambda: self._on_digit("2")),
             ("3","d","",lambda: self._on_digit("3")),
             ("+","op","",lambda: self._on_op("add")),
             ("XOR","bit","ic_fluent_code_filled",lambda: self._on_op("xor"))],
            [("0","d","",lambda: self._on_digit("0")),
             ("A","func","",lambda: self._on_digit("A")),
             ("B","func","",lambda: self._on_digit("B")),
             ("=","eq","ic_fluent_arrow_right_filled",lambda: self._on_eq()),
             ("<<","bit","ic_fluent_arrow_previous_filled",lambda: self._on_op("lsh"))],
            [("C","func","",lambda: self._on_digit("C")),
             ("D","func","",lambda: self._on_digit("D")),
             ("E","func","",lambda: self._on_digit("E")),
             ("F","func","",lambda: self._on_digit("F")),
             (">>","bit","ic_fluent_arrow_next_filled",lambda: self._on_op("rsh"))],
        ]
        self._btns=[]
        grid=QWidget(); gl=QVBoxLayout(grid); gl.setContentsMargins(0,0,0,0); gl.setSpacing(5)
        for rd in rows:
            rw=QWidget(); rl=QHBoxLayout(rw); rl.setContentsMargins(0,0,0,0); rl.setSpacing(5)
            for txt,sty,icon,cb in rd:
                btn=BFButton(txt,sty,icon,self); btn.clicked.connect(cb)
                rl.addWidget(btn); self._btns.append(btn)
            gl.addWidget(rw)
        v.addWidget(grid,1)

        # 提示
        self._hint=SiLabelRefactor(self)
        self._hint.setText("KB  0-9 A-F  + - * / % & | ^ ~  Enter  Esc")
        self._hint.setFont(SiFont.getFont(size=10)); self._hint.setTextColor("#3b4252")
        self._hint.setAlignment(Qt.AlignCenter); self._hint.setFixedHeight(18)
        v.addWidget(self._hint)

    # ===== 设置菜单 (QMenu) =====

    def _menu_settings(self):
        t = self._t
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {t['menu_bg']}; border: 1px solid {t['menu_border']};
                border-radius: 12px; padding: 8px 4px;
            }}
            QMenu::item {{
                color: {t['menu_text']}; padding: 8px 28px 8px 16px;
                font-size: 13px; font-family: 'Segoe UI'; border-radius: 6px; margin: 2px 6px;
            }}
            QMenu::item:selected {{ background: {t['toggle_on_bw']}; color: {t['menu_acc']}; }}
            QMenu::separator {{
                height: 1px; background: {t['menu_border']}; margin: 6px 12px;
            }}
        """)

        # 主题子菜单
        theme_menu = QMenu("主题", menu)
        theme_menu.setStyleSheet(menu.styleSheet())
        dark_action = theme_menu.addAction("● 暗色" if t["name"] == "Dark" else "  暗色")
        light_action = theme_menu.addAction("● 亮色" if t["name"] == "Light" else "  亮色")
        dark_action.triggered.connect(lambda: self._switch_theme(AppTheme.DARK))
        light_action.triggered.connect(lambda: self._switch_theme(AppTheme.BRIGHT))
        menu.addMenu(theme_menu)

        menu.addSeparator()
        ver_action = menu.addAction(f"版本  {self.VER}")
        ver_action.setEnabled(False)
        author_action = menu.addAction("作者  BitForge")
        author_action.setEnabled(False)

        pos = self._gear.mapToGlobal(QPoint(0, self._gear.height()))
        menu.exec_(pos)

    def _switch_theme(self, new_theme):
        if self._t["name"] != new_theme["name"]:
            self._t = new_theme; self._apply_theme()

    # ===== 主题应用 =====

    def _apply_theme(self):
        t = self._t
        self.setStyleSheet(f"QMainWindow{{background:{t['window_bg']};}}")
        self._ttl.setTextColor(t["title_text"])
        self._ttl.setText(f"<b>{self.APP}</b>  <span style='color:{t['title_sub']};font-weight:400'>Programmer</span>")
        self._ver.setTextColor(t["ver_text"])

        bss = f"QFrame{{background:{t['toolbar_bg']};border-radius:10px;border:1px solid {t['toolbar_border']};}}"
        self._rdf.setStyleSheet(bss)
        for r,b in self._rad_btns.items(): b.setStyleSheet(self._ts(r==self._rad))

        self._dsp_lbl.setBackgroundColor(t["display_bg"]); self._dsp_lbl.setTextColor(t["display_text"])
        self._bits.set_theme(t)
        self._bits.setStyleSheet(f"#bits{{background:{t['display_bg']};border-radius:0 0 16px 16px;}}")
        for nm,lb in self._aux.items(): lb.setBackgroundColor(t["aux_bg"]); lb.setTextColor(t["aux_text"])
        for b in self._btns: b.apply_theme(t)
        self._hint.setTextColor(t["hint_text"])
        self._gear.setStyleSheet(f"QPushButton{{background:transparent;color:{t['title_sub']};border:none;font-size:16px;}}"
                                  f"QPushButton:hover{{color:{t['menu_acc']};}}")
        self._render()

    def _ts(self, rad_on=False):
        t=self._t
        if rad_on: return (f"QPushButton{{background:{t['toggle_rad_on']};color:{t['toggle_rad_text']};"
                           f"border:none;border-radius:7px;font-weight:600;}}"
                           f"QPushButton:hover{{background:{t['toggle_rad_on']};}}")
        return (f"QPushButton{{background:transparent;color:{t['toggle_dim']};border:none;"
                f"border-radius:7px;font-weight:600;}}"
                f"QPushButton:hover{{color:{t['toggle_bw_text']};}}")

    def _urd(self):
        for r,b in self._rad_btns.items(): b.setStyleSheet(self._ts(r==self._rad))

    @staticmethod
    def _mf(sz):
        try: return SiFont.getFont(size=sz)
        except: f=QFont("Segoe UI",sz); f.setHintingPreference(QFont.PreferNoHinting); return f

    # ===== 逻辑 =====

    def _on_radix(self,r):
        if self._rad==r or self._err: return
        self._rad=r; self._new=True; self._urd(); self._render()
    def _on_digit(self,d):
        if self._err: self._on_clear()
        vm={16:"0123456789ABCDEFabcdef",10:"0123456789",8:"01234567",2:"01"}
        if d not in vm.get(self._rad,""): return
        mx={2:self._bw,8:22,10:20,16:16}[self._rad]
        if self._new: self._dsp=d; self._new=False
        else:
            if len(self._dsp)>=mx: return
            self._dsp+=d
        try: self._v=clamp(int(self._dsp,self._rad),self._bw)
        except ValueError: return
        self._render()
    def _on_clear(self):
        self._v=0; self._dsp="0"; self._pend=None; self._new=True; self._err=False; self._render()
    def _on_bs(self):
        if self._err: self._on_clear(); return
        if self._new: return
        if len(self._dsp)<=1: self._dsp="0"; self._new=True
        else: self._dsp=self._dsp[:-1]
        try: v=int(self._dsp,self._rad) if self._dsp else 0; self._v=clamp(v,self._bw)
        except ValueError: return
        self._render()
    def _on_op(self,op):
        if self._err: self._on_clear(); return
        if op=="not": self._v=clamp(~self._v,self._bw); self._dsp=self._fmt(self._v); self._new=True; self._pend=None; self._render(); return
        if self._pend is not None: self._eval()
        self._pend={"op":op,"lhs":self._v}; self._new=True; self._render()
    def _on_eq(self):
        if self._err or self._pend is None: return
        self._eval(); self._new=True; self._render()
    def _eval(self):
        if self._pend is None: return
        op,lhs,rhs=self._pend["op"],self._pend["lhs"],self._v
        try: r=self._compute(op,lhs,rhs)
        except (ZeroDivisionError,ValueError):
            self._err=True; self._dsp_lbl.setText("Error"); self._dsp_lbl.setTextColor("#ff6b6b"); return
        self._v=clamp(r,self._bw); self._dsp=self._fmt(self._v); self._pend=None
    @staticmethod
    def _compute(op,lhs,rhs):
        if op=="add": return lhs+rhs
        if op=="sub": return lhs-rhs
        if op=="mul": return lhs*rhs
        if op=="div":
            if rhs==0: raise ZeroDivisionError()
            return int(lhs/rhs)
        if op=="mod":
            if rhs==0: raise ZeroDivisionError()
            return lhs%rhs
        if op=="and": return lhs&rhs
        if op=="or": return lhs|rhs
        if op=="xor": return lhs^rhs
        if op=="lsh": return lhs<<rhs
        if op=="rsh": return lhs>>rhs
        return lhs
    def _fmt(self,val):
        u=clamp(val,self._bw) if self._bw!=64 else val&BIT_MASKS[64]
        if self._rad==16: return format(u,"X")
        if self._rad==8: return format(u,"o")
        if self._rad==2: return format(u,"b")
        return str(to_signed(u,self._bw))
    def _render(self):
        if self._err: return
        t=self._t; u=clamp(self._v,self._bw)
        dt=self._fmt(self._v)
        if self._rad==16: dt="0x"+dt
        elif self._rad==8: dt="0o"+dt
        elif self._rad==2: dt="0b"+dt
        self._dsp_lbl.setText(dt)
        sgn=to_signed(u,self._bw)
        self._dsp_lbl.setTextColor(t["display_neg"] if (sgn<0 and self._rad==10) else t["display_text"])
        self._bits.set_val(self._v,self._bw)
        self._aux["DEC"].setText(f"DEC  {sgn}")
        self._aux["HEX"].setText(f"HEX  0x{format(u,'X')}")
        self._aux["OCT"].setText(f"OCT  0o{format(u,'o')}")

    # ===== 键盘 =====

    def keyPressEvent(self,e:QKeyEvent):
        k,tx=e.key(),e.text()
        if tx in "0123456789": self._on_digit(tx); return
        if tx.lower() in "abcdef" and self._rad==16: self._on_digit(tx.upper()); return
        om={Qt.Key_Plus:"add",Qt.Key_Minus:"sub",Qt.Key_Asterisk:"mul",
            Qt.Key_Slash:"div",Qt.Key_Percent:"mod",
            Qt.Key_Ampersand:"and",Qt.Key_Bar:"or",Qt.Key_AsciiCircum:"xor"}
        if k in om: self._on_op(om[k]); return
        if k in (Qt.Key_Enter,Qt.Key_Return) or tx=="=": self._on_eq(); return
        if k==Qt.Key_Backspace: self._on_bs(); return
        if k in (Qt.Key_Escape,Qt.Key_Delete): self._on_clear(); return
        if k==Qt.Key_AsciiTilde: self._on_op("not"); return
        if k==Qt.Key_Less: self._on_op("lsh"); return
        if k==Qt.Key_Greater: self._on_op("rsh"); return
        super().keyPressEvent(e)

# =====================================================================
def main():
    app=QApplication(sys.argv); app.setApplicationName("BitForge")
    SiGlobal.siui.reloadAllWindowsStyleSheet()
    w=BitForge(); w.show(); sys.exit(app.exec_())
if __name__=="__main__": main()
