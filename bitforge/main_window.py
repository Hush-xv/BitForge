"""BitForge 主窗口: 计算状态、显示刷新、持久化与交互。"""
import json

from PyQt5.QtCore import (Qt, QTimer, QEasingCurve, QVariantAnimation, QEvent,
                          QPoint, QByteArray, QSettings)
from PyQt5.QtGui import QColor, QFont, QFontMetrics, QKeyEvent
from PyQt5.QtWidgets import (
    QApplication, QDialog, QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
    QHBoxLayout, QInputDialog, QLineEdit, QMainWindow, QLabel, QMenu, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from .core import (BIT_MASKS, OP_SYMBOLS, RADIX_DIGITS, byte_swap, clamp, dlog,
                   evaluate_expression, extract_field, parse_number, rotate_left,
                   rotate_right, to_signed, write_field)
from .render import (aux_text, compute_display_model, display_groups, font_size_for,
                     group_display, make_display_font)
from .state import CalculatorState, compute
from .theme import C, DARK_C, LIGHT_C
from .widgets import BFButton, BitGlow, DisplayText, make_app_icon


class BitForge(QMainWindow):
    APP = "BitForge"; VER = "v1.10.0"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{self.APP} · Programmer Calculator")
        self._app_icon=make_app_icon()
        self.setWindowIcon(self._app_icon)
        self.setMinimumSize(540, 720); self.resize(560, 720)
        self.setFocusPolicy(Qt.StrongFocus)
        self._state=CalculatorState()   # 计算状态唯一真相源 (bitforge/state.py)
        self._lock_style_state=None   # 上次刷新时的锁定状态 (样式 guard)
        self._aux_last={}             # 辅助行上次 HTML (setText guard)
        self._expr_last=""            # 表达式行上次文本
        self._display_value="0"       # 未分组的显示值，供复制和右键菜单使用
        self._display_font_size=None
        self._sel_value=None          # 当前选中位域的值 (点击 SEL 标签复制)
        self._persist=True            # 关闭时写 QSettings (测试可关闭)
        self._history=[]              # 最近结果 (最新在前, 上限 10)
        self._expression_history=[]   # 最近表达式（最新在前，上限 5）
        self._settings=QSettings("BitForge","BitForge")
        self._restore_settings()
        self._apply_theme_colors()
        self._set_style()
        self._toast_timer=QTimer(self); self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(self._toast_fade_out)
        self._value_anim=QVariantAnimation(self)
        self._value_anim.setDuration(120)
        self._value_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._value_anim.valueChanged.connect(self._ani_set_text)
        self._ani_last=""; self._ani_running=False
        self._value_anim.finished.connect(lambda: setattr(self,'_ani_running',False))
        self._sys_timer=QTimer(self); self._sys_timer.setInterval(3000)
        self._sys_timer.timeout.connect(self._apply_system_theme)
        self._build_ui()
        if self._saved_mask: self._mask_le.setText(self._saved_mask)
        self._update_layout_density(); self._refresh_display()
        if self._follow_system: self._sys_timer.start()
        self._apply_pin(self._pinned)
        g=self._settings.value("win/geometry")
        if g:
            try: self.restoreGeometry(QByteArray.fromBase64(g.encode()))
            except Exception: pass

    HINT = "KB  0-9 A-F  + - * / % & | ^ ~  Enter  Esc  Tab 切换进制  Ctrl+Z/Y  Ctrl+C/V  F1 帮助"

    # ---- 状态委托: 数据真源在 self._state, 保留旧属性名使窗口代码与测试零改动 ----
    @property
    def _value(self): return self._state.value
    @_value.setter
    def _value(self,v): self._state.value=v

    @property
    def _entry(self): return self._state.entry
    @_entry.setter
    def _entry(self,v): self._state.entry=v

    @property
    def _radix(self): return self._state.radix
    @_radix.setter
    def _radix(self,v): self._state.radix=v

    @property
    def _bit_width(self): return self._state.bit_width
    @_bit_width.setter
    def _bit_width(self,v): self._state.bit_width=v

    @property
    def _new_entry(self): return self._state.new_entry
    @_new_entry.setter
    def _new_entry(self,v): self._state.new_entry=v

    @property
    def _signed(self): return self._state.signed
    @_signed.setter
    def _signed(self,v): self._state.signed=v

    @property
    def _locked(self): return self._state.locked
    @_locked.setter
    def _locked(self,v): self._state.locked=v

    @property
    def _pending(self): return self._state.pending
    @_pending.setter
    def _pending(self,v): self._state.pending=v

    @property
    def _last_op(self): return self._state.last_op
    @_last_op.setter
    def _last_op(self,v): self._state.last_op=v

    @property
    def _error(self): return self._state.error
    @_error.setter
    def _error(self,v): self._state.error=v

    @property
    def _undo_stack(self): return self._state._undo_stack

    @property
    def _redo_stack(self): return self._state._redo_stack

    def _ani_set_text(self,val):
        self._display.setText(f"{val:.0f}")
        self._ani_running=True
        if val>=0: self._set_display_color(C["dsp_fg"])

    def _toast(self,msg,kind="info"):
        self._toast_dir="in"   # 先置方向, 防止 stop() 触发的旧回调隐藏标签
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
        self._toast_anim.stop()
        self._toast_anim.setStartValue(0.0); self._toast_anim.setEndValue(1.0)
        self._toast_effect.setOpacity(0.0)
        self._toast_anim.start()
        self._toast_timer.start(1600)
        dlog("toast", kind, msg)

    def _toast_fade_out(self):
        self._toast_dir="out"
        self._toast_anim.stop()
        self._toast_anim.setStartValue(1.0); self._toast_anim.setEndValue(0.0)
        self._toast_anim.start()

    def _toast_fade_done(self):
        if getattr(self,"_toast_dir",None)=="out":
            self._toast_lb.hide()
            self._toast_effect.setOpacity(1.0)   # 复位, 供下次淡入

    def _menu(self):
        m=QMenu(self)
        m.setStyleSheet(f"QMenu{{background:{C['dsp_bg']};color:{C['title']};border:1px solid {C['tb_bdr']};border-radius:10px;padding:6px;}}"
                        f"QMenu::item{{padding:7px 26px 7px 12px;border-radius:6px;}}"
                        f"QMenu::item:selected{{background:{C['aux_bg']};color:{C['rad_on']};}}"
                        f"QMenu::item:disabled{{color:{C['sub']};font-weight:600;}}"
                        f"QMenu::separator{{height:1px;background:{C['tb_bdr']};margin:5px 8px;}}")
        return m

    # ===== 窗口样式 =====
    def _set_style(self):
        self.setStyleSheet(f"QMainWindow{{background:{C['win']};}}")

    def _set_display_color(self,color):
        if getattr(self,"_display_color_last",None)==color: return   # 每键样式重刷防护
        self._display_color_last=color
        self._display.setTextColor(color)
        self._display.setStyleSheet(f"background:transparent;color:{color};border:none;")

    # ===== 当前会话撤销 / 重做 =====
    def _record_undo(self):
        self._state.record_undo()

    def _restore_calculator_state(self):
        """撤销/重做后按当前状态同步控件 (数据恢复已在 state.undo/redo 内完成)。"""
        self._state.restoring=True
        try:
            self._value_anim.stop(); self._ani_running=False; self._ani_last=""
            self._lock_style_state=None; self._aux_last={}; self._expr_last=""
            self._sign_btn.setChecked(self._signed)
            self._sign_btn.setStyleSheet(self._sign_style(self._signed))
            self._refresh_radix_buttons()
            self._bit_indicator.clear_selection()
            if self._error:
                self._set_active_op(None)
                self._display.setText("Error"); self._set_display_color(C["dsp_neg"])
            else:
                self._set_active_op(self._pending["op"] if self._pending else None)
                self._refresh_display()
        finally:
            self._state.restoring=False

    def _undo(self):
        if not self._state.undo():
            self._toast("没有可撤销的操作","warning")
            return
        self._restore_calculator_state()
        self._toast("已撤销")
        dlog("undo applied", "undo", len(self._undo_stack), "redo", len(self._redo_stack))

    def _redo(self):
        if not self._state.redo():
            self._toast("没有可重做的操作","warning")
            return
        self._restore_calculator_state()
        self._toast("已重做")
        dlog("redo applied", "undo", len(self._undo_stack), "redo", len(self._redo_stack))

    # ===== 构建 UI =====
    def _build_ui(self):
        from siui.components.label import SiLabelRefactor
        from siui.gui import SiFont
        cw=QWidget(self); self.setCentralWidget(cw)
        v=QVBoxLayout(cw); v.setContentsMargins(14,8,14,12); v.setSpacing(6)
        self._root_layout=v
        self._compact_layout=None

        # 进制栏
        tb=QFrame(); tb.setObjectName("calcToolbar")
        self._toolbar=tb
        tb.setStyleSheet(f"QFrame#calcToolbar{{background:{C['tb_bg']};border:1px solid {C['tb_bdr']};border-radius:12px;}}")
        tbl=QHBoxLayout(tb); tbl.setContentsMargins(7,4,7,4); tbl.setSpacing(4)
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
        self._display=DisplayText(self); self._display.setFixedHeight(84)
        self._display.setBackgroundColor(C["dsp_bg"]); self._display.setBorderRadius(18)
        self._display.setAlignment(Qt.AlignRight|Qt.AlignBottom)
        self._display.setFont(self._display_font(34)); self._display.setTextColor(C["dsp_fg"])
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
        self._display.installEventFilter(self)
        self._display.setContextMenuPolicy(Qt.CustomContextMenu)
        self._display.customContextMenuRequested.connect(self._show_display_menu)
        # RGB 色板: HEX 模式下显示低 24 位颜色
        self._rgb_chip=QLabel(self._display)
        self._rgb_chip.setFixedSize(18,12)
        self._rgb_chip.setAlignment(Qt.AlignCenter)
        self._rgb_chip.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._rgb_chip.hide()
        self._chip_last=None

        # 独立表达式栏：不改变传统按键计算状态
        expr_bar=QFrame(); expr_bar.setObjectName("expressionBar"); self._expr_bar=expr_bar
        expr_bar.setStyleSheet(f"QFrame#expressionBar{{background:{C['aux_bg']};border:1px solid {C['tb_bdr']};border-radius:10px;}}")
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
        self._mask_state_label.setFixedSize(32,20); self._mask_state_label.setAlignment(Qt.AlignCenter)
        self._mask_le=QLineEdit(self)
        self._mask_le.setPlaceholderText("0x…")
        self._mask_le.setClearButtonEnabled(True)
        self._mask_le.setFixedWidth(154)
        self._mask_le.setToolTip("支持 0x、0b、0o、十进制或无前缀十六进制")
        self._mask_le.textChanged.connect(self._on_mask_changed)
        self._mask_le.editingFinished.connect(self._confirm_mask)
        self._set_mask_feedback("off")
        bit_head_l.addWidget(bit_title)
        self._sel_label=QLabel(self)
        self._sel_label.setStyleSheet(f"background:{C['aux_bg']};border:1px solid {C['op_active']};border-radius:8px;padding:2px 10px;color:{C['title']};font-family:Consolas;font-size:11px;font-weight:600;")
        self._sel_label.setCursor(Qt.PointingHandCursor)
        self._sel_label.setToolTip("Shift+拖拽 bit 选择位域; 点击复制其值 (AC 清除)")
        self._sel_label.setFixedWidth(158)
        self._sel_label.hide()
        self._sel_label.mouseReleaseEvent = lambda e: self._copy_text(f"0x{self._sel_value:X}","选中位域") if self._sel_value is not None and e.button()==Qt.LeftButton else None
        bit_head_l.addWidget(self._sel_label)
        self._byte_order_label=QLabel(self)
        self._byte_order_label.setStyleSheet(f"background:{C['aux_bg']};border:1px solid {C['tb_bdr']};border-radius:8px;padding:2px 8px;color:{C['aux_fg']};font-family:Consolas;font-size:10px;font-weight:600;")
        self._byte_order_label.setToolTip("Little Endian 字节序预览，不改变计算值或复制内容")
        self._byte_order_label.setMaximumWidth(180)
        self._byte_order_label.hide()
        bit_head_l.addWidget(self._byte_order_label)
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
                lb.setStyleSheet(f"QLabel{{background:{C['aux_bg']};border:1px solid {C['tb_bdr']};border-radius:10px;padding:0 12px 0 12px;}}"
                                 f"QLabel:hover{{background:{C['dsp_bg']};border-color:{C['rad_on']};}}")
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
        # 淡入淡出
        self._toast_effect=QGraphicsOpacityEffect(self._toast_lb)
        self._toast_lb.setGraphicsEffect(self._toast_effect)
        self._toast_anim=QVariantAnimation(self._toast_lb); self._toast_anim.setDuration(140)
        self._toast_anim.valueChanged.connect(lambda v: self._toast_effect.setOpacity(float(v)))
        self._toast_anim.finished.connect(self._toast_fade_done)

        # 初始进制状态
        self._refresh_radix_buttons()

    # ===== 工具 =====
    def _display_font(self,size):
        return make_display_font(size)

    def _toggle_shortcut_overlay(self):
        """按 ? 弹出/关闭快捷键速查浮层 (点外部或 Esc 关闭)。"""
        if getattr(self,"_shortcut_overlay",None) and self._shortcut_overlay.isVisible():
            self._shortcut_overlay.close(); self._shortcut_overlay.deleteLater()
            self._shortcut_overlay=None; return
        ov=QWidget(self, Qt.Popup|Qt.FramelessWindowHint)
        ov.setObjectName("shortcutOverlay")
        ov.setAttribute(Qt.WA_TranslucentBackground)
        bg=QColor(C["dsp_bg"])
        ov.setStyleSheet(f"QWidget#shortcutOverlay{{background:rgba({bg.red()},{bg.green()},{bg.blue()},244);"
                         f"border:1px solid {C['tb_bdr']};border-radius:12px;}}")
        l=QVBoxLayout(ov); l.setContentsMargins(20,14,20,16); l.setSpacing(6)
        title=QLabel("快捷键"); title.setStyleSheet(f"color:{C['title']};font-size:13px;font-weight:700;background:transparent;border:none;")
        l.addWidget(title)
        kb=lambda t:(f"<span style='background:{C['aux_bg']};color:{C['title']};"
                     f"font-weight:600;'>&nbsp;{t}&nbsp;</span>")
        plain=lambda t:f"<span style='color:{C['hint']}'>{t}</span>"
        rows=[("0-9  A-F","数字输入"),("+ - * / % & | ^ ~","运算"),("<<  >>","移位 (Shift+< / >)"),
              ("Enter  =","求值"),("Esc / Del","清空"),("Ctrl+Z / Ctrl+Y","撤销 / 重做"),("Ctrl+C / Ctrl+V","复制 / 粘贴"),
              ("Shift+拖拽 bit","选择位域"),("Tab / Shift+Tab","循环进制"),("F1","帮助"),("F2","表达式")]
        for k,d in rows:
            row=QLabel(f"{kb(k)}  {plain(d)}")
            row.setTextFormat(Qt.RichText)
            row.setStyleSheet("background:transparent;border:none;")
            l.addWidget(row)
        ov.adjustSize()
        g=self.geometry()
        ov.move(g.x()+(g.width()-ov.width())//2, g.y()+(g.height()-ov.height())//2)
        self._shortcut_overlay=ov
        ov.show()
        dlog("shortcut overlay shown")

    def _hint_html(self,compact=False):
        """底部快捷键提示: 键帽样式, 随主题着色。"""
        kb=lambda t:(f"<span style='background:{C['aux_bg']};color:{C['title']};"
                     f"font-weight:600;'>&nbsp;{t}&nbsp;</span>")
        plain=lambda t:f"<span style='color:{C['hint']}'>{t}</span>"
        sep=plain("  ·  ")
        if compact:
            return (kb("F1")+plain(" 帮助 ")+sep+
                    kb("F2")+plain(" 表达式 ")+sep+
                    kb("Ctrl+Z/Y"))
        return (kb("F1")+plain(" 帮助 ")+sep+
                kb("F2")+plain(" 表达式 ")+sep+
                kb("Ctrl+Z/Y")+plain(" 撤销/重做 ")+sep+
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
            self._expr_label.setGeometry(m.left(), 0,
                self._display.width()-m.left()-m.right(), self._display.height()-3)
            self._rgb_chip.move(self._display.width()-34, 9)
        return super().eventFilter(obj,ev)

    def resizeEvent(self,e):
        if not all(hasattr(self,name) for name in ("_root_layout","_tools_btn","_mask_le","_hint_label")):
            return super().resizeEvent(e)
        self._update_layout_density()
        super().resizeEvent(e)
        self._display_font_size=None
        self._refresh_display()

    def _update_layout_density(self):
        compact=self.width()<620
        if compact!=getattr(self,"_compact_layout",None):
            self._compact_layout=compact
            self._root_layout.setContentsMargins(10 if compact else 14,8,10 if compact else 14,12)
            self._tools_btn.setText("⋯" if compact else "工具")
            self._tools_btn.setFixedWidth(28 if compact else 38)
            self._mask_le.setFixedWidth(118 if compact else 154)
            self._hint_label.setText(self._hint_html(compact))
            self._aux_last={}
            if self._byte_order=="little" and hasattr(self,"_byte_order_label"):
                self._byte_order_label.setText("LE" if compact else f"LE  {self._little_endian_preview()}")
            dlog("layout", "compact" if compact else "regular", "width", self.width())

    # ===== 设置记忆 =====
    def _system_theme(self):
        """读取 Windows 应用亮暗设置; 读取失败默认亮色。"""
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
                light,_=winreg.QueryValueEx(key,"AppsUseLightTheme")
            return "light" if light else "dark"
        except OSError:
            return "light"

    def _apply_system_theme(self):
        if not self._follow_system: return
        t=self._system_theme()
        if t!=self._theme: self._set_theme(t)

    def _set_follow_system(self,on):
        """跟随系统亮暗: 开启即应用检测到的主题并启动轮询。"""
        self._follow_system=on
        self._settings.setValue("ui/follow_system",on)
        if on:
            self._apply_system_theme()
            self._sys_timer.start()
            self._toast("主题跟随系统","success")
        else:
            self._sys_timer.stop()
            self._toast("主题手动","success")
        dlog("follow system:", on)

    def _restore_settings(self):
        s=self._settings
        self._theme=s.value("ui/theme","light")
        if self._theme not in ("light","dark"): self._theme="light"
        self._follow_system=s.value("ui/follow_system",False,type=bool)
        if self._follow_system: self._theme=self._system_theme()
        self._radix=s.value("calc/radix",10,type=int)
        if self._radix not in RADIX_DIGITS: self._radix=10
        self._signed=s.value("calc/signed",False,type=bool)
        self._locked=s.value("calc/locked",False,type=bool)
        self._bit_width=s.value("calc/bit_width",8,type=int)
        if self._bit_width not in BIT_MASKS: self._bit_width=8
        self._pad_display=s.value("format/pad_display",False,type=bool)
        self._byte_order=s.value("format/byte_order","native")
        if self._byte_order not in ("native","little"): self._byte_order="native"
        self._mask_favorites=self._restore_number_history(s.value("calc/mask_favorites",[]),8)
        try:
            recent_start=s.value("calc/field_start",0,type=int)
            recent_width=s.value("calc/field_width",1,type=int)
            self._field_recent=(max(0,recent_start),max(1,recent_width))
        except (TypeError,ValueError): self._field_recent=(0,1)
        self._pinned=s.value("win/pinned",False,type=bool)
        # Each launch starts with a clean calculator value; preferences and history still persist.
        self._value=0
        dlog("session current value reset")
        self._history=self._restore_history(s.value("calc/history",[]),10)
        raw_expr=s.value("calc/expression_history",[])
        if not isinstance(raw_expr,(list,tuple)): raw_expr=[] if raw_expr in (None,"") else [raw_expr]
        self._expression_history=[str(v) for v in raw_expr if str(v).strip()][:5]
        self._saved_mask=str(s.value("calc/mask","") or "")
        self._entry=self._format_entry(self._value)

    @staticmethod
    def _restore_number_history(raw,limit):
        if not isinstance(raw,(list,tuple)): raw=[] if raw in (None,"") else [raw]
        result=[]
        for value in raw[:limit]:
            try: result.append(clamp(int(value),64))
            except (TypeError,ValueError): continue
        return result

    @staticmethod
    def _restore_history(raw,limit):
        """Restore current history entries and accept pre-v1.10 numeric-only entries."""
        if not isinstance(raw,(list,tuple)): raw=[] if raw in (None,"") else [raw]
        result=[]
        for entry in raw[:limit]:
            try:
                data=json.loads(entry) if isinstance(entry,str) and entry.lstrip().startswith("{") else entry
                if isinstance(data,dict):
                    value=clamp(int(data["v"]),64); source=str(data.get("src", ""))
                else:
                    value=clamp(int(data),64); source=""
            except (TypeError,ValueError,KeyError,json.JSONDecodeError):
                dlog("history restore rejected:", entry)
                continue
            result.append({"v":value,"src":source})
        return result

    def _apply_theme_colors(self):
        C.clear(); C.update(DARK_C if self._theme=="dark" else LIGHT_C)

    def _set_theme(self,theme):
        if theme==self._theme: return
        expression=self._expression_input.text()
        mask=self._mask_le.text()
        self._theme=theme; self._apply_theme_colors(); self._set_style()
        old=self.takeCentralWidget()
        if old is not None: old.deleteLater()
        self._aux_last={}; self._expr_last=""; self._lock_style_state=None; self._display_font_size=None; self._chip_last=None
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
            s.setValue("ui/follow_system",self._follow_system)
            s.setValue("calc/radix",self._radix)
            s.setValue("calc/signed",self._signed)
            s.setValue("calc/locked",self._locked)
            s.setValue("calc/bit_width",self._bit_width)
            s.setValue("format/pad_display",self._pad_display)
            s.setValue("format/byte_order",self._byte_order)
            s.setValue("calc/mask_favorites",[str(v) for v in self._mask_favorites])
            s.setValue("calc/field_start",self._field_recent[0])
            s.setValue("calc/field_width",self._field_recent[1])
            s.remove("calc/value")
            s.setValue("calc/mask",self._mask_le.text())
            s.setValue("calc/history",[json.dumps(h,ensure_ascii=False,separators=(",",":")) for h in self._history])
            s.setValue("calc/expression_history",self._expression_history)
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
                       f"QPushButton:hover{{background:{C['rad_on']};}}"
                       f"QPushButton:focus{{border:1px solid {C['op_active']};}}")
        return (f"QPushButton{{background:transparent;color:{C['rad_off']};border:none;"
                f"border-radius:7px;font-weight:600;}}"
                f"QPushButton:hover{{color:{C['title']};}}"
                f"QPushButton:focus{{border:1px solid {C['rad_on']};}}")

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
        self._state.flip_signed()
        self._sign_btn.setChecked(self._signed)
        self._sign_btn.setStyleSheet(self._sign_style(self._signed))
        self._refresh_display()
        self._toast("有符号" if self._signed else "无符号")

    def _toggle_lock(self):
        self._record_undo()
        self._locked=self._lock_btn.isChecked()
        self._lock_btn.setToolTip("位宽已锁定" if self._locked else "锁定当前位宽")
        self._lock_btn.setStyleSheet(self._lock_btn_style(self._locked))
        self._refresh_display()
        dlog("bit width lock:", self._locked, "bits", self._bit_width)
        self._toast("位宽已锁定" if self._locked else "位宽自动")

    def _step_bw_up(self):
        for b in (16,32,64):
            if self._bit_width<b:
                self._set_bit_width(b); return

    def _step_bw_dn(self):
        for b in (32,16,8):
            if self._bit_width>b:
                self._set_bit_width(b); return

    def _show_bit_width_menu(self):
        m=self._menu()
        acts={b:m.addAction(f"{b} bit") for b in BIT_MASKS}
        act=m.exec_(self._bit_width_lb.mapToGlobal(self._bit_width_lb.rect().bottomLeft()))
        if act is not None:
            self._set_bit_width(next(b for b,a in acts.items() if a==act))

    def _set_bit_width(self,b):
        if not self._state.set_bit_width(b): return
        self._lock_btn.setChecked(True); self._lock_btn.setToolTip("位宽已锁定")
        self._value_anim.stop(); self._ani_running=False; self._ani_last=""
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
              "<b>快捷键：</b>Enter =，Esc 清空，Tab 循环进制，Ctrl+C 复制，F1 帮助，F2 定位表达式栏。")
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
        if self._error:
            self._toast("错误状态无可复制值","warning")
            dlog("copy rejected: error state")
            return
        self._copy_text(self._display_value,"当前值")

    def _copy_radix(self,name):
        self._copy_text(self._aux_value(name),name)

    def _show_error_ui(self,message):
        """错误态 UI 呈现 (数据字段已由 state.enter_error 清理)。"""
        self._value_anim.stop(); self._ani_running=False
        self._set_active_op(None)
        self._display.setText("Error"); self._set_display_color(C["dsp_neg"])
        self._toast(message,"error")
        dlog("calculation error:", message)

    def _set_error(self,message):
        self._state.enter_error()
        self._show_error_ui(message)

    def _paste(self):
        text=QApplication.clipboard().text().strip()
        if not text: return
        try:
            v=parse_number(text)
        except ValueError:
            self._toast("无法识别剪贴板数值","warning")
            dlog("paste parse failed:", text)
            return
        self._load_value(v)
        truncated=v < -(1<<63) or v > BIT_MASKS[64] or v != self._value
        self._toast(f"已粘贴 {text}"+(" · 已截断" if truncated else ""),"warning" if truncated else "success")
        dlog("paste", text, "->", hex(self._value))

    def _flash_expr_bar(self,color):
        """表达式栏边框短暂着色: 绿=成功, 红=出错。"""
        self._expr_bar.setStyleSheet(f"QFrame#expressionBar{{background:{C['aux_bg']};border:1px solid {color};border-radius:10px;}}")
        QTimer.singleShot(900, lambda: self._expr_bar.setStyleSheet(
            f"QFrame#expressionBar{{background:{C['aux_bg']};border:1px solid {C['tb_bdr']};border-radius:10px;}}"))

    def _evaluate_expression(self):
        text=self._expression_input.text().strip()
        bits=self._bit_width if self._locked else 64
        try: value=evaluate_expression(text,bits,self._signed)
        except (ValueError,RecursionError) as exc:
            self._toast(f"表达式错误：{exc}","error")
            self._flash_expr_bar(C["dsp_neg"])
            dlog("expression failed:", text, exc)
            return
        self._record_undo()
        if self._error: self._error=False
        self._value=self._fit_value(value, signed_64=True); self._entry=self._format_entry(self._value)
        self._new_entry=True; self._pending=None; self._last_op=None
        self._set_active_op(None); self._remember(self._value,text); self._refresh_display()
        self._remember_expression(text)
        self._flash_expr_bar(C["success"])
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

    def _load_value(self,v,record_undo=True):
        cleared=self._state.load_value(v,record_undo=record_undo)
        if cleared:
            self._lock_btn.setChecked(False)
            self._value_anim.stop(); self._ani_running=False; self._ani_last=""
            self._bit_indicator.clear_selection()
        self._set_active_op(None)
        self._refresh_display()
        dlog("load value", v, "->", hex(self._value), "bits", self._bit_width)

    def _fit_value(self,value,signed_64=False):
        """Fit a loaded or computed value before formatting its editable entry."""
        raw=value
        if self._signed and not self._locked and signed_64 and raw >= (1<<63):
            raw=to_signed(raw,64)
        if not self._locked:
            self._bit_width=self._calc_bw(raw)
        return clamp(raw,self._bit_width)

    def _remember(self,v,src=""):
        if self._history and self._history[0]["v"]==v: return
        self._history.insert(0,{"v":v,"src":src})
        del self._history[10:]

    def _show_history(self):
        if not self._history:
            self._toast("暂无历史")
            return
        m=self._menu()
        acts=[]
        for entry in self._history:
            acts.append(m.addAction(self._history_entry_label(entry)))
        m.addSeparator()
        a_clr=m.addAction("清空历史")
        act=m.exec_(self._hist_btn.mapToGlobal(self._hist_btn.rect().bottomLeft()))
        if act is None: return
        if act==a_clr:
            self._history=[]; self._toast("历史已清空","success")
        else:
            self._load_value(self._history[acts.index(act)]["v"])
            self._toast(f"已载入 0x{self._value:X}","success")

    def _history_entry_label(self,entry):
        v=entry["v"]; src=entry.get("src","")
        bits=next(b for b in BIT_MASKS if v<=BIT_MASKS[b])
        head=f"{src}  →  " if src else ""
        return f"{head}0x{v:X}    {v}    {bits} bit"

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
        format_menu=m.addMenu("格式与 Mask")
        a_pad=format_menu.addAction("HEX / BIN 补齐到位宽")
        a_pad.setCheckable(True); a_pad.setChecked(self._pad_display)
        order_menu=format_menu.addMenu("字节序预览")
        a_native=order_menu.addAction("原始字节序")
        a_native.setCheckable(True); a_native.setChecked(self._byte_order=="native")
        a_little=order_menu.addAction("Little Endian")
        a_little.setCheckable(True); a_little.setChecked(self._byte_order=="little")
        format_menu.addSeparator()
        mask_menu=format_menu.addMenu("常用 Mask")
        width=self._bit_width; top_byte=((1<<min(8,width))-1)<<max(width-8,0)
        standard_masks={
            f"当前 {width} bit 全 1":BIT_MASKS[width],
            "低 8 bit · 0xFF":0xFF,
            "低 16 bit · 0xFFFF":0xFFFF,
            f"高 {min(8,width)} bit":top_byte,
        }
        mask_actions={mask_menu.addAction(label):value for label,value in standard_masks.items()}
        if self._mask_favorites:
            mask_menu.addSeparator()
            favorite_actions={mask_menu.addAction(f"收藏 · 0x{value:X}"):value for value in self._mask_favorites}
        else:
            favorite_actions={}
        a_favorite=mask_menu.addAction("收藏当前 Mask")
        m.addSeparator()
        appearance=m.addMenu("外观")
        a_follow=appearance.addAction("跟随系统亮暗")
        a_follow.setCheckable(True); a_follow.setChecked(self._follow_system)
        appearance.addSeparator()
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
        elif act==a_pad: self._set_padding(not self._pad_display)
        elif act==a_native: self._set_byte_order("native")
        elif act==a_little: self._set_byte_order("little")
        elif act in mask_actions: self._apply_mask_value(mask_actions[act],"已应用常用 Mask")
        elif act in favorite_actions: self._apply_mask_value(favorite_actions[act],"已应用收藏 Mask")
        elif act==a_favorite: self._remember_mask_favorite()
        elif act==a_follow:
            self._set_follow_system(a_follow.isChecked())
        elif act==a_light:
            self._set_follow_system(False)
            self._set_theme("light")
        elif act==a_dark:
            self._set_follow_system(False)
            self._set_theme("dark")
        elif act==a_help: self._show_help()
        elif act==a_about: self._show_about()
        else:
            for b,a in sign_actions.items():
                if act==a:
                    self._apply_tool_value(clamp(to_signed(self._value,b),self._bit_width),f"{b}b 符号扩展")
                    break

    def _set_padding(self,on):
        self._pad_display=bool(on); self._refresh_display()
        self._toast("HEX / BIN 已补齐到位宽" if on else "HEX / BIN 使用紧凑显示")
        dlog("display padding", on)

    def _set_byte_order(self,order):
        if order not in ("native","little") or order==self._byte_order: return
        self._byte_order=order; self._refresh_display()
        self._toast("Little Endian 预览" if order=="little" else "原始字节序预览")
        dlog("byte order", order)

    def _apply_mask_value(self,value,label):
        self._mask_le.setText(f"0x{clamp(value,64):X}")
        self._toast(label,"success")
        dlog("mask preset", hex(clamp(value,64)))

    def _remember_mask_favorite(self):
        value=self._bit_indicator._mask
        if not value:
            self._toast("请先输入非零 Mask","warning"); return
        if value in self._mask_favorites: self._mask_favorites.remove(value)
        self._mask_favorites.insert(0,value); del self._mask_favorites[8:]
        self._toast(f"已收藏 Mask 0x{value:X}","success")
        dlog("mask favorite", hex(value), "count", len(self._mask_favorites))

    def _apply_tool_value(self,value,label):
        self._record_undo()
        if self._error: self._error=False
        self._value=clamp(value,64); self._locked=True; self._new_entry=True
        self._entry=self._format_entry(self._value); self._pending=None; self._last_op=None
        self._set_active_op(None); self._remember(self._value,label); self._refresh_display()
        self._toast(f"{label} · {self._bit_width}b","success")
        dlog("tool", label, "->", hex(self._value), "bits", self._bit_width)

    def _field_range(self):
        recent_start,recent_width=self._field_recent
        start,ok=QInputDialog.getInt(self,"位域起始位","起始位（LSB = 0）：",min(recent_start,self._bit_width-1),0,self._bit_width-1)
        if not ok: return None
        width,ok=QInputDialog.getInt(self,"位域长度","长度：",min(recent_width,self._bit_width-start),1,self._bit_width-start)
        if not ok: return None
        self._field_recent=(start,width)
        dlog("field range", start, width)
        return (start,width)

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
        try: value=parse_number(text)
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
    def _cycle_radix(self,step):
        order=(16,10,8,2)
        self._rad(order[(order.index(self._radix)+step)%4])

    def _rad(self,r):
        if self._state.radix_switch(r):
            self._refresh_radix_buttons()
            self._refresh_display()

    def _input_digit(self,d):
        if self._error: self._clear_all()
        msg=self._state.input_digit(d)
        if msg: self._toast(msg); return
        self._set_active_op(self._state.active_op)
        self._refresh_display()

    def _clear_all(self,record_undo=True):
        self._state.clear_all(record_undo=record_undo)
        self._lock_btn.setChecked(False)
        self._value_anim.stop(); self._ani_running=False; self._ani_last=""
        self._set_active_op(None)
        self._bit_indicator.clear_selection()
        self._refresh_display()

    def _backspace(self):
        if self._error: self._clear_all(); return
        self._state.backspace()
        self._refresh_display()

    def _apply_operator(self,op):
        if self._error: self._clear_all(); return
        self._state.apply_operator(op)
        self._set_active_op(self._state.active_op)
        self._refresh_display()

    def _equals(self):
        if self._error: return
        err,mem=self._state.equals()
        if err:
            self._show_error_ui(err); return
        if mem: self._remember(*mem)
        self._set_active_op(self._state.active_op)
        self._refresh_display()

    _compute = staticmethod(compute)

    def _format_entry(self,v):
        return self._state.format_entry(v)

    def _format_radix(self,v,radix,pad=False):
        return self._state.format_radix(v,radix,pad)

    def _calc_bw(self,v):
        return self._state.calc_bw(v)

    def _fit_value(self,value,signed_64=False):
        return self._state.fit_value(value,signed_64)

    def _aux_value(self, name):
        return aux_text(name, self._state, self._pad_display)

    def _little_endian_preview(self):
        u=clamp(self._value,self._bit_width)
        return "0x"+u.to_bytes(self._bit_width//8,"big")[::-1].hex().upper()

    def _group_display(self,text):
        return group_display(self._radix,text)

    def _display_groups(self,text):
        return display_groups(self._radix,text)

    def _display_font_size_for(self,text):
        margins=self._display.contentsMargins()
        # The RGB chip lives in the card's top-right while the value is bottom-aligned.
        available=max(80,self._display.width()-margins.left()-margins.right())
        return font_size_for(text, display_groups(self._radix,text), available)

    def _refresh_display(self):
        if self._error: return
        self._bit_width=self._calc_bw(self._value)   # 自动位宽跟随当前值 (未锁定时)
        margins=self._display.contentsMargins()
        # The RGB chip lives in the card's top-right while the value is bottom-aligned.
        available=max(80,self._display.width()-margins.left()-margins.right())
        m=compute_display_model(self._state, pad_display=self._pad_display,
                                byte_order=self._byte_order, available_width=available)
        # 数值滚动动画 (仅 DEC、操作结果、值变幅 > 9)
        if self._radix==10 and self._new_entry and m.raw!=self._ani_last:
            try:
                ov=int(self._ani_last); nv=int(m.raw)
                if abs(nv-ov)>=10 and abs(nv-ov)<50000:
                    self._value_anim.stop()
                    self._value_anim.setStartValue(float(ov))
                    self._value_anim.setEndValue(float(nv))
                    self._value_anim.start()
            except: pass
        self._ani_last=m.raw
        if not self._ani_running:
            if m.groups:
                self._display.setGroupedText(*m.groups,m.visual)
            else:
                self._display.setText(m.visual)
        self._display_value=m.raw
        if m.font_size!=self._display_font_size:
            self._display_font_size=m.font_size; self._display.setFont(self._display_font(m.font_size))
        self._display.setToolTip(f"完整值：{m.raw}\n右键可按进制复制")
        self._set_display_color(C["dsp_neg"] if m.negative else C["dsp_fg"])
        self._bit_indicator.set_val(self._value,self._bit_width)
        if m.le_preview is not None:
            self._byte_order_label.setText("LE" if self._compact_layout else f"LE  {m.le_preview}")
            self._byte_order_label.setToolTip(f"Little Endian：{m.le_preview}\n不改变计算值或复制内容")
            self._byte_order_label.show()
        else:
            self._byte_order_label.hide()
        bw_text=f"{self._bit_width}b"
        if self._bit_width_lb.text()!=bw_text: self._bit_width_lb.setText(bw_text)
        # 位宽标签/锁按钮样式 — 仅锁定状态变化时刷新, 避免每次按键重刷样式表
        if self._locked != self._lock_style_state:
            self._lock_style_state=self._locked
            self._lock_btn.setChecked(self._locked)
            self._lock_btn.setStyleSheet(self._lock_btn_style(self._locked))
            self._bit_width_lb.setStyleSheet(f"color:{C['lock'] if self._locked else C['sub']};padding:0 6px 0 2px;")
        # 多进制辅助行 — 内容不变时跳过 setText, 避免富文本重复解析
        for name in ("DEC","HEX","OCT","BIN"):
            if self._aux_last.get(name)!=m.aux[name]:
                self._aux_last[name]=m.aux[name]
                self._aux_labels[name].setText(m.aux[name])
        # 显示区左下角 pending 表达式
        if m.expr!=self._expr_last:
            self._expr_last=m.expr
            self._expr_label.setText(m.expr)
        # 位域选择标签 — 值随当前数值实时更新
        if self._bit_indicator._sel is not None:
            v=(self._value>>self._bit_indicator._sel[0])&((1<<(self._bit_indicator._sel[1]-self._bit_indicator._sel[0]+1))-1)
            if v!=self._sel_value:
                lo,hi=self._bit_indicator._sel
                self._set_selection_label(lo,hi,v)
        # RGB 色板 — 仅 HEX 模式, 取低 24 位
        if m.rgb is not None:
            chip=f"background:#{m.rgb:06X};border:1px solid {C['tb_bdr']};border-radius:3px;"
            self._rgb_chip.setToolTip(f"RGB 预览 #{m.rgb:06X}")
            if chip!=self._chip_last:
                self._chip_last=chip
                self._rgb_chip.setStyleSheet(chip); self._rgb_chip.show()
        elif self._chip_last is not None:
            self._chip_last=None; self._rgb_chip.hide()

    def _on_bit_click(self,v):
        self._record_undo()
        if self._error: self._error=False
        self._value=clamp(v,64); self._entry=self._format_entry(self._value); self._pending=None
        self._set_active_op(None)
        dlog("bit click ->", hex(self._value))
        self._refresh_display()

    def _set_mask_feedback(self,state,detail=""):
        le=self._mask_le
        if state=="active":
            color=C["warning"]; state_text="ON"; fg="#4A2A00"; bg=C["warning"]
        elif state=="error":
            color=C["dsp_neg"]; state_text="ERR"; fg="#4A1019"; bg=C["dsp_neg"]
        else:
            color=C["tb_bdr"]; state_text="OFF"; fg=C["sub"]; bg=C["aux_bg"]
        le.setStyleSheet(f"QLineEdit{{min-height:24px;border:1px solid {color};border-radius:8px;padding:1px 24px 1px 8px;color:{C['title']};background:{C['aux_bg']};font-family:Consolas;}}QLineEdit:focus{{border-color:{C['rad_on']};background:{C['dsp_bg']};}}")
        self._mask_state_label.setText(state_text)
        self._mask_state_label.setStyleSheet(f"background:{bg};color:{fg};border:1px solid {color};border-radius:8px;font-size:9px;font-weight:700;")
        le.setToolTip(detail or "支持 0x、0b、0o、十进制或无前缀十六进制")

    def _on_selection_changed(self,sel):
        """BitGlow 位域选择变化 → 更新 SEL 标签 (点击可复制)。"""
        if sel is None:
            self._sel_value=None; self._sel_label.hide(); return
        lo,hi=sel
        self._set_selection_label(lo,hi,(self._value>>lo)&((1<<(hi-lo+1))-1))
        self._sel_label.show()

    def _set_selection_label(self,lo,hi,value):
        """Keep the Mask control stationary even for a 64-bit selection value."""
        self._sel_value=value
        full=f"SEL {hi}:{lo} = 0x{value:X} · {value}"
        text=QFontMetrics(self._sel_label.font()).elidedText(full,Qt.ElideRight,130)
        self._sel_label.setText(text)
        self._sel_label.setToolTip(f"{full}\n点击复制；AC 清除选择")

    def _on_mask_changed(self,text):
        if not text.strip():
            self._bit_indicator.set_mask(0)
            self._set_mask_feedback("off")
            return
        t=text.strip()
        try:
            m=parse_number(t)
            self._bit_indicator.set_mask(clamp(m,64))
            truncated=m < -(1<<63) or m > BIT_MASKS[64]
            self._set_mask_feedback("active",f"Mask active: 0x{clamp(m,64):X}"+(" · 已截断 64 bit" if truncated else ""))
            dlog("mask active:",hex(clamp(m,64)))
        except ValueError:
            # Invalid drafts must not leave the previous Mask silently active.
            self._bit_indicator.set_mask(0)
            dlog("mask parse failed:", text)
            self._set_mask_feedback("error","掩码格式: 0x / 0b / 0o / 十进制")

    def _confirm_mask(self):
        """Report an invalid Mask once after editing, instead of on every keystroke."""
        text=self._mask_le.text().strip()
        if not text: return
        try:
            parse_number(text)
        except ValueError:
            self._toast("掩码格式: 0x / 0b / 0o / 十进制","warning")
            dlog("mask rejected on confirm:", text)

    # ===== 键盘 =====
    def keyPressEvent(self,e:QKeyEvent):
        k,tx=e.key(),e.text()
        if k==Qt.Key_Z and e.modifiers() & Qt.ControlModifier:
            if e.modifiers() & Qt.ShiftModifier: self._redo()
            else: self._undo()
            return
        if k==Qt.Key_Y and e.modifiers() & Qt.ControlModifier: self._redo(); return
        if k==Qt.Key_C and e.modifiers() & Qt.ControlModifier: self._copy_current(); return
        if k==Qt.Key_V and e.modifiers() & Qt.ControlModifier: self._paste(); return
        if tx=="?": self._toggle_shortcut_overlay(); return   # 需先于 "/" 运算映射
        if k==Qt.Key_Backtab: self._cycle_radix(-1); return
        if k==Qt.Key_Tab and not isinstance(QApplication.focusWidget(),QLineEdit):
            self._cycle_radix(-1 if e.modifiers() & Qt.ShiftModifier else 1); return
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
