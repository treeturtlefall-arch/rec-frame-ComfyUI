"""半透明背景ボックス（直角 vs ほんのり角丸 vs ピル型）の比較サンプル画像生成スクリプト。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math

from rec_config import (
    OverlayConfig,
    DEFAULT_FONT,
    BUNDLED_FONT_CHOICES,
)
from rec_overlay import (
    create_rec_overlay_with_config,
    _load_font,
    _draw_corner_frames,
    _draw_battery,
    _draw_center_cross,
    _load_and_resize_dot_asset,
    _frame_thickness,
    discover_dot_assets,
    MARGIN_RATIO,
    ARM_LEN_RATIO,
    DOT_R_RATIO,
    REC_GAP_RATIO,
    REC_BLOCK_X_OFFSET_RATIO,
    REC_BLOCK_Y_OFFSET_RATIO,
    REC_DY_RATIO,
    REC_FONT_RATIO,
    MIN_REC_FONT_SIZE,
    TIMECODE_FONT_RATIO,
    TIMECODE_X_OFFSET_RATIO,
    TIMECODE_Y_GAP_RATIO,
    RED,
)

OUT_DIR = Path(r"C:\Users\coffe\.gemini\antigravity\brain\c76ae104-18f9-43fb-8a42-8c75f360f03c")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def create_bright_test_bg(w=1280, h=720):
    """明るい白・水色・グレーの混ざった写真風背景（白文字・赤丸が背景に溶け込みやすい条件）"""
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

def render_sample_overlay(
    w=1280,
    h=720,
    color="white",
    style="none", # "none", "rect", "rounded", "pill"
    opacity=0.5,
    font_key=DEFAULT_FONT,
    timecode_text="2026/11/01 PM 08:30",
    rec_text="REC",
):
    """プロトタイプ描画関数"""
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    s = min(w, h)

    mono = (255, 255, 255, 255) if color == "white" else (0, 0, 0, 255)
    # 背景ボックス色: 白文字には黒半透明、黒文字には白半透明
    bg_rgb = (0, 0, 0) if color == "white" else (255, 255, 255)
    bg_alpha = int(round(255 * opacity))
    bg_color = (*bg_rgb, bg_alpha)

    margin_x = int(round(s * MARGIN_RATIO))
    margin_y = int(round(s * MARGIN_RATIO))
    arm_len = int(s * ARM_LEN_RATIO)
    thickness = max(2, int(round(s * 0.008)))

    # 1. 四隅枠
    _draw_corner_frames(d, w, h, s, mono, margin_x, margin_y, arm_len, thickness)
    # 2. 電池
    _draw_battery(d, s, margin_x, margin_y, thickness, mono, 4)
    # 3. 十字
    _draw_center_cross(d, w, h, s, mono)

    # パディング比率
    pad_x = int(round(s * 0.012))
    pad_y = int(round(s * 0.006))

    def draw_bg_box(x0, y0, x1, y1):
        if opacity <= 0 or style == "none":
            return
        bx0, by0, bx1, by1 = x0 - pad_x, y0 - pad_y, x1 + pad_x, y1 + pad_y
        box_h = by1 - by0
        if style == "rect":
            d.rectangle([bx0, by0, bx1, by1], fill=bg_color)
        elif style == "rounded":
            r = max(2, int(round(s * 0.008)))  # ほんのり角丸 (720pで約6px)
            d.rounded_rectangle([bx0, by0, bx1, by1], radius=r, fill=bg_color)
        elif style == "pill":
            r = box_h // 2  # ピル・カプセル型
            d.rounded_rectangle([bx0, by0, bx1, by1], radius=r, fill=bg_color)

    # 4. REC インジケータ
    font_size = max(MIN_REC_FONT_SIZE, int(s * REC_FONT_RATIO))
    font = _load_font(font_size, font_key)
    bbox = font.getbbox(rec_text) if rec_text.strip() else (0, 0, 0, 0)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    dot_r = int(s * DOT_R_RATIO)
    gap = int(s * REC_GAP_RATIO)
    block_w = dot_r * 2 + gap + text_w
    block_x = w - margin_x - int(s * REC_BLOCK_X_OFFSET_RATIO) - block_w
    rec_dy = int(s * REC_DY_RATIO)
    block_y = margin_y + thickness + int(s * REC_BLOCK_Y_OFFSET_RATIO) + rec_dy
    row_h = max(text_h, dot_r * 2)
    cy = block_y + row_h // 2

    # REC背景ボックス
    rec_x0 = block_x
    rec_y0 = cy - row_h // 2
    rec_x1 = block_x + block_w
    rec_y1 = cy + (row_h + 1) // 2
    draw_bg_box(rec_x0, rec_y0, rec_x1, rec_y1)

    # 赤丸
    dot_diam = dot_r * 2
    d.ellipse([block_x, cy - dot_r, block_x + dot_diam, cy + dot_r], fill=RED)
    # REC文字
    if rec_text.strip():
        d.text((block_x + dot_r * 2 + gap - bbox[0], cy - text_h // 2 - bbox[1]),
               rec_text, font=font, fill=mono, anchor="lt")

    # 5. タイムコード
    if timecode_text.strip():
        tc_font_size = max(MIN_REC_FONT_SIZE, int(s * TIMECODE_FONT_RATIO))
        tc_font = _load_font(tc_font_size, font_key)
        tc_bbox = tc_font.getbbox(timecode_text)
        tc_w = tc_bbox[2] - tc_bbox[0]
        tc_h = tc_bbox[3] - tc_bbox[1]
        
        tc_rx = w - margin_x - int(s * TIMECODE_X_OFFSET_RATIO)
        tc_by = h - 1 - margin_y - thickness - int(s * TIMECODE_Y_GAP_RATIO) - rec_dy

        # タイムコードの精密な描画座標
        # anchor="rb" で (tc_rx, tc_by) に描いた場合、文字インク範囲は:
        # X: [tc_rx - tc_w, tc_rx]
        # Y: [tc_by - tc_h, tc_by]
        # (フォントbboxオフセットを考慮)
        draw_x = tc_rx - tc_bbox[2]
        draw_y = tc_by - tc_bbox[3]
        
        tc_x0 = draw_x + tc_bbox[0]
        tc_y0 = draw_y + tc_bbox[1]
        tc_x1 = draw_x + tc_bbox[2]
        tc_y1 = draw_y + tc_bbox[3]

        draw_bg_box(tc_x0, tc_y0, tc_x1, tc_y1)
        d.text((tc_rx, tc_by), timecode_text, font=tc_font, fill=mono, anchor="rb")

    return overlay

def generate_all_samples():
    bg = create_bright_test_bg(1280, 720)
    styles = [
        ("01_none", "none", 0.0, "なし (現行)"),
        ("02_sharp_rect", "rect", 0.5, "シャープ長方形 (Rect 50%)"),
        ("03_rounded", "rounded", 0.5, "ほんのり角丸 (Rounded 50%)"),
        ("04_pill", "pill", 0.5, "ピル/カプセル型 (Pill 50%)"),
    ]

    for prefix, st, op, title in styles:
        ov = render_sample_overlay(1280, 720, color="white", style=st, opacity=op)
        comp = bg.copy()
        comp.paste(ov, (0, 0), ov)
        out_path = OUT_DIR / f"sample_{prefix}.png"
        comp.save(out_path)
        print(f"Saved: {out_path}")

    # 黒枠バージョンのサンプルも1つ生成
    ov_black = render_sample_overlay(1280, 720, color="black", style="rounded", opacity=0.5)
    comp_black = bg.copy()
    comp_black.paste(ov_black, (0, 0), ov_black)
    out_black_path = OUT_DIR / "sample_05_black_frame_rounded.png"
    comp_black.save(out_black_path)
    print(f"Saved: {out_black_path}")

    # 4分割比較グリッド画像 (1枚で見比べられるように)
    grid = Image.new("RGB", (1280 * 2, 720 * 2))
    img_none = Image.open(OUT_DIR / "sample_01_none.png")
    img_rect = Image.open(OUT_DIR / "sample_02_sharp_rect.png")
    img_rounded = Image.open(OUT_DIR / "sample_03_rounded.png")
    img_pill = Image.open(OUT_DIR / "sample_04_pill.png")

    grid.paste(img_none, (0, 0))
    grid.paste(img_rect, (1280, 0))
    grid.paste(img_rounded, (0, 720))
    grid.paste(img_pill, (1280, 720))

    grid_draw = ImageDraw.Draw(grid)
    lbl_font = ImageFont.load_default()
    # 簡易タイトル描き込み
    grid.save(OUT_DIR / "sample_comparison_grid.png")
    print(f"Saved: {OUT_DIR / 'sample_comparison_grid.png'}")

if __name__ == "__main__":
    generate_all_samples()
