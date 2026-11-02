"""細部比較用のクロップ画像（右上REC・右下TIMECODE）を生成する。
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(r"C:\Users\coffe\.gemini\antigravity\brain\c76ae104-18f9-43fb-8a42-8c75f360f03c")

files = [
    ("なし (現行)", OUT_DIR / "sample_01_none.png"),
    ("シャープ長方形", OUT_DIR / "sample_02_sharp_rect.png"),
    ("ほんのり角丸", OUT_DIR / "sample_03_rounded.png"),
    ("ピル/カプセル型", OUT_DIR / "sample_04_pill.png"),
]

# 1280x720 の右上 REC エリア: x: 950..1250, y: 15..110
# 1280x720 の右下 TIMECODE エリア: x: 750..1250, y: 620..710
rec_crops = []
tc_crops = []

font = ImageFont.load_default()

for label, p in files:
    img = Image.open(p)
    
    # REC クロップ (320x100)
    rec_part = img.crop((940, 15, 1260, 115))
    d_rec = ImageDraw.Draw(rec_part)
    d_rec.rectangle([0, 0, 120, 20], fill=(0, 0, 0, 200))
    d_rec.text((5, 3), label, fill=(255, 255, 255), font=font)
    rec_crops.append(rec_part)
    
    # タイムコード クロップ (480x100)
    tc_part = img.crop((780, 615, 1260, 715))
    d_tc = ImageDraw.Draw(tc_part)
    d_tc.rectangle([0, 0, 120, 20], fill=(0, 0, 0, 200))
    d_tc.text((5, 3), label, fill=(255, 255, 255), font=font)
    tc_crops.append(tc_part)

# 縦に並べた比較画像
rec_comp = Image.new("RGB", (320, 100 * len(rec_crops) + 10 * (len(rec_crops) - 1)), (50, 50, 50))
for i, crop in enumerate(rec_crops):
    rec_comp.paste(crop, (0, i * 110))
rec_comp.save(OUT_DIR / "crop_rec_comparison.png")
print("Saved: crop_rec_comparison.png")

tc_comp = Image.new("RGB", (480, 100 * len(tc_crops) + 10 * (len(tc_crops) - 1)), (50, 50, 50))
for i, crop in enumerate(tc_crops):
    tc_comp.paste(crop, (0, i * 110))
tc_comp.save(OUT_DIR / "crop_tc_comparison.png")
print("Saved: crop_tc_comparison.png")
