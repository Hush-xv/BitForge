"""
BitForge — Programmer Calculator (Fast Edition)
================================================
基于 PyQt5 + SiliconUI · 亮色主题 · 无主题切换 · 无图标加载

运行: python bitforge.py
"""

import sys

from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QKeyEvent, QPainter, QPixmap, QRadialGradient
from PyQt5.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QMainWindow,
    QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from siui.components.button import SiPushButtonRefactor
from siui.gui import SiFont

# =====================================================================
#  数学工具
# =====================================================================
ALL_DIGITS = "0123456789ABCDEF"
BIT_MASKS = {8: 0xFF, 16: 0xFFFF, 32: 0xFFFFFFFF, 64: (1 << 64) - 1}
def clamp(v, b): return v & BIT_MASKS[b] if b != 64 else v & BIT_MASKS[64]
def to_signed(v, b):
    u = clamp(v, b)
    if b == 64: return u - (1 << 64) if u >= (1 << 63) else u
    h = 1 << (b - 1); return u - (1 << b) if u >= h else u

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
    "dim_bg":  "#ccd0d8",
    "dim_fg":  "#a0a4ae",
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
    "glow":    QColor(140, 80, 200, 50),
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
        "bs":   ("bs_bg","bs_fg"),
    }
    DIMS  = {"d": ("dim_bg","dim_fg")}

    def __init__(self, text, style="d", parent=None):
        super().__init__(parent)
        self._sty = style
        self._k = self.STYLES[style]
        self._dim = False
        self.setText(text)
        self.setFont(SiFont.getFont(size=15))
        self.setMinimumSize(58, 46)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._paint()

    def _paint(self):
        k = self.DIMS.get(self._sty, self._k) if self._dim else self._k
        bg = QColor(C[k[0]]); fg = QColor(C[k[1]])
        sd = self.style_data
        sd.button_color = bg; sd.text_color = fg
        sd.background_color = QColor(0, 0, 0, 0)
        sd.border_radius = BR; sd.border_inner_radius = IR; sd.border_height = BH
        # 增强悬停效果: 浅色按钮深色叠加, 深色按钮(等号)浅色叠加
        if self._dim:
            sd.idle_color = QColor(0, 0, 0, 0)
            sd.hover_color = QColor(0, 0, 0, 20)
        elif self._k == ("eq_bg", "eq_fg"):
            sd.idle_color = QColor(0, 0, 0, 0)
            sd.hover_color = QColor(255, 255, 255, 55)
        else:
            sd.idle_color = QColor(0, 0, 0, 0)
            sd.hover_color = QColor(0, 0, 0, 55)
        self.update()

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
        self._v=0; self._b=32; self.setFixedHeight(46)
        self._cache=None; self._bw_cache=None; self._dirty=True
        self._font=QFont("Consolas",9)

    def set_val(self,v,b):
        if self._v==v and self._b==b: return
        self._v=v; self._b=b
        self.setFixedHeight(82 if b>32 else 46)
        self._dirty=True; self.update()

    def resizeEvent(self,e):
        self._dirty=True; super().resizeEvent(e)

    def mouseReleaseEvent(self,e):
        if e.button()!=Qt.LeftButton: return
        x,y=e.x(),e.y(); bw=self._bw_cache
        if bw is None: return
        m=self.M; gap=self.GAP; ggap=self.GGAP

        if self._b>32:
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
        bit_pos=(self._b-1 if self._b<=32 else 31)-(gi*8+bi)+bit_off
        if bit_pos<0 or bit_pos>=self._b: return
        self.valueChanged.emit(self._v^(1<<bit_pos))

    def paintEvent(self,e):
        if self._dirty or self._cache is None:
            self._rebuild()
        p=QPainter(self); p.drawPixmap(0,0,self._cache)

    def _rebuild(self):
        w=max(self.width(),1); h=self.height()
        self._cache=QPixmap(w,h); self._cache.fill(Qt.transparent)
        p=QPainter(self._cache); p.setRenderHint(QPainter.Antialiasing)
        u=clamp(self._v,self._b); s=bin(u)[2:].zfill(self._b)
        m=self.M; gap=self.GAP; ggap=self.GGAP

        if self._b > 32:
            half=self._b//2; mid=h//2
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
                            gl=QRadialGradient(r.center().x(),r.center().y(),bw*1.1)
                            gl.setColorAt(0,C["glow"]); gl.setColorAt(0.5,QColor(200,150,240,20))
                            gl.setColorAt(1,Qt.transparent)
                            p.setBrush(gl); p.setPen(Qt.NoPen)
                            p.drawRoundedRect(r.adjusted(-3,-3,3,3),5,5)
                            p.setBrush(QColor(C["bit_on"])); p.setPen(Qt.NoPen)
                            p.drawRoundedRect(r,3,3)
                            p.setPen(QColor("#ffffff")); p.drawText(r,Qt.AlignCenter,txt)
                        else:
                            p.setPen(QColor(C["bit_off"])); p.drawText(r,Qt.AlignCenter,txt)
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
            gs=[s[i:i+8] for i in range(0,self._b,8)]
            tw=w-2*m
            bw=(tw-(len(gs)-1)*ggap-(self._b-len(gs))*gap)/self._b; bw=max(bw,7)
            self._bw_cache=bw
            pt=8 if bw>=12 else(7 if bw>=9 else 6)
            p.setFont(QFont("Consolas",pt))
            x=m; y=14; bit_idx=self._b-1
            for g in gs:
                for ch in g:
                    txt=f"{bit_idx:>2d}"; r=QRectF(x,y+2,bw,h-18)
                    if ch=="1":
                        gl=QRadialGradient(r.center().x(),r.center().y(),bw*1.1)
                        gl.setColorAt(0,C["glow"]); gl.setColorAt(0.5,QColor(200,150,240,20))
                        gl.setColorAt(1,Qt.transparent)
                        p.setBrush(gl); p.setPen(Qt.NoPen)
                        p.drawRoundedRect(r.adjusted(-3,-3,3,3),5,5)
                        p.setBrush(QColor(C["bit_on"])); p.setPen(Qt.NoPen)
                        p.drawRoundedRect(r,3,3)
                        p.setPen(QColor("#ffffff")); p.drawText(r,Qt.AlignCenter,txt)
                    else:
                        p.setPen(QColor(C["bit_off"])); p.drawText(r,Qt.AlignCenter,txt)
                    x+=bw+gap; bit_idx-=1
                x+=ggap-gap
        p.setFont(self._font); p.end(); self._dirty=False


