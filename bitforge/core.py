"""BitForge 纯逻辑层: 数学工具 / 表达式解析 / 数值解析。无 Qt 依赖。"""
import os
import re

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
OP_SYMBOLS = {"add": "+", "sub": "\u2212", "mul": "\u00d7", "div": "\u00f7", "mod": "%",
              "and": "AND", "or": "OR", "xor": "XOR", "lsh": "<<", "rsh": ">>",
              "rol": "ROL", "ror": "ROR"}
def ellipsize(s, n=24):
    """长文本截断 (错误消息/Toast/菜单项用), 超长以省略号收尾。"""
    return s if len(s) <= n else s[:n] + "…"

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

def evaluate_expression(text, b=64, signed=False):
    """Evaluate a bounded programmer-calculator expression without Python eval."""
    tokens=[]; pos=0
    while pos<len(text):
        m=_EXPR_TOKEN.match(text,pos)
        if not m:
            if text[pos:].strip():
                raise ValueError(f"无法识别：{ellipsize(text[pos:].strip())}")
            break
        token=m.group(1); tokens.append(token.upper() if token.isalpha() else token); pos=m.end()
    if not tokens: raise ValueError("请输入表达式")
    depth=prefix_count=0
    for token in tokens:
        if token=="(":
            depth+=1; prefix_count=0
            if depth>128:
                dlog("expression rejected: nesting depth", depth)
                raise ValueError("表达式嵌套过深")
        elif token==")":
            depth-=1; prefix_count=0
        elif token in ("~","NOT","+","-"):
            prefix_count+=1
            if prefix_count>128:
                dlog("expression rejected: prefix depth", prefix_count)
                raise ValueError("表达式前缀过深")
        else:
            prefix_count=0
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
            if right>=b:
                value=-1 if signed and to_signed(left,b)<0 else 0
            else:
                value=to_signed(left,b)>>right if signed else left>>right
        elif op=="+": value=left+right
        elif op=="-": value=left-right
        elif op=="*": value=left*right
        elif op=="/":
            if right==0: raise ValueError("除数不能为 0")
            if signed:
                left,right=to_signed(left,b),to_signed(right,b)
                value=(abs(left)//abs(right))*(-1 if (left<0) != (right<0) else 1)
            else: value=left//right
        elif op=="%":
            if right==0: raise ValueError("除数不能为 0")
            if signed:
                left,right=to_signed(left,b),to_signed(right,b)
                quotient=(abs(left)//abs(right))*(-1 if (left<0) != (right<0) else 1)
                value=left-quotient*right
            else: value=left%right
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
            raise ValueError(f"期望数值，得到 {ellipsize(token)}")

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
    if index!=len(tokens): raise ValueError(f"意外标记：{ellipsize(tokens[index])}")
    return value

def parse_number(text):
    """Parse a clipboard, mask, or bit-field integer without using eval."""
    raw=text.strip().replace(",","").replace("_","").replace(" ","")
    if not raw: raise ValueError("请输入数值")
    sign=1
    if raw[0] in "+-":
        sign=-1 if raw[0]=="-" else 1; raw=raw[1:]
    if not raw: raise ValueError("缺少数值")
    low=raw.lower()
    if low.endswith("h"):
        digits=raw[:-1]; base=16
    elif low.startswith("0x"):
        digits=raw[2:]; base=16
    elif low.startswith("0b"):
        digits=raw[2:]; base=2
    elif low.startswith("0o"):
        digits=raw[2:]; base=8
    elif any(c in "abcdef" for c in low):
        digits=raw; base=16
    else:
        digits=raw; base=10
    if not digits: raise ValueError("缺少数值")
    return sign*int(digits,base)

def dec_group(text, sep=","):
    """十进制千分位分组 (仅用于显示; 复制值保持原样)。非纯数字文本原样返回。"""
    sign=""
    if text.startswith("-"):
        sign,text="-",text[1:]
    if not text.isdigit():
        return sign+text
    parts=[]
    while len(text)>3:
        parts.append(text[-3:]); text=text[:-3]
    parts.append(text)
    return sign+sep.join(reversed(parts))
