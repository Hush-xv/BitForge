"""BitForge 自绘控件: BFButton / DisplayText / BitGlow / 应用图标。"""
from PyQt5.QtCore import Qt, QRectF, QTimer, QVariantAnimation, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QFontMetrics, QIcon, QPainter, QPainterPath, QPixmap
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QLabel, QSizePolicy, QToolTip, QWidget
from siui.components.button import SiPushButtonRefactor

from .core import clamp
from .render import GROUP_GAP
from .theme import BH, BR, C, IR


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


def make_shadow(widget, blur, dy, alpha):
    """统一投影: 半径/位移/透明度由调用处给值, 颜色固定同一冷灰蓝。"""
    effect=QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur); effect.setOffset(0,dy)
    effect.setColor(QColor(80,90,120,alpha))
    widget.setGraphicsEffect(effect)
    return effect

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
        self._ripples = []   # 按压涟漪: {anim,pos,radius,alpha}
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
        if self._ripples:
            # 涟漪: 圆形扩散, 裁剪在圆角矩形内
            path=QPainterPath(); path.addRoundedRect(rect,BR,BR)
            p.setClipPath(path)
            for entry in self._ripples:
                base=QColor(255,255,255) if not self._dim else QColor(0,0,0)
                base.setAlpha(int(entry["alpha"]))
                p.setPen(Qt.NoPen); p.setBrush(base)
                p.drawEllipse(entry["pos"], entry["radius"], entry["radius"])
            p.setClipping(False)
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
        if e.button()==Qt.LeftButton: self._start_ripple(e.pos())
        super().mousePressEvent(e)

    def _start_ripple(self,pos):
        """按压涟漪: 半径扩散 + 透明度衰减, 380ms 后自动移除。"""
        r_max=(self.width()**2+self.height()**2)**0.5
        anim=QVariantAnimation(self); anim.setDuration(380)
        anim.setStartValue(0.0); anim.setEndValue(1.0)
        entry={"anim":anim,"pos":pos,"radius":0.0,"alpha":90.0}
        def step(v):
            entry["radius"]=r_max*float(v); entry["alpha"]=90.0*(1.0-float(v)); self.update()
        def done():
            if entry in self._ripples: self._ripples.remove(entry)
            self.update()
        anim.valueChanged.connect(step); anim.finished.connect(done)
        self._ripples.append(entry); anim.start()

    def mouseReleaseEvent(self,e):
        self._pressed=False; self.update()
        super().mouseReleaseEvent(e)

    def set_dimmed(self, d: bool):
        if d != self._dim: self._dim = d; self._paint()


class DisplayText(QLabel):
    """Right-aligned result label with deterministic byte-group gaps."""
    GROUP_GAP=GROUP_GAP   # 与渲染层同源 (bitforge/render.py)

    def __init__(self,parent=None):
        super().__init__(parent)
        self._text_color=QColor(C["dsp_fg"])
        self._groups=None

    def setTextColor(self,color):
        self._text_color=QColor(color); self.update()

    def setGroupedText(self,prefix,groups,accessible_text):
        self._groups=(prefix,tuple(groups))
        super().setText(accessible_text)
        self.update()

    def setText(self,text):
        self._groups=None
        super().setText(text)

    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.TextAntialiasing)
        p.setFont(self.font()); p.setPen(self._text_color)
        if self._groups:
            prefix,groups=self._groups; fm=QFontMetrics(self.font())
            total=fm.horizontalAdvance(prefix)+sum(fm.horizontalAdvance(group) for group in groups)
            total+=self.GROUP_GAP*(len(groups)-1)
            rect=self.contentsRect(); x=rect.right()-total+1; y=rect.bottom()-fm.descent()
            p.drawText(x,y,prefix); x+=fm.horizontalAdvance(prefix)
            for index,group in enumerate(groups):
                p.drawText(x,y,group); x+=fm.horizontalAdvance(group)
                if index<len(groups)-1: x+=self.GROUP_GAP
        else:
            p.drawText(self.contentsRect(),self.alignment(),self.text())
        p.end()


