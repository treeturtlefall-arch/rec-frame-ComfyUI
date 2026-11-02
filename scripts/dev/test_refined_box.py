"""ボックス内の完璧なセンタリングとL字枠クリアランスの検証スクリプト。
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
    _draw_battery,
    _draw_center_cross,
    _frame_thickness,
    MARGIN_RATIO,
    ARM_LEN_RATIO,
    DOT_R_RATIO,
    REC_GAP_RATIO,
    REC_FONT_RATIO,
    MIN_REC_FONT_SIZE,
    TIMECODE_FONT_RATIO,
    RED,
)

OUT_DIR = Path(r"C:\Users\coffe\.gemini\antigravity\brain\c76ae104-18f9-43fb-8a42-8c75f360f03c")
OUT_DIR.mkdir(parents=True, exist_ok=True)

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

def _tight_ink_metrics(font, text: str) -> tuple[int, int, int, int]:
    """anchor='lt' 描画時の厳密なインク左上オフセット (dx, dy) とインク寸法 (w, h) を返す。"""
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


def render_refined_overlay(
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

    # 1. 四隅枠
    _draw_corner_frames(d, w, h, s, mono, margin_x, margin_y, arm_len, thickness)
    # 2. 電池
    _draw_battery(d, s, margin_x, margin_y, thickness, mono, 4)
    # 3. 十字
    _draw_center_cross(d, w, h, s, mono)

    # パディングとクリアランスの比率計算
    pad_x = max(3, int(round(s * 0.010)))  # ボックス内左右余白
    pad_y = max(3, int(round(s * 0.008)))  # ボックス内上下余白
    clearance_x = max(2, int(round(s * 0.012)))  # L字縦枠からの距離
    clearance_y = max(2, int(round(s * 0.010)))  # L字横枠からの距離

    # 4. REC インジケータ
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

    # ボックス外形サイズ
    box_w = content_w + pad_x * 2
    box_h = content_h + pad_y * 2

    # L字枠からクリアランスを保った配置
    box_x1 = (w - 1 - margin_x - thickness) - clearance_x
    box_x0 = box_x1 - box_w
    box_y0 = (margin_y + thickness) + clearance_y
    box_y1 = box_y0 + box_h

    # ボックス描画
    if bg_box_opacity > 0:
        d.rectangle([box_x0, box_y0, box_x1, box_y1], fill=bg_color)

    # ボックス内の垂直中心 cy
    cy = box_y0 + box_h // 2

    # 赤丸描画 (cy を中心に対称配置)
    dot_x0 = box_x0 + pad_x
    dot_y0 = cy - dot_r
    d.ellipse([dot_x0, dot_y0, dot_x0 + dot_diam, dot_y0 + dot_diam], fill=RED)

    # REC文字描画 (cy を中心にインク上下・左右完全一致)
    if has_text:
        text_ink_x0 = dot_x0 + dot_diam + gap
        text_ink_y0 = cy - text_h // 2
        draw_x = text_ink_x0 - ink_dx
        draw_y = text_ink_y0 - ink_dy
        d.text((draw_x, draw_y), rec_text, font=font, fill=mono, anchor="lt")

    # 5. タイムコード (右下)
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

def run_tests():
    bg = create_bright_test_bg(1280, 720)

    # 1. 改善版の全体サンプル (50% 長方形)
    ov = render_refined_overlay(1280, 720, color="white", bg_box_opacity=0.5, font_key=DEFAULT_FONT)
    comp = bg.copy()
    comp.paste(ov, (0, 0), ov)
    comp.save(OUT_DIR / "refined_sample_rect_v2.png")
    print("Saved: refined_sample_rect_v2.png")

    # 2. 同梱全6フォントでのREC・タイムコード比較画像を生成
    font_crops = []
    default_font_sys = ImageFont.load_default()

    for font_name in BUNDLED_FONT_CHOICES:
        ov_f = render_refined_overlay(1280, 720, color="white", bg_box_opacity=0.5, font_key=font_name)
        c_f = bg.copy()
        c_f.paste(ov_f, (0, 0), ov_f)
        
        # 右上RECエリア クロップ (300x90)
        rec_crop = c_f.crop((960, 20, 1260, 110))
        d_rc = ImageDraw.Draw(rec_crop)
        d_rc.rectangle([0, 0, 150, 16], fill=(0, 0, 0, 220))
        d_rc.text((3, 2), font_name.split("(")[0], fill=(255, 255, 255), font=default_font_sys)
        font_crops.append(rec_crop)

    # 縦並びのフォント検証画像
    total_h = sum(c.height for c in font_crops) + 10 * (len(font_crops) - 1)
    font_sheet = Image.new("RGB", (300, total_h), (40, 40, 40))
    curr_y = 0
    for c in font_crops:
        font_sheet.paste(c, (0, curr_y))
        curr_y += c.height + 10
    font_sheet.save(OUT_DIR / "font_alignment_sheet_v2.png")
    print("Saved: font_alignment_sheet_v2.png")

    # 3. ビフォー・アフター比較クロップ（枠とのクリアランス＆センタリング）
    # ビフォー（修正前）の右上一帯
    old_img = Image.open(OUT_DIR / "sample_02_sharp_rect.png")
    old_rec = old_img.crop((950, 15, 1265, 125))
    d_o = ImageDraw.Draw(old_rec)
    d_o.rectangle([0, 0, 80, 18], fill=(200, 0, 0, 240))
    d_o.text((5, 3), "BEFORE", fill=(255, 255, 255), font=default_font_sys)

    # アフター（修正後）の右上一帯
    new_img = Image.open(OUT_DIR / "refined_sample_rect_v2.png")
    new_rec = new_img.crop((950, 15, 1265, 125))
    d_n = ImageDraw.Draw(new_rec)
    d_n.rectangle([0, 0, 80, 18], fill=(0, 160, 0, 240))
    d_n.text((5, 3), "AFTER", fill=(255, 255, 255), font=default_font_sys)

    # 並べて比較
    ba_comp = Image.new("RGB", (old_rec.width * 2 + 10, old_rec.height), (30, 30, 30))
    ba_comp.paste(old_rec, (0, 0))
    ba_comp.paste(new_rec, (old_rec.width + 10, 0))
    ba_comp.save(OUT_DIR / "before_after_rec_clearance_v2.png")
    print("Saved: before_after_rec_clearance_v2.png")

    # タイムコードのビフォー・アフター
    old_tc = old_img.crop((780, 600, 1265, 715))
    d_otc = ImageDraw.Draw(old_tc)
    d_otc.rectangle([0, 0, 100, 18], fill=(200, 0, 0, 240))
    d_otc.text((5, 3), "BEFORE", fill=(255, 255, 255), font=default_font_sys)

    new_tc = new_img.crop((780, 600, 1265, 715))
    d_ntc = ImageDraw.Draw(new_tc)
    d_ntc.rectangle([0, 0, 100, 18], fill=(0, 160, 0, 240))
    d_ntc.text((5, 3), "AFTER", fill=(255, 255, 255), font=default_font_sys)

    ba_tc_comp = Image.new("RGB", (old_tc.width * 2 + 10, old_tc.height), (30, 30, 30))
    ba_tc_comp.paste(old_tc, (0, 0))
    ba_tc_comp.paste(new_tc, (old_tc.width + 10, 0))
    ba_tc_comp.save(OUT_DIR / "before_after_tc_clearance_v2.png")
    print("Saved: before_after_tc_clearance_v2.png")

if __name__ == "__main__":
    run_tests()
