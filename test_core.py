"""
BitForge — 纯逻辑测试套件 (无 Qt 应用实例 / 无 GUI, 秒级)
用法: python test_core.py
覆盖: core 数学工具 / 表达式求值 / 数值解析 / compute / CalculatorState 状态机 / 撤销重做
UI 集成回归见 test_bitforge.py — 发布前两者都要跑。
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))

from bitforge.core import (BIT_MASKS, byte_swap, clamp, evaluate_expression,
                           extract_field, parse_number, rotate_left, rotate_right,
                           to_signed, write_field)
from bitforge.state import CalculatorState, compute

passed = 0; failed = 0

def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
    else:
        failed += 1
        if detail:
            safe_detail=str(detail).encode("ascii","backslashreplace").decode("ascii")
            print(f"  FAIL {name}  ({safe_detail})")
        else:
            print(f"  FAIL {name}")

def fresh(radix=10, signed=False, locked=False, bit_width=8):
    s=CalculatorState()
    s.radix=radix; s.signed=signed; s.locked=locked; s.bit_width=bit_width
    return s

# ======== 1. 数学工具 ========
print("=== 1. Math helpers ===")

check("clamp masks 8bit", clamp(0x1FF, 8) == 0xFF)
check("clamp negative", clamp(-1, 8) == 0xFF)
check("clamp 64bit", clamp(1 << 70, 64) == 0, hex(clamp(1 << 70, 64)))
check("to_signed 8bit", to_signed(0xFF, 8) == -1)
check("to_signed 64bit", to_signed((1 << 64) - 1, 64) == -1)
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

# ======== 2. 表达式求值 ========
print("=== 2. Expression evaluation ===")

check("expression precedence", evaluate_expression("1 + 2 * 3") == 7)
check("expression parentheses", evaluate_expression("(1 + 2) * 3") == 9)
check("expression radix and shift", evaluate_expression("(0x20 << 3) | 0x07") == 0x107)
check("expression aliases", evaluate_expression("NOT 0x0F AND 0xF0", 8) == 0xF0)
check("expression wraps at bit-width", evaluate_expression("0xFF + 2", 8) == 1)
check("expression 64-bit division exact", evaluate_expression("0xFFFFFFFFFFFFFFFE / 2") == 0x7FFFFFFFFFFFFFFF)
check("expr negative shift -> 0", evaluate_expression("1 << -1", 64) == 0)
check("expr negative rshift -> 0", evaluate_expression("1 >> -1", 64) == 0)
check("expr shift 65 -> 0", evaluate_expression("1 << 65", 64) == 0)
check("expr rshift huge -> 0", evaluate_expression("99 >> 9999999999", 64) == 0)
check("signed minimum divided by -1 wraps", evaluate_expression("-128 / -1", 8, True) == 0x80)
check("signed maximum-width right shift keeps sign fill", evaluate_expression("-128 >> 8", 8, True) == 0xFF)
check("signed expression division", evaluate_expression("-2 / 2", 8, True) == 0xFF)
check("signed expression right shift", evaluate_expression("-128 >> 1", 8, True) == 0xC0)
try:
    evaluate_expression("1 / 0")
    check("expression division error", False)
except ValueError as exc:
    check("expression division error", "除数不能为 0" in str(exc), str(exc))
try:
    evaluate_expression("("*129 + "1" + ")"*129)
    check("deep expression returns a validation error", False)
except ValueError:
    check("deep expression returns a validation error", True)

# ======== 3. 数值解析 ========
print("=== 3. Number parsing ===")

check("parse signed prefixed HEX", parse_number("-0xFF") == -255)
check("parse grouped decimal", parse_number("1_000,000") == 1000000)
check("parse h suffix", parse_number("FFh") == 0xFF)
check("parse single bare HEX", parse_number("A") == 0xA)
check("parse 0b prefix", parse_number("0b1010") == 0xA)
check("parse 0o prefix", parse_number("0o17") == 0xF)
check("parse decimal", parse_number("57005") == 0xDEAD)
try:
    parse_number("zzz")
    check("parse invalid raises", False)
except ValueError:
    check("parse invalid raises", True)

# ======== 4. compute 纯函数 ========
print("=== 4. compute() ===")

check("signed helper division truncates toward zero", compute("div", 0xFE, 2, 8, True) == -1)
check("signed helper modulo keeps dividend sign", compute("mod", 0xFD, 2, 8, True) == -1)
check("signed helper right shift sign-extends", compute("rsh", 0x80, 1, 8, True) == -64)
check("left shift beyond 64-bit range is zero", compute("lsh", 1, 64, 8) == 0)
try:
    compute("rsh", 1, -1, 8)
    check("negative keypad shift is rejected", False)
except ValueError:
    check("negative keypad shift is rejected", True)

# ======== 5. 状态机: 输入 ========
print("=== 5. CalculatorState: digit input ===")

s=fresh()
for c in "999": s.input_digit(c)
check("DEC input 999", s.value == 999 and s.entry == "999", f"{s.value}/{s.entry}")
s.radix_switch(16)
check("switch to HEX keeps value", s.value == 999 and s.entry == "3E7", f"{s.value}/{s.entry}")
s.input_digit("8")
check("HEX append 8 -> 0x3E78", s.value == 0x3E78 and s.entry == "3E78", f"{s.value}/{s.entry}")
s.radix_switch(8)
check("switch OCT reformats entry", s.entry == "37170", s.entry)
s.radix_switch(2)
check("switch BIN keeps value", s.value == 0x3E78 and s.entry == format(0x3E78, "b"), f"{hex(s.value)}/{s.entry}")

s=fresh()
s.input_digit("0"); s.input_digit("0"); s.input_digit("5")
check("leading zero strip", s.entry == "5" and s.value == 5, f"{s.entry}/{s.value}")

s=fresh(locked=True, bit_width=8)
msg=s.input_digit("2"); msg=s.input_digit("5")
check("locked DEC input 25", s.value == 25 and msg is None, f"{s.value}/{msg}")
msg=s.input_digit("6")
check("locked input rejects outside word width", s.value == 25 and s.entry == "25" and msg is not None,
      f"{s.value}/{s.entry}/{msg}")

s=fresh()
for digit in "18446744073709551616": s.input_digit(digit)
check("64-bit decimal overflow keeps last valid value",
      s.value == 1844674407370955161 and s.entry == "1844674407370955161", f"{s.value}/{s.entry}")

s=fresh(radix=2)
for digit in "1"*9: s.input_digit(digit)
check("automatic binary input grows past 8 bits", s.value == 0x1FF and s.bit_width == 16 and len(s.entry) == 9,
      f"{hex(s.value)}/{s.bit_width}/{s.entry}")

s=fresh(radix=10)
msg=s.input_digit("G")
check("invalid digit rejected silently", msg is None and s.value == 0 and s.entry == "0",
      f"{msg}/{s.value}/{s.entry}")

# ======== 6. 状态机: 运算与等号 ========
print("=== 6. CalculatorState: operators / equals ===")

s=fresh()
for c in "123": s.input_digit(c)
s.apply_operator("add"); s.value = 456; s.entry = "456"
err,mem=s.equals()
check("123+456=579", err is None and s.value == 579, f"{err}/{s.value}")
check("equals returns history source", mem == (579, "123 + 456"), str(mem))
s.radix_switch(16)
check("result in HEX 0x243", s.entry == "243", s.entry)

s=fresh()
s.value=10; s.entry="10"
s.apply_operator("add"); s.value = 20; s.entry = "20"; s.equals()
s.apply_operator("mul"); s.value = 3; s.entry = "3"; s.equals()
check("chained 30*3=90", s.value == 90, str(s.value))

# 运算符替换: 不提前计算
s=fresh()
s.value=12; s.entry="12"
s.apply_operator("add"); s.apply_operator("mul")
check("operator replace", s.pending["op"] == "mul" and s.pending["lhs"] == 12, str(s.pending))
check("active_op follows pending", s.active_op == "mul", str(s.active_op))
s.equals()
check("12*12 after replace", s.value == 144, str(s.value))
check("active_op cleared by equals", s.active_op is None, str(s.active_op))

# 连按 = 重复上次运算
s.equals()
check("repeat equals", s.value == 144*12, str(s.value))
s.equals()
check("repeat equals 2", s.value == 144*144, str(s.value))

# 输入第二操作数后 active_op 熄灭
s=fresh()
s.value=12; s.entry="12"
s.apply_operator("add")
check("active_op on new pending", s.active_op == "add", str(s.active_op))
s.input_digit("5")
check("active_op cleared by digit", s.active_op is None, str(s.active_op))

# NOT: 无待定 → 64 位取反
s=fresh()
s.value=0xFF; s.entry="FF"
s.apply_operator("not")
check("NOT 0xFF on 64bit", s.value == 0xFFFFFFFFFFFFFF00, hex(s.value))
s.apply_operator("not")
check("NOT NOT 0xFF = 0xFF", s.value == 0xFF, hex(s.value))

# NOT: 保留待定运算 (按待定位宽取反 lhs)
s=fresh(bit_width=8)
s.value=12; s.entry="12"
s.apply_operator("add"); s.apply_operator("not")
check("NOT keeps pending", s.pending is not None and s.pending["lhs"] == clamp(~12, 8),
      hex(s.pending["lhs"]) if s.pending else "None")

# 除零错误态 + 数字恢复
s=fresh()
s.value=10; s.entry="10"
s.apply_operator("div"); s.value = 0; s.entry = "0"
err,mem=s.equals()
check("division error message", err == "除数不能为 0", str(err))
check("division error clears pending/last_op", s.error and s.pending is None and s.last_op is None, str(s.pending))
s.input_digit("3")
check("digit recovers from error", not s.error and s.value == 3, f"{s.error}/{s.value}")

# ROL 使用原位宽并锁定
s=fresh(radix=16, bit_width=16)
s.value=0x8000; s.entry="8000"
s.apply_operator("rol"); s.value = 1; s.entry = "1"
s.equals()
check("ROL uses original bit-width", s.value == 1 and s.bit_width == 16 and s.locked,
      f"{hex(s.value)}/{s.bit_width}/{s.locked}")
s.apply_operator("ror"); s.value = 1; s.entry = "1"; s.equals()
check("ROR keeps bit-width", s.value == 0x8000 and s.bit_width == 16, f"{hex(s.value)}/{s.bit_width}")

# 锁定 8 位加法回绕 + 重复等号回绕
s=fresh(radix=16, locked=True, bit_width=8)
s.value=0xFF; s.entry="FF"
s.apply_operator("add"); s.value = 1; s.entry = "1"; s.equals()
check("locked 8-bit addition wraps", s.value == 0 and s.bit_width == 8 and s.locked,
      f"{hex(s.value)}/{s.bit_width}/{s.locked}")
s.apply_operator("not")
check("locked 8-bit NOT stays 8-bit", s.value == 0xFF and s.bit_width == 8, f"{hex(s.value)}/{s.bit_width}")
s.value=0xFE; s.entry="FE"
s.apply_operator("add"); s.value = 2; s.entry = "2"; s.equals()
first_repeat=s.value
s.equals()
second_repeat=s.value
check("locked repeated equals wraps", first_repeat == 0 and second_repeat == 2, f"{first_repeat}/{second_repeat}")

# ======== 7. 状态机: 退格 / 位宽 / 载入 ========
print("=== 7. CalculatorState: backspace / width / load ===")

s=fresh(radix=16)
for c in "ABCDE": s.input_digit(c)
check("input ABCDE", s.entry == "ABCDE", s.entry)
for expected in ("ABCD", "ABC", "AB", "A", "0"):
    s.backspace()
    check(f"BS -> {expected}", s.entry == expected, s.entry)
s.backspace()
check("BS at 0 stays 0", s.entry == "0" and s.value == 0, f"{s.entry}/{s.value}")

s=fresh()
s.error=True
s.backspace()
check("BS in Error -> AC", s.value == 0 and not s.error, f"{s.value}/{s.error}")

s=fresh(radix=16)
s.value=0x1FF; s.sync_autowidth()   # 直改值后同步位宽 (等价 UI 的 _refresh_display)
check("set_bit_width locks", s.set_bit_width(8) and s.bit_width == 8 and s.locked, f"{s.bit_width}/{s.locked}")
check("set_bit_width clamps entry", s.entry == "FF", s.entry)
check("set_bit_width expands", s.set_bit_width(32) and s.entry == "1FF", s.entry)
check("invalid bit-width ignored", not s.set_bit_width(12) and s.bit_width == 32, str(s.bit_width))

s=fresh()
check("load_value fits and clears pending", s.load_value(0xDEAD) is False and s.value == 0xDEAD
      and s.pending is None and not s.new_entry, f"{hex(s.value)}/{s.pending}/{s.new_entry}")
s.error=True
cleared=s.load_value(7)
check("load_value clears error state", cleared and not s.error and s.value == 7 and s.bit_width == 8,
      f"{cleared}/{s.error}/{hex(s.value)}")

s=fresh(signed=True)
check("signed paste -1 uses 8 bits", s.load_value(-1) is False and s.value == 0xFF and s.bit_width == 8
      and s.entry == "-1", f"{hex(s.value)}/{s.bit_width}/{s.entry}")

# ======== 8. 撤销 / 重做 ========
print("=== 8. Undo / redo ===")

s=fresh()
s._undo_stack.clear(); s._redo_stack.clear()
for digit in "123": s.input_digit(digit)
check("undo returns True", s.undo() is True)
check("undo restores previous digit", s.value == 12 and s.entry == "12", f"{s.value}/{s.entry}")
check("redo restores digit", s.redo() is True and s.value == 123 and s.entry == "123", f"{s.value}/{s.entry}")

s.apply_operator("add")
check("pending set", s.pending is not None and s.pending["op"] == "add", str(s.pending))
check("undo restores no pending", s.undo() is True and s.pending is None and s.value == 123, str(s.pending))
check("redo restores pending", s.redo() is True and s.pending is not None and s.pending["op"] == "add", str(s.pending))

s.set_bit_width(16)
check("undo restores automatic width", s.undo() is True and s.bit_width == 8 and not s.locked, f"{s.bit_width}/{s.locked}")
check("redo restores locked width", s.redo() is True and s.bit_width == 16 and s.locked, f"{s.bit_width}/{s.locked}")

s2=fresh()
check("undo on empty stack returns False", s2.undo() is False and s2.redo() is False)
s2.record_undo(); n=len(s2._undo_stack)
s2.record_undo()
check("record_undo dedups identical snapshots", len(s2._undo_stack) == n, f"{n}/{len(s2._undo_stack)}")
s2.input_digit("5")
check("new action clears redo stack", len(s2._redo_stack) == 0, str(len(s2._redo_stack)))
snap=s2.snapshot()
s2.input_digit("6")
s2.apply_snapshot(snap)
check("apply_snapshot restores fields", s2.value == 5 and s2.entry == "5", f"{s2.value}/{s2.entry}")

# ======== 9. 随机固定字长回归 ========
print("=== 9. Randomized word math ===")

rng=random.Random(0xB17F0)
for bits in (8, 16, 32, 64):
    mask=BIT_MASKS[bits]
    for case in range(8):
        lhs=rng.getrandbits(bits); rhs=rng.getrandbits(bits); shift=rng.randrange(0, 80)
        checks={
            "add":((lhs+rhs)&mask), "sub":((lhs-rhs)&mask), "mul":((lhs*rhs)&mask),
            "and":(lhs&rhs), "or":(lhs|rhs), "xor":(lhs^rhs),
            "lsh":(0 if shift >= 64 else (lhs << shift)&mask),
            "rsh":(0 if shift >= 64 else lhs >> shift),
            "rol":rotate_left(lhs, bits, shift), "ror":rotate_right(lhs, bits, shift),
        }
        for op, expected in checks.items():
            actual=clamp(compute(op, lhs, shift if op in ("lsh", "rsh", "rol", "ror") else rhs, bits), bits)
            check(f"random {bits}b {op} #{case}", actual == expected,
                  f"lhs=0x{lhs:X} rhs=0x{rhs:X} shift={shift} actual=0x{actual:X} expected=0x{expected:X}")
        expression=f"(0x{lhs:X} + 0x{rhs:X}) XOR 0x{lhs:X}"
        expected=((lhs+rhs)&mask)^lhs
        check(f"random {bits}b expression #{case}", evaluate_expression(expression, bits) == (expected&mask), expression)

print()
print(f"TOTAL: {passed} passed, {failed} failed")
if failed > 0:
    print("SOME TESTS FAILED!")
else:
    print("ALL TESTS PASSED!")
sys.exit(failed)