# =====================================================================
#  主窗口
# =====================================================================
class BitForge(QMainWindow):
    APP = "BitForge"; VER = "v1.5-preview"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{self.APP} · Programmer Calculator")
        self.setMinimumSize(540, 660); self.resize(560, 700)
        self.setFocusPolicy(Qt.StrongFocus)
        self._set_style()
        self._v=0; self._d="0"; self._r=10; self._bw=8
        self._n=True; self._signed=False; self._p=None; self._e=False
        self._b(); self._rnd()

    # ===== 窗口样式 =====
    def _set_style(self):
        self.setStyleSheet(f"QMainWindow{{background:{C['win']};}}")

    # ===== 构建 UI =====
    def _b(self):
        from siui.components.label import SiLabelRefactor
        from siui.gui import SiFont
        cw=QWidget(self); self.setCentralWidget(cw)
        v=QVBoxLayout(cw); v.setContentsMargins(16,10,16,14); v.setSpacing(7)

        # 标题栏
        h=QWidget(); hl=QHBoxLayout(h); hl.setContentsMargins(0,0,0,0)
        self._tl=SiLabelRefactor(self)
        self._tl.setText(f"<b>{self.APP}</b>  <span style='color:{C['sub']};font-weight:400'>Programmer</span>")
        self._tl.setFont(SiFont.getFont(size=14)); self._tl.setTextColor(C["title"])
        hl.addWidget(self._tl); hl.addStretch()
        self._vl=SiLabelRefactor(self); self._vl.setText(self.VER)
        self._vl.setFont(SiFont.getFont(size=10)); self._vl.setTextColor(C["ver"]); hl.addWidget(self._vl)
        v.addWidget(h)

        # 进制栏
        tb=QWidget(); tbl=QHBoxLayout(tb); tbl.setContentsMargins(0,0,0,0)
        self._rb={}; rf=QFrame()
        rf.setStyleSheet(f"QFrame{{background:{C['tb_bg']};border-radius:10px;border:1px solid {C['tb_bdr']};}}")
        rl=QHBoxLayout(rf); rl.setContentsMargins(3,3,3,3); rl.setSpacing(0)
        for lb,r in [("HEX",16),("DEC",10),("OCT",8),("BIN",2)]:
            b=QPushButton(lb); b.setCheckable(True); b.setChecked(r==10)
            b.setFont(self._mf(10)); b.setFixedHeight(24); b.setMinimumWidth(44)
            b.setStyleSheet(self._rss(r==10))
            b.clicked.connect(lambda _,rr=r: self._rad(rr))
            rl.addWidget(b); self._rb[r]=b
        tbl.addWidget(rf,1)
        self._sign_btn=QPushButton("\u00b1")
        self._sign_btn.setFont(self._mf(14))
        self._sign_btn.setFixedSize(32,24)
        self._sign_btn.setCheckable(True)
        self._sign_btn.setStyleSheet(self._sign_style(False))
        self._sign_btn.clicked.connect(self._toggle_sign)
        tbl.addWidget(self._sign_btn)
        self._bw_lb=QLabel("8b")
        self._bw_lb.setFont(self._mf(9))
        self._bw_lb.setStyleSheet(f"color:{C['sub']};padding:0 6px 0 2px;")
        self._bw_lb.setAlignment(Qt.AlignCenter)
        tbl.addWidget(self._bw_lb)
        v.addWidget(tb)

        # 显示
        self._dl=SiLabelRefactor(self); self._dl.setMinimumHeight(88)
        self._dl.setBackgroundColor(C["dsp_bg"]); self._dl.setBorderRadius(16)
        self._dl.setAlignment(Qt.AlignRight|Qt.AlignBottom)
        self._dl.setFont(SiFont.getFont(size=34)); self._dl.setTextColor(C["dsp_fg"])
        self._dl.setText("0"); self._dl.setContentsMargins(16,12,16,12); v.addWidget(self._dl)

        # Bit
        self._bi=BitGlow(self); v.addWidget(self._bi)
        self._bi.valueChanged.connect(self._on_bit_click)

        # 辅助 — 2×2 多进制同步显示
        self._ax={}
        aw=QWidget(); al=QVBoxLayout(aw); al.setContentsMargins(0,0,0,0); al.setSpacing(4)
        for row_nm in (("DEC","HEX"),("OCT","BIN")):
            rw=QWidget(); rl=QHBoxLayout(rw); rl.setContentsMargins(0,0,0,0); rl.setSpacing(5)
            for nm in row_nm:
                lb=QLabel(self)
                lb.setTextFormat(Qt.RichText)
                lb.setStyleSheet(f"background:{C['aux_bg']};border-radius:8px;padding:0 10px 0 10px;")
                fsize=10 if nm=="BIN" else 12
                lb.setFont(SiFont.getFont(size=fsize))
                lb.setMinimumHeight(26); lb.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
                rl.addWidget(lb); self._ax[nm]=lb
            al.addWidget(rw)
        v.addWidget(aw)

        # 按钮
        rows=[
            [("AC","ac",lambda: self._ac()),("⌫","bs",lambda: self._bs()),
             ("%","op",lambda: self._op("mod")),("/","op",lambda: self._op("div")),
             ("NOT","bit",lambda: self._op("not"))],
            [("7","d",lambda: self._dig("7")),("8","d",lambda: self._dig("8")),
             ("9","d",lambda: self._dig("9")),("*","op",lambda: self._op("mul")),
             ("AND","bit",lambda: self._op("and"))],
            [("4","d",lambda: self._dig("4")),("5","d",lambda: self._dig("5")),
             ("6","d",lambda: self._dig("6")),("-","op",lambda: self._op("sub")),
             ("OR","bit",lambda: self._op("or"))],
            [("1","d",lambda: self._dig("1")),("2","d",lambda: self._dig("2")),
             ("3","d",lambda: self._dig("3")),("+","op",lambda: self._op("add")),
             ("XOR","bit",lambda: self._op("xor"))],
            [("0","d",lambda: self._dig("0")),("A","d",lambda: self._dig("A")),
             ("B","d",lambda: self._dig("B")),("=","eq",lambda: self._eq()),
             ("<<","bit",lambda: self._op("lsh"))],
            [("C","d",lambda: self._dig("C")),("D","d",lambda: self._dig("D")),
             ("E","d",lambda: self._dig("E")),("F","d",lambda: self._dig("F")),
             (">>","bit",lambda: self._op("rsh"))],
        ]
        self._btns=[]; self._dbt={}
        grid=QWidget(); gl=QVBoxLayout(grid); gl.setContentsMargins(0,0,0,0); gl.setSpacing(5)
        for rd in rows:
            rw=QWidget(); rl=QHBoxLayout(rw); rl.setContentsMargins(0,0,0,0); rl.setSpacing(5)
            for txt,sty,cb in rd:
                btn=BFButton(txt,sty,self); btn.clicked.connect(cb)
                rl.addWidget(btn); self._btns.append(btn)
                if txt in "0123456789ABCDEF": self._dbt[txt]=btn
            gl.addWidget(rw)
        v.addWidget(grid,1)

        # 提示
        self._hl=SiLabelRefactor(self)
        self._hl.setText("KB  0-9 A-F  + - * / % & | ^ ~  Enter  Esc")
        self._hl.setFont(SiFont.getFont(size=10)); self._hl.setTextColor(C["hint"])
        self._hl.setAlignment(Qt.AlignCenter); self._hl.setFixedHeight(18)
        v.addWidget(self._hl)

        # 初始进制状态
        self._ud()

    # ===== 工具 =====
    def _mf(self,s):
        try: return SiFont.getFont(size=s)
        except: f=QFont("Segoe UI",s); f.setHintingPreference(QFont.PreferNoHinting); return f

    def _rss(self,on):
        if on: return (f"QPushButton{{background:{C['rad_on']};color:#fff;border:none;"
                       f"border-radius:7px;font-weight:600;}}"
                       f"QPushButton:hover{{background:{C['rad_on']};}}")
        return (f"QPushButton{{background:transparent;color:{C['rad_off']};border:none;"
                f"border-radius:7px;font-weight:600;}}"
                f"QPushButton:hover{{color:{C['title']};}}")

    def _ud(self):
        for r,b in self._rb.items(): b.setStyleSheet(self._rss(r==self._r))
        vm = {16:"0123456789ABCDEF",10:"0123456789",8:"01234567",2:"01"}[self._r]
        for ch,btn in self._dbt.items(): btn.set_dimmed(ch not in vm)

    def _toggle_sign(self):
        self._signed=not self._signed
        self._sign_btn.setChecked(self._signed)
        self._sign_btn.setStyleSheet(self._sign_style(self._signed))
        self._rnd()

    @staticmethod
    def _sign_style(on):
        if on: return (f"QPushButton{{background:{C['rad_on']};color:#fff;border:none;border-radius:7px;}}"
                       f"QPushButton:hover{{background:{C['rad_on']};}}")
        return (f"QPushButton{{background:transparent;color:{C['rad_off']};border:none;border-radius:7px;}}"
                f"QPushButton:hover{{color:{C['title']};}}")

    # ===== 计算逻辑 =====
    def _rad(self,r):
        if self._r==r or self._e: return
        self._r=r; self._n=False; self._d=self._fmt(self._v); self._ud(); self._rnd()

    def _dig(self,d):
        if self._e: self._ac()
        vm={16:"0123456789ABCDEF",10:"0123456789",8:"01234567",2:"01"}
        if d not in vm.get(self._r,""): return
        mx={2:self._bw,8:22,10:20,16:16}[self._r]
        if self._n: self._d=d; self._n=False
        else:
            if len(self._d)>=mx: return
            self._d+=d
        try: self._v=clamp(int(self._d,self._r),64)
        except ValueError: return
        self._rnd()

    def _ac(self):
        self._v=0; self._d="0"; self._p=None; self._n=True; self._bw=8; self._e=False; self._rnd()

    def _bs(self):
        if self._e: self._ac(); return
        if self._n: return
        if len(self._d)<=1: self._d="0"; self._n=True
        else: self._d=self._d[:-1]
        try: v=int(self._d,self._r) if self._d else 0; self._v=clamp(v,64)
        except ValueError: return
        self._rnd()

    def _op(self,op):
        if self._e: self._ac(); return
        if op=="not": self._v=clamp(~self._v,64); self._d=self._fmt(self._v); self._n=True; self._p=None; self._rnd(); return
        if self._p is not None: self._ev()
        self._p={"op":op,"lhs":self._v}; self._n=True; self._rnd()

    def _eq(self):
        if self._e or self._p is None: return
        self._ev(); self._n=True; self._rnd()

    def _ev(self):
        if self._p is None: return
        op,lhs,rhs=self._p["op"],self._p["lhs"],self._v
        try: r=self._cp(op,lhs,rhs)
        except (ZeroDivisionError,ValueError):
            self._e=True; self._dl.setText("Error"); self._dl.setTextColor(C["dsp_neg"]); return
        self._v=clamp(r,64); self._d=self._fmt(self._v); self._p=None

    @staticmethod
    def _cp(op,l,r):
        if op=="add": return l+r
        if op=="sub": return l-r
        if op=="mul": return l*r
        if op=="div":
            if r==0: raise ZeroDivisionError()
            return int(l/r)
        if op=="mod":
            if r==0: raise ZeroDivisionError()
            return l%r
        if op=="and": return l&r
        if op=="or":  return l|r
        if op=="xor": return l^r
        if op=="lsh": return l<<r
        if op=="rsh": return l>>r
        return l

    def _fmt(self,v):
        u=clamp(v,self._bw)
        if self._r==16: return format(u,"X")
        if self._r==8:  return format(u,"o")
        if self._r==2:  return format(u,"b")
        return str(to_signed(u,self._bw))

    def _calc_bw(self,v):
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

    def _rnd(self):
        if self._e: return
        self._bw=max(self._bw,self._calc_bw(self._v)); u=clamp(self._v,self._bw); t=self._fmt(self._v)
        if self._r==16: t="0x"+t
        elif self._r==8: t="0o"+t
        elif self._r==2: t="0b"+t
        elif not self._signed: t=str(u)  # DEC 无符号
        self._dl.setText(t)
        s=to_signed(u,self._bw)
        self._dl.setTextColor(C["dsp_neg"] if (s<0 and self._r==10 and self._signed) else C["dsp_fg"])
        self._bi.set_val(self._v,self._bw)
        self._bw_lb.setText(f"{self._bw}b")
        dec_v=s if self._signed else u
        self._ax["DEC"].setText(f"<span style='color:{C['sub']}'>DEC</span>  <span style='color:{C['dsp_fg']}'>{dec_v}</span>")
        self._ax["HEX"].setText(f"<span style='color:{C['sub']}'>HEX</span>  <span style='color:{C['dsp_fg']}'>0x{format(u,'X')}</span>")
        self._ax["OCT"].setText(f"<span style='color:{C['sub']}'>OCT</span>  <span style='color:{C['dsp_fg']}'>0o{format(u,'o')}</span>")
        self._ax["BIN"].setText(f"<span style='color:{C['sub']}'>BIN</span>  <span style='color:{C['dsp_fg']}'>0b{format(u,'b')}</span>")

    def _on_bit_click(self,v):
        if self._e: self._e=False
        self._v=clamp(v,64); self._d=self._fmt(self._v); self._p=None
        self._rnd()

    # ===== 键盘 =====
    def keyPressEvent(self,e:QKeyEvent):
        k,tx=e.key(),e.text()
        if tx in "0123456789": self._dig(tx); return
        if tx.lower() in "abcdef" and self._r==16: self._dig(tx.upper()); return
        om={Qt.Key_Plus:"add",Qt.Key_Minus:"sub",Qt.Key_Asterisk:"mul",
            Qt.Key_Slash:"div",Qt.Key_Percent:"mod",
            Qt.Key_Ampersand:"and",Qt.Key_Bar:"or",Qt.Key_AsciiCircum:"xor"}
        if k in om: self._op(om[k]); return
        if k in (Qt.Key_Enter,Qt.Key_Return) or tx=="=": self._eq(); return
        if k==Qt.Key_Backspace: self._bs(); return
        if k in (Qt.Key_Escape,Qt.Key_Delete): self._ac(); return
        if k==Qt.Key_AsciiTilde: self._op("not"); return
        if k==Qt.Key_Less: self._op("lsh"); return
        if k==Qt.Key_Greater: self._op("rsh"); return
        super().keyPressEvent(e)


# =====================================================================
def main():
    app=QApplication(sys.argv); app.setApplicationName("BitForge")
    w=BitForge(); w.show()
    # 立即释放图标包内存 (~50MB, 5410 个 SVG)
    from siui.core import SiGlobal
    if hasattr(SiGlobal.siui,'iconpack') and hasattr(SiGlobal.siui.iconpack,'clear'):
        SiGlobal.siui.iconpack.clear()
    sys.exit(app.exec_())
if __name__=="__main__": main()
