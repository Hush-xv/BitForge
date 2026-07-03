"""
BitForge — 组合测试套件
用法: python test_bitforge.py
每次修改升版前运行，确保所有功能正常。
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from PyQt5.QtWidgets import QApplication
from bitforge import BitForge, clamp, to_signed

app = QApplication(sys.argv)
w = BitForge()
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
    w._on_bit_click(w._v ^ (1 << bit))

# 模拟右键清除 bit
def right_click(bit):
    w._on_bit_click(w._v & ~(1 << bit))

# ======== 1. 进制切换 + 输入组合 ========
print("=== 1. Radix switch + input ===")

w._ac(); w._r = 10
for c in "999": w._dig(c)
check("DEC input 999", w._v == 999, str(w._v))
w._rad(16)
check("switch to HEX keeps value", w._v == 999, str(w._v))
check("HEX display string", w._d == "3E7", w._d)

w._dig("8")
check("HEX append 8 -> 0x3E78", w._v == 0x3E78, hex(w._v))
w._rad(8)
check("switch OCT keeps value", w._v == 0x3E78, str(w._v))
# _fmt(0x3E78, 8) = format(15992,"o") = "37170"
check("OCT display string", w._d == "37170", w._d)
w._dig("7")
check("OCT append 7", w._v == int("371707", 8), hex(w._v))

w._rad(2)
check("switch BIN keeps value", w._v == int("371707", 8), str(w._v))

# ======== 2. 输入 + 运算 + 进制切换组合 ========
print("=== 2. Input + operation + radix switch ===")

w._ac(); w._r = 10
for c in "123": w._dig(c)
w._op("add"); w._v = 456; w._eq()
check("123+456=579", w._v == 579, str(w._v))
w._rad(16)
check("result in HEX 0x243", w._d == "243", w._d)

w._ac(); w._r = 16
for c in "FF": w._dig(c)
w._op("mul"); w._v = 2; w._eq()
check("0xFF*2=510", w._v == 510, str(w._v))
w._rad(10)
check("result in DEC 510", w._d == "510", w._d)

w._ac(); w._r = 16
for c in "F0": w._dig(c)
w._op("or"); w._v = 0x0F; w._eq()
check("0xF0 | 0x0F = 0xFF", w._v == 0xFF, hex(w._v))
w._op("xor"); w._v = 0xFF; w._eq()
check("0xFF ^ 0xFF = 0", w._v == 0, hex(w._v))

# ======== 3. 位宽操作组合 ========
print("=== 3. Bit-width operations ===")

w._ac()
check("AC: bw=8 locked=False", w._bw == 8 and not w._locked)
w._v = 0x100; w._rnd()
check("0x100 -> bw=16 auto", w._bw == 16, str(w._bw))
w._step_bw_up()
check("[+] -> bw=32 locked", w._bw == 32 and w._locked)
w._step_bw_up()
check("[+] -> bw=64", w._bw == 64)
w._step_bw_dn()
check("[-] -> bw=32 locked", w._bw == 32 and w._locked)

w._v = 0x1; w._rnd()
check("locked: small value keeps bw=32", w._bw == 32, str(w._bw))
w._v = 0x100000000; w._rnd()
check("locked: big value keeps bw=32", w._bw == 32, str(w._bw))

w._locked = False; w._rnd()
check("unlock: bw recalc for 0x100000000", w._bw == 64, str(w._bw))
w._v = 0x1; w._rnd()
check("unlock: small value shrinks bw", w._bw == 8, str(w._bw))

# ======== 4. 点击 bit 各种组合 ========
print("=== 4. Bit click combinations ===")

w._ac()
left_click(0); check("L click bit0 -> 1", w._v == 1, hex(w._v))
left_click(0); check("L click bit0 again -> 0", w._v == 0, hex(w._v))

left_click(0); left_click(1); left_click(2)
check("L click bits 0,1,2 -> 0x7", w._v == 0x7, hex(w._v))

w._v = 0xFF; w._rnd()
right_click(3)
check("R click bit3 of 0xFF -> 0xF7", w._v == 0xF7, hex(w._v))

w._v = 0; w._rnd()
left_click(4); check("L click bit4 -> 0x10", w._v == 0x10, hex(w._v))
left_click(4); check("L click bit4 again -> 0", w._v == 0, hex(w._v))

# ======== 5. 掩码组合 ========
print("=== 5. Mask operations ===")

w._v = 0xFFFF; w._rnd()
w._bi.set_mask(0x00FF)
check("mask set 0x00FF", w._bi._mask == 0x00FF)
w._bi.set_mask(0)
check("mask cleared", w._bi._mask == 0)
w._bi.set_mask(0xFF00)
check("mask re-set 0xFF00", w._bi._mask == 0xFF00)
w._bi.set_mask(0)

# ======== 6. 有符号/无符号组合 ========
print("=== 6. Signed/Unsigned ===")

w._v = 0x7FFFFFFF; w._signed = False; w._rnd()
check("unsigned 0x7FFFFFFF", "2147483647" in w._ax["DEC"].text())
w._toggle_sign()
check("signed 0x7FFFFFFF", "2147483647" in w._ax["DEC"].text())
w._toggle_sign()

w._v = 0x80000000; w._rnd()
t = w._ax["DEC"].text()
check("unsigned 0x80000000", "2147483648" in t, t)
w._toggle_sign()
t = w._ax["DEC"].text()
check("signed 0x80000000", "-2147483648" in t, t)
w._toggle_sign()

# ======== 7. 运算组合 ========
print("=== 7. Arithmetic combinations ===")

w._ac(); w._v = 10; w._op("add"); w._v = 20; w._eq()
check("10+20=30", w._v == 30)
w._op("mul"); w._v = 3; w._eq()
check("30*3=90", w._v == 90)
w._op("sub"); w._v = 15; w._eq()
check("90-15=75", w._v == 75)
w._op("div"); w._v = 5; w._eq()
check("75/5=15", w._v == 15)

w._ac(); w._v = 0xFF; w._op("not")
check("NOT 0xFF on 64bit", w._v == 0xFFFFFFFFFFFFFF00, hex(w._v))
w._op("not")
check("NOT NOT 0xFF = 0xFF", w._v == 0xFF, hex(w._v))

w._ac(); w._v = 1; w._op("lsh"); w._v = 10; w._eq()
check("1<<10=1024", w._v == 1024)
w._op("rsh"); w._v = 5; w._eq()
check("1024>>5=32", w._v == 32)

w._ac(); w._v = 100; w._op("mod"); w._v = 30; w._eq()
check("100%30=10", w._v == 10)

w._ac(); w._v = 10; w._op("div"); w._v = 0; w._eq()
check("10/0=Error", w._e and "Error" in w._dl.text())

# ======== 8. 退格组合 ========
print("=== 8. Backspace combinations ===")

w._ac(); w._r = 16
for c in "ABCDE": w._dig(c)
check("input ABCDE", w._d == "ABCDE")
w._bs(); check("BS -> ABCD", w._d == "ABCD")
w._bs(); check("BS -> ABC", w._d == "ABC")
w._bs(); check("BS -> AB", w._d == "AB")
w._bs(); check("BS -> A", w._d == "A")
w._bs(); check("BS -> 0", w._d == "0")
w._bs(); check("BS at 0 stays 0", w._d == "0")

w._ac(); w._r = 16
for c in "AB": w._dig(c)
check("input AB", w._v == 0xAB)
left_click(0)
check("flip bit0 -> 0xAA", w._v == 0xAA, hex(w._v))
w._bs()
check("then BS -> A", w._d == "A", w._d)

w._e = True; w._bs()
check("BS in Error -> AC", w._v == 0 and not w._e)

# ======== 9. 边界条件 ========
print("=== 9. Edge cases ===")

w._ac()
check("AC v=0 bw=8", w._v == 0 and w._bw == 8)

w._v = 0xFF; w._rnd()
check("8-bit max 0xFF", w._v == 0xFF and w._bw == 8)

w._v = 0xFFFF; w._rnd()
check("16-bit max 0xFFFF", w._v == 0xFFFF and w._bw == 16)

w._v = 0xFFFFFFFF; w._rnd()
check("32-bit max 0xFFFFFFFF", w._v == 0xFFFFFFFF and w._bw == 32)

w._v = 0x100000000; w._rnd()
check("64-bit entry", w._v == 0x100000000 and w._bw == 64)

w._v = 0xFF; w._r = 16; w._ac(); w._rnd()
check("HEX prefix", w._dl.text().startswith("0x"), w._dl.text())

w._ac(); w._r = 10; w._rnd()
check("DEC 0 display", w._dl.text() == "0")

w._on_mask_changed("")
check("empty mask clears", w._bi._mask == 0)
w._on_mask_changed("0xDC")
check("mask 0xDC", w._bi._mask == 0xDC, hex(w._bi._mask))
w._on_mask_changed("")
check("empty mask clears again", w._bi._mask == 0)

# ======== 10. 功能完整性 ========
print("=== 10. Feature integrity ===")
check("valueChanged signal", hasattr(w._bi, "valueChanged"))
check("lock button", hasattr(w, "_lock_btn"))
check("step up/down", hasattr(w, "_step_bw_up") and hasattr(w, "_step_bw_dn"))
check("toast", hasattr(w, "_toast"))
check("v_ani", hasattr(w, "_v_ani"))
check("about", hasattr(w, "_show_about"))
ico = os.path.join(os.path.dirname(__file__), "bitforge.ico")
check("icon file", os.path.exists(ico))

print()
print(f"TOTAL: {passed} passed, {failed} failed")
if failed > 0:
    print("SOME TESTS FAILED!")
else:
    print("ALL TESTS PASSED!")

w.close(); app.quit()
sys.exit(failed)