# =====================================================================
#  Bit 指示器 (带位号标签)
#  - QPixmap 缓存消除鼠标滑动卡顿
#  - 标签样式: 位号显示在位内部
# =====================================================================
class BitGlow(QWidget):
    valueChanged = pyqtSignal(object)
    selectionChanged = pyqtSignal(object)
    M=8; GAP=3; GGAP=12
    SINGLE_ROW_HEIGHT=28

    def __init__(self, parent=None):
        super().__init__(parent)
        # Keep a 64-bit-sized slot at every width so content below never shifts.
        self._value=0; self._bits=32; self.setFixedHeight(82)
        self._cache=None; self._dirty=True
        self._font=QFont("Consolas",9); self._mask=0
        self._sel=None; self._anchor=None   # 位域选择: (lo,hi) 闭区间 / 拖拽锚点
        self._flash={}                       # 位翻转闪烁: bit → 剩余帧数
        self._flash_timer=QTimer(self); self._flash_timer.setInterval(40)
        self._flash_timer.timeout.connect(self._flash_tick)
        self.setMouseTracking(True)

    def _flash_tick(self):
        if not self._flash:
            self._flash_timer.stop(); return
        for bit in list(self._flash):
            self._flash[bit]-=1
            if self._flash[bit]<=0: del self._flash[bit]
        self._dirty=True; self.update()

    def _start_flash(self,old,new):
        changed=(old^new) & ((1<<self._bits)-1)
        if not changed: return
        bit=0
        while changed>>bit:
            if (changed>>bit)&1: self._flash[bit]=6   # 6 帧 ≈ 240ms
            bit+=1
        if not self._flash_timer.isActive(): self._flash_timer.start()

    def set_val(self,value,bits):
        if self._value==value and self._bits==bits: return
        if bits==self._bits: self._start_flash(self._value,value)
        self._value=value; self._bits=bits
        if self._sel is not None and self._sel[1]>=bits: self.clear_selection()
        self._dirty=True; self.update()

    def set_mask(self,m):
        if self._mask==m: return
        self._mask=m; self._dirty=True; self.update()

    @property
    def mask(self):
        """当前掩码 (只读视图, 供主窗口读取)。"""
        return self._mask

    @property
    def selection(self):
        """当前位域选择 (lo,hi) 或 None (只读视图)。"""
        return self._sel

    def resizeEvent(self,e):
        self._dirty=True; super().resizeEvent(e)

    def _single_row_top(self):
        """Keep 8/16/32-bit cells vertically centred in the reserved map slot."""
        return max(2,(self.height()-self.SINGLE_ROW_HEIGHT)//2)

    def _bit_at(self,x,y):
        w=max(self.width(),1); m=self.M; gap=self.GAP; ggap=self.GGAP
        cols=32 if self._bits>32 else self._bits
        grps=cols//8; tw=w-2*m
        bw=(tw-(grps-1)*ggap-(cols-grps)*gap)/cols; bw=max(bw,7)

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
            # Single-row maps are centered in the fixed 64-bit slot.
            top=self._single_row_top()
            if y<top or y>top+self.SINGLE_ROW_HEIGHT: return None
            bit_off=0

        grp_total=8*bw+7*gap+ggap; rel_x=x-m
        if rel_x<0: return None
        gi=int(rel_x//grp_total); inner_x=rel_x-gi*grp_total
        bi=int(inner_x//(bw+gap))
        # Gaps between cells and byte groups are not clickable targets.
        if gi>=grps or bi>=8 or inner_x-bi*(bw+gap)>=bw: return None
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

    def _draw_cell(self,p,r,txt,bit_idx,on):
        """绘制单个位格: 光晕/底色、Mask 框、位域选区、翻转闪烁 — 两种布局共用。"""
        if on:
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
            p.drawRoundedRect(r,3,3)
        if self._sel and self._sel[0]<=bit_idx<=self._sel[1]:
            sel_fill=QColor(C["op_active"]); sel_fill.setAlpha(46)
            p.setBrush(sel_fill); p.setPen(QColor(C["op_active"]))
            p.drawRoundedRect(r,3,3)
        if bit_idx in self._flash:
            fl=QColor("#FFFFFF"); fl.setAlpha(30*self._flash[bit_idx]//6)
            p.setBrush(fl); p.setPen(Qt.NoPen)
            p.drawRoundedRect(r,3,3)

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
                pt=8 if bw>=12 else(7 if bw>=9 else 6)
                p.setFont(QFont("Consolas",pt))
                x=m; bit_idx=half-1+bo
                bh=mid-18  # bit rect height per row
                for g in gs:
                    for ch in g:
                        r=QRectF(x,y_off+10,bw,bh); txt=f"{bit_idx:>2d}"
                        self._draw_cell(p,r,txt,bit_idx,ch=="1")
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
            pt=8 if bw>=12 else(7 if bw>=9 else 6)
            p.setFont(QFont("Consolas",pt))
            x=m; y=self._single_row_top()-2; bit_idx=self._bits-1
            for g in gs:
                for ch in g:
                    txt=f"{bit_idx:>2d}"; r=QRectF(x,y+2,bw,28)
                    self._draw_cell(p,r,txt,bit_idx,ch=="1")
                    x+=bw+gap; bit_idx-=1
                x+=ggap-gap
        p.setFont(self._font); p.end(); self._dirty=False
