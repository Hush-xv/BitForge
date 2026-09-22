"""
BitForge — 组合测试套件
用法: python test_bitforge.py
每次修改升版前运行，确保所有功能正常。
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from PyQt5.QtCore import Qt, QEvent, QPoint
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QApplication
from bitforge import (BitForge, C, byte_swap, clamp, evaluate_expression,
                      extract_field, rotate_left, rotate_right, to_signed,
                      write_field)

app = QApplication(sys.argv)
w = BitForge()
w._persist = False   # 测试不写 QSettings
w.show(); app.processEvents()  # 触发布局，验证浮层坐标
passed = 0; failed = 0

def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
    else:
        failed += 1
        if detail:
            print(f"  FAIL {name}  ({detail})")
        else:
            print(f"  FAIL {name}")

# 模拟左键点击 bit
def left_click(bit):
    w._on_bit_click(w._value ^ (1 << bit))

# 模拟右键清除 bit
def right_click(bit):
    w._on_bit_click(w._value & ~(1 << bit))

# ======== 1. 进制切换 + 输入组合 ========
print("=== 1. Radix switch + input ===")

w._clear_all(); w._radix = 10
for c in "999": w._input_digit(c)
check("DEC input 999", w._value == 999, str(w._value))
w._rad(16)
check("switch to HEX keeps value", w._value == 999, str(w._value))
check("HEX display string", w._entry == "3E7", w._entry)

w._input_digit("8")
check("HEX append 8 -> 0x3E78", w._value == 0x3E78, hex(w._value))
w._rad(8)
check("switch OCT keeps value", w._value == 0x3E78, str(w._value))
# _format_entry(0x3E78, 8) = format(15992,"o") = "37170"
check("OCT display string", w._entry == "37170", w._entry)
w._input_digit("7")
check("OCT append 7", w._value == int("371707", 8), hex(w._value))

w._rad(2)
check("switch BIN keeps value", w._value == int("371707", 8), str(w._value))

# ======== 2. 输入 + 运算 + 进制切换组合 ========
print("=== 2. Input + operation + radix switch ===")

w._clear_all(); w._radix = 10
for c in "123": w._input_digit(c)
w._apply_operator("add"); w._value = 456; w._equals()
check("123+456=579", w._value == 579, str(w._value))
w._rad(16)
check("result in HEX 0x243", w._entry == "243", w._entry)

w._clear_all(); w._radix = 16
for c in "FF": w._input_digit(c)
w._apply_operator("mul"); w._value = 2; w._equals()
check("0xFF*2=510", w._value == 510, str(w._value))
w._rad(10)
check("result in DEC 510", w._entry == "510", w._entry)

w._clear_all(); w._radix = 16
for c in "F0": w._input_digit(c)
w._apply_operator("or"); w._value = 0x0F; w._equals()
check("0xF0 | 0x0F = 0xFF", w._value == 0xFF, hex(w._value))
w._apply_operator("xor"); w._value = 0xFF; w._equals()
check("0xFF ^ 0xFF = 0", w._value == 0, hex(w._value))

# ======== 3. 位宽操作组合 ========
print("=== 3. Bit-width operations ===")

w._clear_all()
check("AC: bw=8 locked=False", w._bit_width == 8 and not w._locked)
w._value = 0x100; w._refresh_display()
check("0x100 -> bw=16 auto", w._bit_width == 16, str(w._bit_width))
w._step_bw_up()
check("[+] -> bw=32 locked", w._bit_width == 32 and w._locked)
w._step_bw_up()
check("[+] -> bw=64", w._bit_width == 64)
w._step_bw_dn()
check("[-] -> bw=32 locked", w._bit_width == 32 and w._locked)

w._value = 0x1; w._refresh_display()
check("locked: small value keeps bw=32", w._bit_width == 32, str(w._bit_width))
w._value = 0x100000000; w._refresh_display()
check("locked: big value keeps bw=32", w._bit_width == 32, str(w._bit_width))

w._locked = False; w._refresh_display()
check("unlock: bw recalc for 0x100000000", w._bit_width == 64, str(w._bit_width))
w._value = 0x1; w._refresh_display()
check("unlock: small value shrinks bw", w._bit_width == 8, str(w._bit_width))

# ======== 4. 点击 bit 各种组合 ========
print("=== 4. Bit click combinations ===")

w._clear_all()
left_click(0); check("L click bit0 -> 1", w._value == 1, hex(w._value))
left_click(0); check("L click bit0 again -> 0", w._value == 0, hex(w._value))

left_click(0); left_click(1); left_click(2)
check("L click bits 0,1,2 -> 0x7", w._value == 0x7, hex(w._value))

w._value = 0xFF; w._refresh_display()
right_click(3)
check("R click bit3 of 0xFF -> 0xF7", w._value == 0xF7, hex(w._value))

w._value = 0; w._refresh_display()
left_click(4); check("L click bit4 -> 0x10", w._value == 0x10, hex(w._value))
left_click(4); check("L click bit4 again -> 0", w._value == 0, hex(w._value))

# ======== 5. 掩码组合 ========
print("=== 5. Mask operations ===")

w._value = 0xFFFF; w._refresh_display()
w._bit_indicator.set_mask(0x00FF)
check("mask set 0x00FF", w._bit_indicator._mask == 0x00FF)
w._bit_indicator.set_mask(0)
check("mask cleared", w._bit_indicator._mask == 0)
w._bit_indicator.set_mask(0xFF00)
check("mask re-set 0xFF00", w._bit_indicator._mask == 0xFF00)
w._bit_indicator.set_mask(0)

# ======== 6. 有符号/无符号组合 ========
print("=== 6. Signed/Unsigned ===")

w._value = 0x7FFFFFFF; w._signed = False; w._refresh_display()
check("unsigned 0x7FFFFFFF", "2147483647" in w._aux_labels["DEC"].text())
w._toggle_sign()
check("signed 0x7FFFFFFF", "2147483647" in w._aux_labels["DEC"].text())
w._toggle_sign()

w._value = 0x80000000; w._refresh_display()
t = w._aux_labels["DEC"].text()
check("unsigned 0x80000000", "2147483648" in t, t)
w._toggle_sign()
t = w._aux_labels["DEC"].text()
check("signed 0x80000000", "-2147483648" in t, t)
w._toggle_sign()

# ======== 7. 运算组合 ========
print("=== 7. Arithmetic combinations ===")

w._clear_all(); w._value = 10; w._apply_operator("add"); w._value = 20; w._equals()
check("10+20=30", w._value == 30)
w._apply_operator("mul"); w._value = 3; w._equals()
check("30*3=90", w._value == 90)
w._apply_operator("sub"); w._value = 15; w._equals()
check("90-15=75", w._value == 75)
w._apply_operator("div"); w._value = 5; w._equals()
check("75/5=15", w._value == 15)

w._clear_all(); w._value = 0xFF; w._apply_operator("not")
check("NOT 0xFF on 64bit", w._value == 0xFFFFFFFFFFFFFF00, hex(w._value))
w._apply_operator("not")
check("NOT NOT 0xFF = 0xFF", w._value == 0xFF, hex(w._value))

w._clear_all(); w._value = 1; w._apply_operator("lsh"); w._value = 10; w._equals()
check("1<<10=1024", w._value == 1024)
w._apply_operator("rsh"); w._value = 5; w._equals()
check("1024>>5=32", w._value == 32)

w._clear_all(); w._value = 100; w._apply_operator("mod"); w._value = 30; w._equals()
check("100%30=10", w._value == 10)

w._clear_all(); w._value = 10; w._apply_operator("div"); w._value = 0; w._equals()
check("10/0=Error", w._error and "Error" in w._display.text())

# ======== 8. 退格组合 ========
print("=== 8. Backspace combinations ===")

w._clear_all(); w._radix = 16
for c in "ABCDE": w._input_digit(c)
check("input ABCDE", w._entry == "ABCDE")
w._backspace(); check("BS -> ABCD", w._entry == "ABCD")
w._backspace(); check("BS -> ABC", w._entry == "ABC")
w._backspace(); check("BS -> AB", w._entry == "AB")
w._backspace(); check("BS -> A", w._entry == "A")
w._backspace(); check("BS -> 0", w._entry == "0")
w._backspace(); check("BS at 0 stays 0", w._entry == "0")

w._clear_all(); w._radix = 16
for c in "AB": w._input_digit(c)
check("input AB", w._value == 0xAB)
left_click(0)
check("flip bit0 -> 0xAA", w._value == 0xAA, hex(w._value))
w._backspace()
check("then BS -> A", w._entry == "A", w._entry)

w._error = True; w._backspace()
check("BS in Error -> AC", w._value == 0 and not w._error)

# ======== 9. 边界条件 ========
print("=== 9. Edge cases ===")

w._clear_all()
check("AC v=0 bw=8", w._value == 0 and w._bit_width == 8)

w._value = 0xFF; w._refresh_display()
check("8-bit max 0xFF", w._value == 0xFF and w._bit_width == 8)

w._value = 0xFFFF; w._refresh_display()
check("16-bit max 0xFFFF", w._value == 0xFFFF and w._bit_width == 16)

w._value = 0xFFFFFFFF; w._refresh_display()
check("32-bit max 0xFFFFFFFF", w._value == 0xFFFFFFFF and w._bit_width == 32)

w._value = 0x100000000; w._refresh_display()
check("64-bit entry", w._value == 0x100000000 and w._bit_width == 64)

w._value = 0xFF; w._radix = 16; w._clear_all(); w._refresh_display()
check("HEX prefix", w._display.text().startswith("0x"), w._display.text())

w._clear_all(); w._radix = 10; w._refresh_display()
check("DEC 0 display", w._display.text() == "0")

w._on_mask_changed("")
check("empty mask clears", w._bit_indicator._mask == 0)
w._on_mask_changed("0xDC")
check("mask 0xDC", w._bit_indicator._mask == 0xDC, hex(w._bit_indicator._mask))
w._on_mask_changed("")
check("empty mask clears again", w._bit_indicator._mask == 0)

check("clamp masks 8bit", clamp(0x1FF, 8) == 0xFF)
check("clamp negative", clamp(-1, 8) == 0xFF)
check("clamp 64bit", clamp(1 << 70, 64) == 0, hex(clamp(1 << 70, 64)))
check("to_signed 8bit", to_signed(0xFF, 8) == -1)

# ======== 10. 功能完整性 ========
print("=== 10. Feature integrity ===")
check("valueChanged signal", hasattr(w._bit_indicator, "valueChanged"))
check("lock button", hasattr(w, "_lock_btn"))
check("step up/down", hasattr(w, "_step_bw_up") and hasattr(w, "_step_bw_dn"))
check("toast", hasattr(w, "_toast"))
check("value_anim", hasattr(w, "_value_anim"))
check("about", hasattr(w, "_show_about"))
ico = os.path.join(os.path.dirname(__file__), "bitforge.ico")
check("icon file", os.path.exists(ico))

# ======== 11. 复制到剪贴板 ========
print("=== 11. Copy to clipboard ===")

w._clear_all(); w._radix = 16
for c in "DEAD": w._input_digit(c)
w._refresh_display()

w._copy_radix("HEX")
check("copy HEX", QApplication.clipboard().text() == "0xDEAD", QApplication.clipboard().text())
w._copy_radix("DEC")
check("copy DEC", QApplication.clipboard().text() == "57005", QApplication.clipboard().text())
w._copy_radix("OCT")
check("copy OCT", QApplication.clipboard().text() == oct(0xDEAD), QApplication.clipboard().text())
w._copy_radix("BIN")
check("copy BIN", QApplication.clipboard().text() == bin(0xDEAD), QApplication.clipboard().text())

w._bit_width = 32; w._signed = True; w._value = 0x80000000; w._refresh_display()
w._copy_radix("DEC")
check("copy signed DEC", QApplication.clipboard().text() == "-2147483648", QApplication.clipboard().text())
w._signed = False; w._clear_all()

ev = QKeyEvent(QEvent.KeyPress, Qt.Key_C, Qt.ControlModifier, "c")
w.keyPressEvent(ev)
check("Ctrl+C copies display", QApplication.clipboard().text() == w._display.text(),
      QApplication.clipboard().text())

# ======== 12. 表达式行 / 置顶 / 右键菜单 ========
print("=== 12. Expr line / pin / context menu ===")

w._clear_all(); w._radix = 10; w._value = 123; w._refresh_display()
w._apply_operator("add")
check("expr shows pending", w._expr_label.text() == "123 +", w._expr_label.text())
w._clear_all()
check("expr cleared", w._expr_label.text() == "", w._expr_label.text())

w._apply_operator("mul")
check("expr mul symbol", "\u00d7" in w._expr_label.text(), w._expr_label.text())
w._clear_all()

before = bool(w.windowFlags() & Qt.WindowStaysOnTopHint)
w._pin_btn.setChecked(True); w._toggle_pin()
after = bool(w.windowFlags() & Qt.WindowStaysOnTopHint)
check("pin toggles on", after and w._pinned and after != before)
w._pin_btn.setChecked(False); w._toggle_pin()
check("pin toggles off", not (bool(w.windowFlags() & Qt.WindowStaysOnTopHint)) and not w._pinned)

check("context menu handler", hasattr(w, "_show_display_menu"))
w._toast_timer.stop(); w._toast_lb.hide()   # 第 11 节复制操作可能触发过 toast
check("toast pill widget", hasattr(w, "_toast_lb") and w._toast_lb.isHidden())
w._toast("test")
check("toast shows text", not w._toast_lb.isHidden() and w._toast_lb.text() == "test")
w._toast_lb.hide()
check("vsep helper", hasattr(w, "_vsep"))

# ======== 13. 交互修正: 运算符替换 / 连等 / 前导零 / 粘贴 / 历史 ========
print("=== 13. UX: operator replace / repeat equals / paste ===")

# 待定运算时按第二个运算符 → 替换而非提前计算
w._clear_all(); w._radix = 10
w._value = 12; w._refresh_display()
w._apply_operator("add"); w._apply_operator("mul")
check("operator replace", w._pending["op"] == "mul" and w._pending["lhs"] == 12, str(w._pending))
check("op button active", w._op_btns["mul"]._active and not w._op_btns["add"]._active)
w._equals()
check("12*12 after replace", w._value == 144, str(w._value))
check("op active cleared by equals", not w._op_btns["mul"]._active)

# 连按 = 重复上次运算: 144*12=1728 → = 20736
w._equals()
check("repeat equals", w._value == 1728, str(w._value))
w._equals()
check("repeat equals 2", w._value == 20736, str(w._value))

# 运算符高亮随输入熄灭
w._apply_operator("add")
check("op active on new pending", w._op_btns["add"]._active)
w._input_digit("5")
check("op active cleared by digit", not w._op_btns["add"]._active)
w._clear_all()
check("op active cleared by AC", not w._op_btns["add"]._active)

# NOT 保留待定运算: 12 + NOT → 12 + (~12)
w._value = 12; w._refresh_display()
w._apply_operator("add"); w._apply_operator("not")
check("NOT keeps pending", w._pending is not None and w._pending["lhs"] == clamp(~12, 64),
      hex(w._pending["lhs"]) if w._pending else "None")
w._clear_all()

# 前导零
w._input_digit("0"); w._input_digit("0"); w._input_digit("5")
check("leading zero strip", w._entry == "5", w._entry)
w._clear_all()

# Ctrl+V 粘贴
QApplication.clipboard().setText("0xDEAD"); w._paste()
check("paste 0x", w._value == 0xDEAD, hex(w._value))
QApplication.clipboard().setText("57005"); w._paste()
check("paste dec", w._value == 57005, hex(w._value))
QApplication.clipboard().setText("0b101"); w._paste()
check("paste 0b", w._value == 5, hex(w._value))
QApplication.clipboard().setText("3E7h"); w._paste()
check("paste h-suffix", w._value == 0x3E7, hex(w._value))
QApplication.clipboard().setText("1,000"); w._paste()
check("paste comma strip", w._value == 1000, hex(w._value))
QApplication.clipboard().setText("zzz"); w._paste()
check("paste invalid keeps value", w._value == 1000, hex(w._value))
evv = QKeyEvent(QEvent.KeyPress, Qt.Key_V, Qt.ControlModifier, "v")
QApplication.clipboard().setText("0xFF"); w.keyPressEvent(evv)
check("Ctrl+V pastes", w._value == 0xFF, hex(w._value))
w._clear_all()

# 历史: 记录 + 载入
w._value = 10; w._refresh_display()
w._apply_operator("add"); w._value = 20; w._equals()
check("history records", len(w._history) >= 1 and w._history[0] == 30, str(w._history))
w._load_value(w._history[0])
check("history load", w._value == 30 and w._pending is None)
check("hist button", hasattr(w, "_hist_btn"))
w._clear_all()

# Mask 前缀扩展
w._on_mask_changed("0b1100")
check("mask 0b prefix", w._bit_indicator._mask == 0xC, hex(w._bit_indicator._mask))
w._on_mask_changed("DC")
check("mask bare hex", w._bit_indicator._mask == 0xDC, hex(w._bit_indicator._mask))
w._on_mask_changed("0o17")
check("mask 0o prefix", w._bit_indicator._mask == 0xF, hex(w._bit_indicator._mask))
w._on_mask_changed("")

# ======== 14. 新增易用性：位宽预设 / 错误恢复 ========
print("=== 14. UX: bit-width presets / errors ===")

w._clear_all(); w._value = 0x1FF; w._refresh_display()
w._set_bit_width(8)
check("bit-width preset locks", w._bit_width == 8 and w._locked)
check("bit-width preset clamps display", w._display.text() == "255", w._display.text())
w._set_bit_width(32)
check("bit-width preset expands", w._bit_width == 32 and w._display.text() == "511", w._display.text())
w._set_bit_width(12)
check("invalid bit-width ignored", w._bit_width == 32, str(w._bit_width))

w._clear_all(); w._value = 7; w._apply_operator("div"); w._value = 0; w._equals()
check("division error clears pending", w._error and w._pending is None and w._last_op is None)
check("division error explains cause", w._toast_lb.text() == "除数不能为 0", w._toast_lb.text())
w._input_digit("3")
check("digit recovers from error", not w._error and w._value == 3, str(w._value))
check("help remains available", not hasattr(w, "_help_btn") and hasattr(w, "_show_help"))

# ======== 15. 位操作工具 / 长数值显示 ========
print("=== 15. Bit tools / grouped display ===")

check("ROL 8-bit", rotate_left(0x81, 8, 1) == 0x03)
check("ROR 8-bit", rotate_right(0x81, 8, 1) == 0xC0)
check("rotate count wraps", rotate_left(0x81, 8, 8) == 0x81)
check("byte swap 16-bit", byte_swap(0x12AB, 16) == 0xAB12)
check("byte swap 32-bit", byte_swap(0x12345678, 32) == 0x78563412)
check("extract bit field", extract_field(0xD6, 8, 1, 3) == 0x3)
check("write bit field", write_field(0xD6, 8, 1, 3, 0) == 0xD0)
try:
    extract_field(0, 8, 7, 2)
    check("field range rejected", False)
except ValueError:
    check("field range rejected", True)

w._clear_all(); w._value=0x8000; w._refresh_display()
w._apply_operator("rol"); w._value=1; w._equals()
check("ROL uses original bit-width", w._value == 1 and w._bit_width == 16 and w._locked)
w._apply_operator("ror"); w._value=1; w._equals()
check("ROR keeps bit-width", w._value == 0x8000 and w._bit_width == 16)

w._set_bit_width(32); w._radix=16; w._value=0xDEADBEEF; w._new_entry=False; w._refresh_display()
check("HEX display grouped", w._display.text() == "0xDE AD BE EF", w._display.text())
w._copy_current()
check("grouped HEX copies raw", QApplication.clipboard().text() == "0xDEADBEEF", QApplication.clipboard().text())
w._radix=2; w._value=0xA5F; w._refresh_display()
check("BIN display grouped", w._display.text() == "0b1010 0101 1111", w._display.text())
check("tool button", hasattr(w, "_tools_btn") and hasattr(w, "_show_tools"))

# ======== 16. 表达式模式 ========
print("=== 16. Expression mode ===")

check("expression precedence", evaluate_expression("1 + 2 * 3") == 7)
check("expression parentheses", evaluate_expression("(1 + 2) * 3") == 9)
check("expression radix and shift", evaluate_expression("(0x20 << 3) | 0x07") == 0x107)
check("expression aliases", evaluate_expression("NOT 0x0F AND 0xF0", 8) == 0xF0)
check("expression wraps at bit-width", evaluate_expression("0xFF + 2", 8) == 1)
check("expression 64-bit division exact", evaluate_expression("0xFFFFFFFFFFFFFFFE / 2") == 0x7FFFFFFFFFFFFFFF)
try:
    evaluate_expression("1 / 0")
    check("expression division error", False)
except ValueError as exc:
    check("expression division error", "除数不能为 0" in str(exc), str(exc))

w._clear_all(); w._locked=False; w._expression_input.setText("(0x20 << 3) | 0x07")
w._evaluate_expression()
check("expression UI result", w._value == 0x107 and w._bit_width == 16, hex(w._value))
w._set_bit_width(8); w._expression_input.setText("0xFF + 2")
w._evaluate_expression()
check("expression UI locked width", w._value == 1 and w._bit_width == 8 and w._locked)
w._expression_input.setText("1 / 0"); w._evaluate_expression()
check("expression UI keeps prior value on error", w._value == 1 and "表达式错误" in w._toast_lb.text(), w._toast_lb.text())
check("expression input", hasattr(w, "_expression_input") and hasattr(w, "_evaluate_expression"))

# ======== 17. 主题切换 ========
print("=== 17. Theme switching ===")

w._value=0x1234; w._expression_input.setText("0x12 + 0x34")
w._set_theme("dark")
check("dark theme applies", w._theme == "dark" and C["win"] == "#171A20")
check("theme preserves value", w._value == 0x1234 and w._expression_input.text() == "0x12 + 0x34")
check("theme is consolidated in tools", not hasattr(w, "_theme_btn") and hasattr(w, "_tools_btn"))
w._set_theme("light")
check("light theme restores", w._theme == "light" and C["win"] == "#F0F2F5")

# ======== 18. 外观状态与窄窗口布局 ========
print("=== 18. Visual hierarchy / responsive layout ===")

w._radix=16; w._signed=False; w._locked=True; w._bit_width=32; w._value=0xDEADBEEF; w._refresh_display()
check("display status metadata", "HEX" in w._display_meta_label.text() and "32 BIT" in w._display_meta_label.text(),
      w._display_meta_label.text())
check("active radix visually marked", C["rad_on"] in w._aux_labels["HEX"].text(), w._aux_labels["HEX"].text())
w.resize(580,700); w._update_layout_density(); app.processEvents()
check("compact layout", w._compact_layout and w._tools_btn.text()=="⋯", "compact")
w.resize(700,700); w._update_layout_density(); app.processEvents()
check("regular layout", not w._compact_layout and w._tools_btn.text()=="工具", "regular")
check("accessible calculator button", w._buttons[0].accessibleName() == "计算器按键 AC", w._buttons[0].accessibleName())

# ======== 19. 菜单、反馈与 Mask 状态 ========
print("=== 19. Menu / feedback / mask state ===")

menu=w._menu()
check("menu uses unified style", "QMenu::item:selected" in menu.styleSheet())
w._toast("state", "error")
check("error toast style", C["dsp_neg"] in w._toast_lb.styleSheet(), w._toast_lb.styleSheet())
check("toast is outside result card", w._toast_lb.parentWidget() is w.centralWidget(), str(w._toast_lb.parentWidget()))
w._on_mask_changed("0xDC")
check("active mask feedback", "Mask active: 0xDC" in w._mask_le.toolTip(), w._mask_le.toolTip())
check("active mask badge", w._mask_state_label.text() == "ON", w._mask_state_label.text())
w._on_mask_changed("")
check("empty mask placeholder", w._mask_le.placeholderText() == "0x…", w._mask_le.placeholderText())
check("empty mask badge", w._mask_state_label.text() == "OFF", w._mask_state_label.text())
check("mask has clear action", w._mask_le.isClearButtonEnabled())
w._bit_indicator.set_val(1,8); w._bit_indicator.resize(500,46)
check("bit hover hit test", w._bit_indicator._bit_at(460,25) == 0, str(w._bit_indicator._bit_at(460,25)))
check("button accessibility description", w._buttons[0].accessibleDescription() == "全部清除", w._buttons[0].accessibleDescription())

# ======== 20. 显示卡片与双主题对比度 ========
print("=== 20. Display card / theme contrast ===")

check("display uses a card", C["dsp_bg"] in w._display_card.styleSheet(), w._display_card.styleSheet())
check("compact display card", w._display.height() == 84, str(w._display.height()))
check("mask is in the bit map header", w._mask_le.width() == 154, str(w._mask_le.width()))
check("content header has no duplicate logo", not hasattr(w, "_brand_logo"))
check("button has full rounded shape", "paintEvent" in type(w._buttons[0]).__dict__ and w._buttons[0].bottomBorderHeight == 0 and w._buttons[0].style_data.border_radius == 12 and w._buttons[0].style_data.border_inner_radius == 12)
check("content header is removed", not hasattr(w, "_version_label") and not hasattr(w, "_theme_btn"))
w._radix=16; w._refresh_radix_buttons()
check("number key uses neutral contrast", w._buttons[5].style_data.button_color.name().upper() == "#D4D4D4", w._buttons[5].style_data.button_color.name())
w._mask_le.setText("0xAA")
w._set_theme("dark")
check("dark display text is visible", C["dsp_fg"] in w._display.styleSheet(), w._display.styleSheet())
check("dark display card is visible", C["dsp_bg"] in w._display_card.styleSheet(), w._display_card.styleSheet())
check("dark content header has no duplicate logo", not hasattr(w, "_brand_logo"))
check("theme keeps mask input", w._mask_le.text() == "0xAA", w._mask_le.text())
w._set_theme("light")
check("semantic accent is restrained purple", C["rad_on"] == "#AF92FB", C["rad_on"])
check("semantic success uses green", C["success"] == "#58C667", C["success"])
check("semantic warning uses orange", C["warning"] == "#FFB45B", C["warning"])

# ======== 21. 位宽切换不改变键盘尺寸 ========
print("=== 21. Stable keypad across bit widths ===")

w._set_bit_width(32); app.processEvents()
height_32=w._buttons[0].height()
w._set_bit_width(64); app.processEvents()
height_64=w._buttons[0].height()
check("keypad row height is stable", height_32 == height_64 == 42, f"{height_32}/{height_64}")
check("keypad grid height is stable", w._keypad_grid.height() == 277, str(w._keypad_grid.height()))
w._expression_input.setText("0x20 << 2"); w._evaluate_expression()
check("expression history remembers success", w._expression_history[0] == "0x20 << 2", str(w._expression_history))
button=w._buttons[0]; button._hover=True; button._pressed=True; button.update()
check("button feedback state is available", button._hover and button._pressed)
button._hover=False; button._pressed=False

# ======== 22. Bug 修复回归: 移位越界 / ROL 语义 / 错误态 ========
print("=== 22. Bug-fix regression: shift bounds / ROL / error state ===")

# 移位量为负 → 值经 64 位钳位后视为巨移位, 结果为 0 (不再 MemoryError 崩溃)
check("expr negative shift -> 0", evaluate_expression("1 << -1", 64) == 0)
check("expr negative rshift -> 0", evaluate_expression("1 >> -1", 64) == 0)

# 移位量 >= 位宽 → 结果为 0, 不再无界膨胀
check("expr shift 65 -> 0", evaluate_expression("1 << 65", 64) == 0)
check("expr rshift huge -> 0", evaluate_expression("99 >> 9999999999", 64) == 0)

# 键盘路径: 超大移位量同样安全
w._clear_all(); w._radix = 10
w._value = 2**64 - 1; w._refresh_display()
w._apply_operator("lsh"); w._equals()
check("keypad huge shift -> 0", w._value == 0 and not w._error, hex(w._value))
w._clear_all()

# ROL 菜单: 即时循环移位 1 位 (值 3, 8 位 → 6)
w._clear_all(); w._value = 3; w._refresh_display()
n_acts = len(w._history)
w._apply_tool_value(rotate_left(w._value, w._bit_width, 1), "循环左移 1 位")
check("ROL by 1", w._value == 6, hex(w._value))
check("ROL recorded in history", len(w._history) >= 1 and w._history[0] == 6, str(w._history[:3]))

# 错误态切主题: Error 显示保持
w._clear_all(); w._value = 10; w._refresh_display()
w._apply_operator("div"); w._value = 0; w._equals()
assert w._error and w._display.text() == "Error"
w._set_theme("dark")
check("error survives theme switch", w._error and w._display.text() == "Error",
      f"text={w._display.text()}")
w._set_theme("light")
check("error survives theme switch back", w._display.text() == "Error", w._display.text())

# 错误态右键菜单: 不提供复制
clipboard_before = QApplication.clipboard().text()
w._show_display_menu(QPoint(0, 0))
check("error context menu blocked", "无可复制" in w._toast_lb.text() and
      QApplication.clipboard().text() == clipboard_before, w._toast_lb.text())
w._toast_timer.stop(); w._toast_lb.hide()
w._clear_all()

# ======== 23. 位域鼠标选择 (Shift+拖拽) ========
print("=== 23. Bit-field mouse selection ===")

w._clear_all(); w._radix = 16
w._value = 0x12D687; w._refresh_display()

w._bit_indicator._sel_apply(4, 7)
check("selection stored", w._bit_indicator._sel == (4, 7), str(w._bit_indicator._sel))
check("selection label text", "SEL 7:4" in w._sel_label.text() and "0x8" in w._sel_label.text(),
      w._sel_label.text())
check("selection value", w._sel_value == 0x8, hex(w._sel_value))
check("selection label visible", not w._sel_label.isHidden())

w._bit_indicator._sel_apply(7, 4)
check("selection order normalized", w._bit_indicator._sel == (4, 7), str(w._bit_indicator._sel))

w._bit_indicator._sel_apply(0, 0)
check("single-bit selection", w._bit_indicator._sel == (0, 0) and w._sel_value == 1,
      f"sel={w._bit_indicator._sel} v={w._sel_value}")

# 数值变化 → 选中位域值实时更新
w._bit_indicator._sel_apply(4, 7)
left_click(7)   # 0x12D687 bit7=1 → 翻转为 0
check("selection value tracks input", w._sel_value == 0x0 and "0x0" in w._sel_label.text(),
      f"v={w._sel_value} label={w._sel_label.text()}")
w._bit_indicator.clear_selection()
check("selection cleared", w._bit_indicator._sel is None and w._sel_label.isHidden())

# 位宽缩小 → 越界选择自动清除
w._clear_all()
w._bit_indicator.set_val(0xDEADBEEFCAFEBABE, 64)
w._bit_indicator._sel_apply(60, 63)
check("high selection set", w._bit_indicator._sel == (60, 63), str(w._bit_indicator._sel))
w._refresh_display()   # _bit_width=16 → set_val 触发清除
check("width shrink clears selection", w._bit_indicator._sel is None and w._sel_label.isHidden())

# AC 清除选择
w._refresh_display()
w._bit_indicator._sel_apply(4, 7)
w._clear_all()
check("AC clears selection", w._bit_indicator._sel is None and w._sel_value is None)
check("sel label widget", hasattr(w, "_sel_label"))
check("selection signal handler", hasattr(w, "_on_selection_changed"))

print()
print(f"TOTAL: {passed} passed, {failed} failed")
if failed > 0:
    print("SOME TESTS FAILED!")
else:
    print("ALL TESTS PASSED!")

w.close(); app.quit()
sys.exit(failed)
