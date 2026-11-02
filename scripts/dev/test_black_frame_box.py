"""黒枠・黒文字における半透明座布団（白半透明 50%）のテスト画像生成スクリプト。
暗い背景（夜景・ダークシーン）および明るい背景での見え方を検証する。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from PIL import Image, ImageDraw, ImageFont
import math

from rec_config import DEFAULT_FONT
from test_battery_box import render_full_overlay, create_bright_test_bg, OUT_DIR

def create_dark_test_bg(w=1280, h=720):
    """暗い夜景・ネオン・ダークトーンの背景（黒文字・黒枠が埋もれて見えなくなる条件）"""
    img = Image.new("RGB", (w, h))
    pixels = img.load()
    for y in range(h):
        for x in range(w):
            ny = y / h
            nx = x / w
            # 暗いトーン (RGB 20〜60)
            r = int(25 + 20 * math.sin(nx * 8) * math.cos(ny * 6))
            g = int(30 + 15 * math.cos(nx * 6 + ny * 4))
            b = int(45 + 25 * math.sin(ny * 10))
            # ディテール・グリッド
            if (x // 25 + y // 25) % 2 == 0:
                r = min(255, r + 15)
                g = min(255, g + 15)
                b = min(255, b + 20)
            pixels[x, y] = (min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b)))
    return img

def generate_black_frame_samples():
    dark_bg = create_dark_test_bg(1280, 720)
    bright_bg = create_bright_test_bg(1280, 720)

    # 1. 暗い背景 × 黒枠（座布団なし vs 白半透明座布団 50%）
    ov_black_no_bg = render_full_overlay(1280, 720, color="black", bg_box_opacity=0.0)
    ov_black_with_bg = render_full_overlay(1280, 720, color="black", bg_box_opacity=0.5)

    comp_dark_no = dark_bg.copy()
    comp_dark_no.paste(ov_black_no_bg, (0, 0), ov_black_no_bg)
    comp_dark_no.save(OUT_DIR / "sample_black_dark_no_bg.png")

    comp_dark_with = dark_bg.copy()
    comp_dark_with.paste(ov_black_with_bg, (0, 0), ov_black_with_bg)
    comp_dark_with.save(OUT_DIR / "sample_black_dark_with_bg.png")
    print("Saved: sample_black_dark_with_bg.png")

    # 2. 明るい背景 × 黒枠（白半透明座布団 50%）
    comp_bright_with = bright_bg.copy()
    comp_bright_with.paste(ov_black_with_bg, (0, 0), ov_black_with_bg)
    comp_bright_with.save(OUT_DIR / "sample_black_bright_with_bg.png")
    print("Saved: sample_black_bright_with_bg.png")

    # 3. 暗い背景での各要素の拡大比較 (電池・REC・タイムコード)
    sys_font = ImageFont.load_default()
    
    # 電池
    bat_no = comp_dark_no.crop((15, 15, 250, 115))
    bat_with = comp_dark_with.crop((15, 15, 250, 115))
    d_bn = ImageDraw.Draw(bat_no)
    d_bn.rectangle([0, 0, 70, 16], fill=(200, 0, 0, 240))
    d_bn.text((5, 2), "BEFORE", fill=(255, 255, 255), font=sys_font)
    d_bw = ImageDraw.Draw(bat_with)
    d_bw.rectangle([0, 0, 70, 16], fill=(0, 160, 0, 240))
    d_bw.text((5, 2), "AFTER", fill=(255, 255, 255), font=sys_font)
    bat_c = Image.new("RGB", (bat_no.width * 2 + 10, bat_no.height), (30, 30, 30))
    bat_c.paste(bat_no, (0, 0))
    bat_c.paste(bat_with, (bat_no.width + 10, 0))
    bat_c.save(OUT_DIR / "black_bat_dark_comp.png")

    # REC
    rec_no = comp_dark_no.crop((950, 15, 1265, 125))
    rec_with = comp_dark_with.crop((950, 15, 1265, 125))
    d_rn = ImageDraw.Draw(rec_no)
    d_rn.rectangle([0, 0, 70, 16], fill=(200, 0, 0, 240))
    d_rn.text((5, 2), "BEFORE", fill=(255, 255, 255), font=sys_font)
    d_rw = ImageDraw.Draw(rec_with)
    d_rw.rectangle([0, 0, 70, 16], fill=(0, 160, 0, 240))
    d_rw.text((5, 2), "AFTER", fill=(255, 255, 255), font=sys_font)
    rec_c = Image.new("RGB", (rec_no.width * 2 + 10, rec_no.height), (30, 30, 30))
    rec_c.paste(rec_no, (0, 0))
    rec_c.paste(rec_with, (rec_no.width + 10, 0))
    rec_c.save(OUT_DIR / "black_rec_dark_comp.png")

    # タイムコード
    tc_no = comp_dark_no.crop((780, 600, 1265, 715))
    tc_with = comp_dark_with.crop((780, 600, 1265, 715))
    d_tn = ImageDraw.Draw(tc_no)
    d_tn.rectangle([0, 0, 70, 16], fill=(200, 0, 0, 240))
    d_tn.text((5, 2), "BEFORE", fill=(255, 255, 255), font=sys_font)
    d_tw = ImageDraw.Draw(tc_with)
    d_tw.rectangle([0, 0, 70, 16], fill=(0, 160, 0, 240))
    d_tw.text((5, 2), "AFTER", fill=(255, 255, 255), font=sys_font)
    tc_c = Image.new("RGB", (tc_no.width * 2 + 10, tc_no.height), (30, 30, 30))
    tc_c.paste(tc_no, (0, 0))
    tc_c.paste(tc_with, (tc_no.width + 10, 0))
    tc_c.save(OUT_DIR / "black_tc_dark_comp.png")

    print("All black frame samples generated.")

if __name__ == "__main__":
    generate_black_frame_samples()
