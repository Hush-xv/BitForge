"""BitForge 计算状态机: 纯 Python, 无 Qt 依赖。

CalculatorState 持有计算器全部数据字段 (唯一真相源) 与转移逻辑;
UI 层 (main_window.BitForge) 通过方法驱动状态, 读取字段后自行刷新控件。
转移方法的约定:
- 返回 Optional[str]: 需要弹 Toast 的消息 (输入超限等), None 表示无消息
- equals() 返回 (错误消息|None, (值, 来源)|None): 错误消息非空时已进入错误态
- 撤销/重做栈与快照在状态内部; 恢复时的控件同步由 UI 层完成
"""
from dataclasses import dataclass
from typing import Optional, Tuple

from .core import BIT_MASKS, OP_SYMBOLS, RADIX_DIGITS, clamp, dlog, rotate_left, rotate_right, to_signed


def compute(op, l, r, b=64, signed=False):
    """按键运算的纯函数实现 (原 BitForge._compute)。"""
    if op == "add": return l + r
    if op == "sub": return l - r
    if op == "mul": return l * r
    if op == "div":
        if r == 0: raise ZeroDivisionError()
        if not signed: return l // r
        left, right = to_signed(clamp(l, b), b), to_signed(clamp(r, b), b)
        if right == 0: raise ZeroDivisionError()
        dlog("signed compute", op, left, right, "bits", b)
        return (abs(left) // abs(right)) * (-1 if (left < 0) != (right < 0) else 1)
    if op == "mod":
        if r == 0: raise ZeroDivisionError()
        if not signed: return l % r
        left, right = to_signed(clamp(l, b), b), to_signed(clamp(r, b), b)
        if right == 0: raise ZeroDivisionError()
        quotient = (abs(left) // abs(right)) * (-1 if (left < 0) != (right < 0) else 1)
        dlog("signed compute", op, left, right, "bits", b)
        return left - quotient * right
    if op == "and": return l & r
    if op == "or":  return l | r
    if op == "xor": return l ^ r
    if op == "lsh":
        if r < 0: raise ValueError("移位数不能为负")
        return 0 if r >= 64 else l << r   # 自动位宽允许结果扩展到 64 bit
    if op == "rsh":
        if r < 0: raise ValueError("移位数不能为负")
        if r >= b: return -1 if signed and to_signed(clamp(l, b), b) < 0 else 0
        if signed:
            left = to_signed(clamp(l, b), b)
            dlog("signed compute", op, left, r, "bits", b)
            return left >> r
        return l >> r
    if op == "rol": return rotate_left(l, b, r)
    if op == "ror": return rotate_right(l, b, r)
    return l


@dataclass(frozen=True)
class CalcSnapshot:
    """撤销/重做快照: 仅计算状态, 历史与偏好有意不参与撤销。"""
    value: int
    entry: str
    radix: int
    bit_width: int
    locked: bool
    signed: bool
    new_entry: bool
    error: bool
    pending: Optional[dict]
    last_op: Optional[dict]


class CalculatorState:
    def __init__(self):
        self.value = 0; self.entry = "0"; self.radix = 10; self.bit_width = 8
        self.new_entry = True; self.signed = False; self.locked = False
        self.pending = None; self.error = False; self.last_op = None
        self._undo_stack = []   # 当前会话撤销栈；不写入设置，避免恢复旧计算值
        self._redo_stack = []
        self.restoring = False  # 恢复期间抑制 _record_undo (UI 层同步控件时同样生效)

    # ---- 视图 ----
    @property
    def active_op(self):
        """当前应高亮的运算符: 待定运算且第二操作数尚未输入。"""
        return self.pending["op"] if (self.pending is not None and self.new_entry) else None

    # ---- 撤销 / 重做 ----
    def snapshot(self):
        return CalcSnapshot(
            value=self.value, entry=self.entry, radix=self.radix,
            bit_width=self.bit_width, locked=self.locked, signed=self.signed,
            new_entry=self.new_entry, error=self.error,
            pending=None if self.pending is None else dict(self.pending),
            last_op=None if self.last_op is None else dict(self.last_op))

    def apply_snapshot(self, s: CalcSnapshot):
        self.value = s.value; self.entry = s.entry; self.radix = s.radix
        self.bit_width = s.bit_width; self.locked = s.locked; self.signed = s.signed
        self.new_entry = s.new_entry; self.error = s.error
        self.pending = None if s.pending is None else dict(s.pending)
        self.last_op = None if s.last_op is None else dict(s.last_op)

    def record_undo(self):
        if self.restoring: return
        snapshot = self.snapshot()
        if self._undo_stack and self._undo_stack[-1] == snapshot: return
        self._undo_stack.append(snapshot)
        del self._undo_stack[:-50]
        self._redo_stack.clear()
        dlog("undo snapshot", "undo", len(self._undo_stack))

    def undo(self) -> bool:
        if not self._undo_stack: return False
        self._redo_stack.append(self.snapshot())
        self.apply_snapshot(self._undo_stack.pop())
        return True

    def redo(self) -> bool:
        if not self._redo_stack: return False
        self._undo_stack.append(self.snapshot())
        self.apply_snapshot(self._redo_stack.pop())
        return True

    # ---- 转移 ----
    def enter_error(self):
        self.error = True; self.pending = None; self.last_op = None

    def input_digit(self, d) -> Optional[str]:
        if self.error: self.clear_all()
        if d not in RADIX_DIGITS.get(self.radix, ""):
            dlog("digit rejected:", d, "radix:", self.radix); return None
        mx = {2: self.bit_width if self.locked else 64, 8: 22, 10: 20, 16: 16}[self.radix]
        if self.new_entry:
            candidate = d
        elif self.entry == "0":
            candidate = d   # 前导零不叠加
        else:
            candidate = self.entry + d
            if len(candidate) > mx:
                dlog("input max length:", self.entry, "radix:", self.radix)
                return "当前位宽已达输入上限"
        try: value = int(candidate, self.radix)
        except ValueError:
            dlog("int parse failed:", candidate, "radix:", self.radix); return None
        bits = self.bit_width if self.locked else 64
        if value > BIT_MASKS[bits]:
            dlog("input overflow:", candidate, "bits:", bits)
            return f"超出当前 {bits} 位范围"
        self.record_undo()
        if self.new_entry:
            self.new_entry = False
        self.entry = candidate; self.value = value
        self.sync_autowidth()
        return None

    def clear_all(self, record_undo=True):
        if record_undo: self.record_undo()
        self.value = 0; self.entry = "0"; self.pending = None; self.new_entry = True
        self.bit_width = 8; self.locked = False; self.error = False; self.last_op = None

    def backspace(self):
        if self.error: self.clear_all(); return
        if self.new_entry: return
        self.record_undo()
        if len(self.entry) <= 1: self.entry = "0"; self.new_entry = True
        else: self.entry = self.entry[:-1]
        try:
            v = int(self.entry, self.radix) if self.entry else 0; self.value = clamp(v, 64)
        except ValueError:
            # 有符号负数退格到 "-" 时无法解析, 归零避免卡键
            self.entry = "0"; self.value = 0; self.new_entry = True
        self.sync_autowidth()

    def apply_operator(self, op):
        if self.error: self.clear_all(); return
        self.record_undo()
        if op == "not":
            # 待定运算存在时 NOT 作用于等待中的操作数, 保留待定关系
            if self.pending is not None and self.new_entry:
                bits = self.pending.get("bits", self.bit_width)   # 与随后的 = 使用同一位宽
                self.pending["lhs"] = clamp(~self.pending["lhs"], bits)
                self.value = self.pending["lhs"]
                self.sync_autowidth()
                return
            bits = self.bit_width if self.locked else 64
            self.value = clamp(~self.value, bits); self.entry = self.format_entry(self.value)
            self.new_entry = True; self.pending = None
            self.sync_autowidth()
            return
        # 尚未输入第二个操作数 → 替换运算符, 不提前计算
        if self.pending is not None and self.new_entry:
            self.pending = {"op": op, "lhs": self.pending["lhs"], "bits": self.bit_width,
                            "locked": self.locked, "signed": self.signed}
            return
        if self.pending is not None: self.evaluate()
        self.pending = {"op": op, "lhs": self.value, "bits": self.bit_width,
                        "locked": self.locked, "signed": self.signed}; self.new_entry = True

    def equals(self) -> Tuple[Optional[str], Optional[Tuple[int, str]]]:
        """按 =。返回 (错误消息, 需记录的历史 (值, 来源))。"""
        if self.pending is not None or self.last_op is not None: self.record_undo()
        if self.pending is not None:
            self.last_op = {"op": self.pending["op"], "rhs": self.value,
                            "bits": self.pending.get("bits", self.bit_width),
                            "locked": self.pending.get("locked", self.locked),
                            "signed": self.pending.get("signed", self.signed)}
            sym = OP_SYMBOLS.get(self.pending["op"], self.pending["op"])
            src = f"{self.pending['lhs']} {sym} {self.value}"
            err = self.evaluate()
            if err: return err, None
            self.new_entry = True
            return None, (self.value, src)
        if self.last_op is not None:
            # 连按 =: 重复上次运算 (结果 op rhs)
            try:
                bits = self.last_op.get("bits", self.bit_width)
                r = compute(self.last_op["op"], self.value, self.last_op["rhs"], bits,
                            self.last_op.get("signed", self.signed))
            except (ZeroDivisionError, ValueError):
                self.enter_error()
                return "除数不能为 0", None
            if self.last_op.get("locked", False): self.bit_width = bits; self.locked = True; r = clamp(r, bits)
            self.value = self.fit_value(r); self.entry = self.format_entry(self.value)
            sym = OP_SYMBOLS.get(self.last_op["op"], self.last_op["op"])
            self.new_entry = True
            return None, (self.value, f"重复 {self.value} {sym} {self.last_op['rhs']}")
        return None, None

    def evaluate(self) -> Optional[str]:
        """应用待定运算。出错时进入错误态并返回错误消息。"""
        if self.pending is None: return None
        op, lhs, rhs = self.pending["op"], self.pending["lhs"], self.value
        bits = self.pending.get("bits", self.bit_width)
        try: r = compute(op, lhs, rhs, bits, self.pending.get("signed", self.signed))
        except (ZeroDivisionError, ValueError):
            self.enter_error()
            return "除数不能为 0" if op in ("div", "mod") and rhs == 0 else "计算失败"
        if self.pending.get("locked", False):
            self.bit_width = bits; self.locked = True; r = clamp(r, bits)
        elif op in ("rol", "ror"):
            self.bit_width = bits; self.locked = True
        self.value = self.fit_value(r); self.entry = self.format_entry(self.value); self.pending = None
        return None

    def flip_signed(self):
        self.record_undo()
        self.signed = not self.signed
        self.sync_autowidth()

    def radix_switch(self, r) -> bool:
        if self.radix == r or self.error: return False
        self.record_undo()
        self.radix = r; self.new_entry = False; self.entry = self.format_entry(self.value)
        return True

    def set_bit_width(self, b) -> bool:
        if b not in BIT_MASKS:
            dlog("bit width rejected:", b)
            return False
        self.record_undo()
        self.bit_width = b; self.locked = True
        self.entry = self.format_entry(self.value)
        return True

    def load_value(self, v, record_undo=True) -> bool:
        """载入一个值。返回是否从错误态清除 (UI 需同步锁按钮与动画)。"""
        cleared = False
        if record_undo: self.record_undo()
        if self.error:
            self.clear_all(record_undo=False); cleared = True
        self.value = self.fit_value(v)
        self.entry = self.format_entry(self.value)
        self.new_entry = False
        self.pending = None
        return cleared

    # ---- 格式化 ----
    def fit_value(self, value, signed_64=False):
        """载入或计算出的值先适配位宽, 再格式化为可编辑 entry。"""
        raw = value
        if self.signed and not self.locked and signed_64 and raw >= (1 << 63):
            raw = to_signed(raw, 64)
        if not self.locked:
            self.bit_width = self.calc_bw(raw)
        return clamp(raw, self.bit_width)

    def calc_bw(self, v):
        if self.locked: return self.bit_width
        if self.signed and v < 0:
            for b in (8, 16, 32, 64):
                if v >= -(1 << (b - 1)):
                    return b
        if v == 0: return 8
        n = v.bit_length()
        if n <= 8: return 8
        if n <= 16: return 16
        if n <= 32: return 32
        return 64

    def format_entry(self, v):
        return self.format_radix(v, self.radix)

    def format_radix(self, v, radix, pad=False):
        u = clamp(v, self.bit_width)
        if radix == 16: return format(u, f"0{self.bit_width // 4}X" if pad else "X")
        if radix == 8: return format(u, "o")
        if radix == 2: return format(u, f"0{self.bit_width}b" if pad else "b")
        return str(to_signed(u, self.bit_width))

    def sync_autowidth(self):
        """显示刷新前的自动位宽同步 (未锁定时跟随当前值)。"""
        self.bit_width = self.calc_bw(self.value)
