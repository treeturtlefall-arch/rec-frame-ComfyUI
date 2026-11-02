"""電池マークにも座布団を追加した全体検証スクリプト。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from PIL import Image, ImageDraw, ImageFont
import math

from rec_config import (
    OverlayConfig,
    DEFAULT_FONT,
    BUNDLED_FONT_CHOICES,
)
from rec_overlay import (
    _load_font,
    _draw_corner_frames,
    _draw_center_cross,
    _frame_thickness,
    MARGIN_RATIO,
    ARM_LEN_RATIO,
    BAT_W_RATIO,
    BAT_H_RATIO,
    BAT_T_RATIO,
    NUB_W_RATIO,
    NUB_H_RATIO,
    BAT_BARS,
    MIN_THICKNESS,
    DOT_R_RATIO,
    REC_GAP_RATIO,
    REC_FONT_RATIO,
    MIN_REC_FONT_SIZE,
    TIMECODE_FONT_RATIO,
    RED,
)

OUT_DIR = Path(r"C:\Users\coffe\.gemini\antigravity\brain\c76ae104-18f9-43fb-8a42-8c75f360f03c")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def _tight_ink_metrics(font, text: str) -> tuple[int, int, int, int]:
    if not text or not text.strip():
        return 0, 0, 0, 0
    mask, offset = font.getmask2(text, anchor="lt")
    mb = mask.getbbox()
    if mb is None:
        return 0, 0, 0, 0
    dx = offset[0] + mb[0]
    dy = offset[1] + mb[1]
    w = mb[2] - mb[0]
    h = mb[3] - mb[1]
    return dx, dy, w, h

def create_bright_test_bg(w=1280, h=720):
    img = Image.new("RGB", (w, h))
    pixels = img.load()
    for y in range(h):
        for x in range(w):
            ny = y / h
            nx = x / w
            r = int(215 + 35 * math.sin(nx * 10) * math.cos(ny * 8))
            g = int(225 + 25 * math.cos(nx * 8 + ny * 4))
            b = int(235 + 20 * math.sin(ny * 12))
            if (x // 25 + y // 25) % 2 == 0:
                r = min(255, r + 15)
                g = min(255, g + 15)
                b = min(255, b + 15)
            pixels[x, y] = (min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b)))
    return img

def render_battery_with_bg(
    d: ImageDraw.ImageDraw,
    s: int,
    margin_x: int,
    margin_y: int,
    thickness: int,
    mono: tuple[int, int, int, int],
    bg_color: tuple[int, int, int, int],
    bg_box_opacity: float,
    pad_x: int,
    pad_y: int,
    clearance_x: int,
    clearance_y: int,
    active_bars: int = 4,
):
    bat_w = int(s * BAT_W_RATIO)
    bat_h = int(s * BAT_H_RATIO)
    nub_w = int(bat_w * NUB_W_RATIO)
    nub_h = int(bat_h * NUB_H_RATIO)
    total_w = bat_w + nub_w

    box_w = total_w + pad_x * 2
    box_h = bat_h + pad_y * 2

    # 左上L字枠の内側基準からクリアランスを確保
    box_x0 = (margin_x + thickness) + clearance_x
    box_y0 = (margin_y + thickness) + clearance_y
    box_x1 = box_x0 + box_w
    box_y1 = box_y0 + box_h

    if bg_box_opacity > 0:
        d.rectangle([box_x0, box_y0, box_x1, box_y1], fill=bg_color)

    # ボックス内で完全センタリング配置
    bat_x = box_x0 + pad_x
    bat_y = box_y0 + pad_y
    bat_t = max(MIN_THICKNESS, int(s * BAT_T_RATIO))

    # 電池本体外枠
    d.rectangle([bat_x, bat_y, bat_x + bat_w, bat_y + bat_h], outline=mono, width=bat_t)

    # 突起 (右側)
    nub_x = bat_x + bat_w
    nub_y = bat_y + (bat_h - nub_h) // 2
    d.rectangle([nub_x, nub_y, nub_x + nub_w, nub_y + nub_h], fill=mono)

    # 残量バー
    pad = bat_t + 1
    avail = bat_w - pad * 2
    if avail > 0:
        pitch = avail / BAT_BARS
        bar_w = pitch * 0.5
        bars_to_draw = max(0, min(BAT_BARS, active_bars))
        for i in range(bars_to_draw):
            bx0 = bat_x + pad + i * pitch
            by0 = bat_y + pad
            bx1 = bx0 + bar_w
            by1 = bat_y + bat_h - pad
            d.rectangle([bx0, by0, bx1, by1], fill=mono)

def render_full_overlay(
    w=1280,
    h=720,
    color="white",
    bg_box_opacity=0.5,
    font_key=DEFAULT_FONT,
    timecode_text="2026/11/01 PM 08:30",
    rec_text="REC",
    thickness_val=50,
):
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    s = min(w, h)

    mono = (255, 255, 255, 255) if color == "white" else (0, 0, 0, 255)
    bg_rgb = (0, 0, 0) if color == "white" else (255, 255, 255)
    bg_alpha = int(round(255 * bg_box_opacity))
    bg_color = (*bg_rgb, bg_alpha)

    margin_x = int(round(s * MARGIN_RATIO))
    margin_y = int(round(s * MARGIN_RATIO))
    arm_len = int(s * ARM_LEN_RATIO)
    thickness = _frame_thickness(s, thickness_val)

    # 共通パディング・クリアランス比率
    pad_x = max(3, int(round(s * 0.010)))
    pad_y = max(3, int(round(s * 0.008)))
    clearance_x = max(2, int(round(s * 0.012)))
    clearance_y = max(2, int(round(s * 0.010)))

    # 1. 四隅枠
    _draw_corner_frames(d, w, h, s, mono, margin_x, margin_y, arm_len, thickness)

    # 2. 十字
    _draw_center_cross(d, w, h, s, mono)

    # 3. 電池 (座布団付き)
    render_battery_with_bg(
        d, s, margin_x, margin_y, thickness, mono, bg_color, bg_box_opacity,
        pad_x, pad_y, clearance_x, clearance_y, active_bars=4
    )

    # 4. REC インジケータ (座布団付き)
    font_size = max(MIN_REC_FONT_SIZE, int(s * REC_FONT_RATIO))
    font = _load_font(font_size, font_key)
    dot_r = int(s * DOT_R_RATIO)
    dot_diam = dot_r * 2
    gap = int(s * REC_GAP_RATIO)

    has_text = bool(rec_text.strip())
    if has_text:
        ink_dx, ink_dy, text_w, text_h = _tight_ink_metrics(font, rec_text)
    else:
        ink_dx, ink_dy, text_w, text_h = 0, 0, 0, 0

    content_w = dot_diam + (gap + text_w if has_text else 0)
    content_h = max(dot_diam, text_h)

    box_w = content_w + pad_x * 2
    box_h = content_h + pad_y * 2

    box_x1 = (w - 1 - margin_x - thickness) - clearance_x
    box_x0 = box_x1 - box_w
    box_y0 = (margin_y + thickness) + clearance_y
    box_y1 = box_y0 + box_h

    if bg_box_opacity > 0:
        d.rectangle([box_x0, box_y0, box_x1, box_y1], fill=bg_color)

    cy = box_y0 + box_h // 2
    dot_x0 = box_x0 + pad_x
    dot_y0 = cy - dot_r
    d.ellipse([dot_x0, dot_y0, dot_x0 + dot_diam, dot_y0 + dot_diam], fill=RED)

    if has_text:
        text_ink_x0 = dot_x0 + dot_diam + gap
        text_ink_y0 = cy - text_h // 2
        draw_x = text_ink_x0 - ink_dx
        draw_y = text_ink_y0 - ink_dy
        d.text((draw_x, draw_y), rec_text, font=font, fill=mono, anchor="lt")

    # 5. タイムコード (座布団付き)
    if timecode_text.strip():
        tc_font_size = max(MIN_REC_FONT_SIZE, int(s * TIMECODE_FONT_RATIO))
        tc_font = _load_font(tc_font_size, font_key)
        tc_dx, tc_dy, tc_w, tc_h = _tight_ink_metrics(tc_font, timecode_text)

        tc_box_w = tc_w + pad_x * 2
        tc_box_h = tc_h + pad_y * 2

        tc_box_x1 = (w - 1 - margin_x - thickness) - clearance_x
        tc_box_x0 = tc_box_x1 - tc_box_w
        tc_box_y1 = (h - 1 - margin_y - thickness) - clearance_y
        tc_box_y0 = tc_box_y1 - tc_box_h

        if bg_box_opacity > 0:
            d.rectangle([tc_box_x0, tc_box_y0, tc_box_x1, tc_box_y1], fill=bg_color)

        tc_cy = tc_box_y0 + tc_box_h // 2
        tc_ink_x0 = tc_box_x0 + pad_x
        tc_ink_y0 = tc_cy - tc_h // 2
        tc_draw_x = tc_ink_x0 - tc_dx
        tc_draw_y = tc_ink_y0 - tc_dy
        d.text((tc_draw_x, tc_draw_y), timecode_text, font=tc_font, fill=mono, anchor="lt")

    return overlay

def generate():
    bg = create_bright_test_bg(1280, 720)

    # 全体（白枠・黒半透明座布団 50%）
    ov_white = render_full_overlay(1280, 720, color="white", bg_box_opacity=0.5)
    comp_white = bg.copy()
    comp_white.paste(ov_white, (0, 0), ov_white)
    comp_white.save(OUT_DIR / "sample_all_with_battery_box.png")
    print("Saved: sample_all_with_battery_box.png")

    # 電池部分のビフォー／アフター拡大 (300x120)
    # ビフォー: 座布団なし
    ov_no_bg = render_full_overlay(1280, 720, color="white", bg_box_opacity=0.0)
    comp_no_bg = bg.copy()
    comp_no_bg.paste(ov_no_bg, (0, 0), ov_no_bg)
    bat_before = comp_no_bg.crop((15, 15, 250, 115))

    # アフター: 座布団あり
    bat_after = comp_white.crop((15, 15, 250, 115))

    default_sys_font = ImageFont.load_default()
    d_b = ImageDraw.Draw(bat_before)
    d_b.rectangle([0, 0, 70, 16], fill=(200, 0, 0, 240))
    d_b.text((5, 2), "BEFORE", fill=(255, 255, 255), font=default_sys_font)

    d_a = ImageDraw.Draw(bat_after)
    d_a.rectangle([0, 0, 70, 16], fill=(0, 160, 0, 240))
    d_a.text((5, 2), "AFTER", fill=(255, 255, 255), font=default_sys_font)

    bat_comp = Image.new("RGB", (bat_before.width * 2 + 10, bat_before.height), (30, 30, 30))
    bat_comp.paste(bat_before, (0, 0))
    bat_comp.paste(bat_after, (bat_before.width + 10, 0))
    bat_comp.save(OUT_DIR / "battery_before_after.png")
    print("Saved: battery_before_after.png")

if __name__ == "__main__":
    generate()
