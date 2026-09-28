"""BitForge 主题配色: LIGHT_C / DARK_C, _apply_theme_colors 切换。"""

C = {
    "win":"#F0F2F5", "dsp_bg":"#FFFFFF", "dsp_fg":"#101216", "dsp_neg":"#FF6D7F",
    "aux_bg":"#F6F7FA", "aux_fg":"#3A3D48", "title":"#181A20", "sub":"#687080",
    "ver":"#8D96A6", "hint":"#98A0B0", "tb_bg":"#FFFFFF", "tb_bdr":"#D4D4D4",
    "rad_on":"#AF92FB", "rad_off":"#8890A0", "num_bg":"#D4D4D4", "num_fg":"#181A20",
    "dim_bg":"#E1E3E6", "dim_fg":"#A8AEB8", "toast_bg":"#53A9FD", "toast_fg":"#102C46",
    "success":"#58C667", "warning":"#FFB45B", "lock":"#E8D836",
    "op_bg":"#DDEEFD", "op_fg":"#1D6FBE", "op_active":"#2D7FD6",
    "bit_bg":"#EFEAFD", "bit_fg":"#6B4FD8", "eq_bg":"#AF92FB", "eq_fg":"#261A3E",
    "ac_bg":"#FF6D7F", "ac_fg":"#4A1019", "bs_bg":"#FFDDE1", "bs_fg":"#B8323F",
    "bit_on":"#AF92FB", "bit_on_fg":"#261A3E", "bit_off":"#7A8290",
}
LIGHT_C = C.copy()
DARK_C = {**LIGHT_C,
    "win":"#171A20", "dsp_bg":"#20242C", "dsp_fg":"#F3F5F8", "dsp_neg":"#FF6D7F",
    "aux_bg":"#292F3A", "aux_fg":"#D9DEE7", "title":"#F3F5F8", "sub":"#AAB3C2",
    "ver":"#7F8A9B", "hint":"#8590A1", "tb_bg":"#20242C", "tb_bdr":"#454E5D",
    "rad_on":"#AF92FB", "rad_off":"#AAB3C2", "num_bg":"#3A414C", "num_fg":"#F3F5F8",
    "dim_bg":"#272D37", "dim_fg":"#687487", "toast_bg":"#53A9FD", "toast_fg":"#102C46",
    "op_bg":"#1E3448", "op_fg":"#8FC5F5", "op_active":"#53A9FD",
    "bit_bg":"#32294B", "bit_fg":"#CFBBFF", "eq_bg":"#AF92FB", "eq_fg":"#261A3E",
    "ac_bg":"#6A3540", "ac_fg":"#FFE7EA", "bs_bg":"#5A2F35", "bs_fg":"#FFB9C1",
    "bit_on":"#AF92FB", "bit_on_fg":"#261A3E", "bit_off":"#687487",
}
BH = 0    # border_height：取消透明底边，避免下圆角被截断
BR = 12   # border_radius：增强按键四角的视觉辨识
IR = 12   # inner_radius

# =====================================================================
#  设计 token: 间距 / 圆角阶梯 (UI 升级统一规格, 新样式一律取值于此)
# =====================================================================
SP = {"xs": 4, "s": 6, "m": 8, "l": 12, "xl": 16}   # spacing
RD = {"s": 8, "m": 12, "l": 16, "xl": 20}           # radius
