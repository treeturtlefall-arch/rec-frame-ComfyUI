#!/usr/bin/env python3
"""README および公式ドキュメント用のビジュアルアセット（デモ画像・点滅GIFアニメ）を一括生成するスクリプト。

生成ファイル:
  1. assets/demo/hero_showcase.png         - 4スタイル比較ヒーローバナー (1280x720)
  2. assets/demo/video_playback.gif        - 赤丸点滅＋タイムコード進行のループアニメーションGIF (640x360)
  3. assets/demo/retro_effect_levels.png   - retro_effect (0〜6) の段階比較画像 (1200x520)
  4. assets/demo/color_presets.png         - 6色プリセット＋ドットスタイルの比較画像 (1200x360)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps

# プロジェクトルートを import パスに追加
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from rec_config import OverlayConfig, COLOR_PRESETS
from rec_overlay import composite_with_config, create_rec_overlay_with_config


def get_base_image(width: int, height: int, tone: str = "normal") -> Image.Image:
    """ベース背景画像を取得・加工して返す (著作権フリーのパブリックドメイン名画 sample_07 を活用)。"""
    src = ROOT_DIR / "tests" / "preview_gallery" / "images" / "sample_07_orig.webp"
    if src.is_file():
        im = Image.open(src).convert("RGB")
        # センタークロップでアスペクト比を合わせる
        src_w, src_h = im.size
        target_ratio = width / height
        src_ratio = src_w / src_h

        if src_ratio > target_ratio:
            new_w = int(src_h * target_ratio)
            left = (src_w - new_w) // 2
            im = im.crop((left, 0, left + new_w, src_h))
        else:
            new_h = int(src_w / target_ratio)
            top = (src_h - new_h) // 2
            im = im.crop((0, top, src_w, top + new_h))

        im = im.resize((width, height), Image.Resampling.LANCZOS)
    else:
        # 代替のプロシージャルグラデーション
        im = Image.new("RGB", (width, height), (20, 24, 36))
        d = ImageDraw.Draw(im)
        for y in range(height):
            r = int(15 + 25 * (y / height))
            g = int(20 + 35 * (y / height))
            b = int(35 + 50 * (y / height))
            d.line([(0, y), (width, y)], fill=(r, g, b))

    # トーン調整
    if tone == "night_vision":
        # グリーン暗視風
        gray = ImageOps.grayscale(im)
        green = Image.new("RGB", (width, height), (10, 80, 30))
        im = ImageOps.colorize(gray, black="#051508", white="#60FF80", mid="#108030")
        im = ImageEnhance.Contrast(im).enhance(1.2)
    elif tone == "warm_retro":
        # 2000sレトロ風 (コントラスト微増＋暖色)
        r, g, b = im.split()
        r = r.point(lambda i: min(255, int(i * 1.08)))
        b = b.point(lambda i: int(i * 0.92))
        im = Image.merge("RGB", (r, g, b))
        im = ImageEnhance.Contrast(im).enhance(1.15)
    elif tone == "alert_red":
        # シネマティック高コントラスト＋赤系引き締め
        gray = ImageOps.grayscale(im)
        im = ImageOps.colorize(gray, black="#1a0505", white="#ffb0b0", mid="#801515")
        im = ImageEnhance.Contrast(im).enhance(1.25)
    elif tone == "darkened":
        # UIが映えるように少しトーンを落とす
        im = ImageEnhance.Brightness(im).enhance(0.85)

    return im


def draw_label_badge(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, font: ImageFont.ImageFont, accent_color: tuple[int, int, int] = (255, 255, 255)):
    """タイルの左上にスタイリッシュな半透明バッジを描画する。"""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_x, pad_y = 10, 5
    box_w = tw + pad_x * 2 + 12
    box_h = th + pad_y * 2

    # 背景ピル
    draw.rounded_rectangle([x, y, x + box_w, y + box_h], radius=4, fill=(15, 18, 26, 210), outline=(60, 68, 85, 255), width=1)
    # アクセントバー
    draw.rectangle([x + 4, y + 4, x + 7, y + box_h - 4], fill=accent_color)
    # テキスト
    draw.text((x + 14, y + pad_y), text, font=font, fill=(240, 243, 248, 255))


def generate_hero_showcase(output_path: Path):
    """1. 4スタイル比較ヒーローバナー (1280x720) を生成する。"""
    print(f"[1/4] Generating hero showcase: {output_path.name}...")
    tile_w, tile_h = 640, 360
    total_w, total_h = 1280, 720

    # 4タイルの設定定義
    presets = [
        {
            "title": "01 CLASSIC CAMCORDER",
            "accent": (255, 50, 50),
            "tone": "darkened",
            "config": OverlayConfig(
                color="white",
                thickness=50,
                font_key="Roboto Condensed Bold(細長)",
                dot_style="glow_red",
                rec_label="REC",
                battery_bars=4,
                show_timecode=True,
                timecode_text="2026/11/02 PM 08:30:15",
                retro_effect=0,
                bg_box_opacity=0.20,
            )
        },
        {
            "title": "02 RETRO 2000s DIGICAM (Y2K)",
            "accent": (255, 180, 0),
            "tone": "warm_retro",
            "config": OverlayConfig(
                color="white",
                thickness=40,
                font_key="VT323(レトロドット)",
                dot_style="flat_red",
                rec_label="REC",
                battery_bars=2,
                show_cross=True,
                show_timecode=True,
                timecode_text="2004/08/15 PM 02:45:00",
                retro_effect=2,
                bg_box_opacity=0.35,
            )
        },
        {
            "title": "03 TACTICAL NIGHT VISION",
            "accent": (0, 255, 80),
            "tone": "night_vision",
            "config": OverlayConfig(
                color="green",
                thickness=30,
                font_key="Share Tech Mono(等幅)",
                dot_style="glow_green",
                rec_label="NVG-01",
                battery_bars=3,
                show_cross=True,
                show_timecode=True,
                timecode_text="ISO 12800 F1.4 1/30s",
                retro_effect=1,
                bg_box_opacity=0.25,
            )
        },
        {
            "title": "04 EMERGENCY ACTION HUD",
            "accent": (255, 30, 30),
            "tone": "alert_red",
            "config": OverlayConfig(
                color="red",
                thickness=65,
                font_key="Bebas Neue(縦長大文字)",
                dot_style="flat_amber",
                rec_label="ALERT",
                battery_bars=1,
                show_cross=False,
                show_timecode=True,
                timecode_text="SYSTEM LOCK: LEVEL-4",
                retro_effect=1,
                bg_box_opacity=0.30,
            )
        },
    ]

    hero_img = Image.new("RGB", (total_w, total_h), (10, 12, 16))
    badge_font_path = ROOT_DIR / "fonts" / "ShareTechMono-Regular.ttf"
    badge_font = ImageFont.truetype(str(badge_font_path), 13) if badge_font_path.is_file() else ImageFont.load_default()

    coords = [(0, 0), (tile_w, 0), (0, tile_h), (tile_w, tile_h)]

    for idx, (p, (tx, ty)) in enumerate(zip(presets, coords)):
        base = get_base_image(tile_w, tile_h, tone=p["tone"])
        comp = composite_with_config(base, p["config"])

        # タイトルバッジ描画 (電池マーク Y:14..37 と被らないよう少し下げて Y=48 に配置)
        overlay_badge = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay_badge)
        draw_label_badge(d, 20, 48, p["title"], badge_font, p["accent"])
        comp.paste(overlay_badge, (0, 0), overlay_badge)

        hero_img.paste(comp, (tx, ty))

    # 区切り線
    draw = ImageDraw.Draw(hero_img)
    draw.line([(tile_w, 0), (tile_w, total_h)], fill=(40, 45, 60), width=2)
    draw.line([(0, tile_h), (total_w, tile_h)], fill=(40, 45, 60), width=2)

    hero_img.save(output_path, "PNG", optimize=True)
    print(f"  -> Saved {output_path} ({os.path.getsize(output_path) // 1024} KB)")


def generate_video_playback_gif(output_path: Path):
    """2. 赤丸点滅＋タイムコード進行のループアニメーションGIF (640x360) を生成する。"""
    print(f"[2/4] Generating video playback GIF: {output_path.name}...")
    w, h = 640, 360
    base = get_base_image(w, h, tone="darkened")

    # 実機の録画仕様: 1秒周期 (0.5秒点灯、0.5秒消灯) ＋ 1秒ごとにタイムコード加算
    # 合計 3.0 秒 (6 ステップ、各 500ms)
    steps = [
        (True,  "2026/11/02 PM 08:30:15", 500),
        (False, "2026/11/02 PM 08:30:15", 500),
        (True,  "2026/11/02 PM 08:30:16", 500),
        (False, "2026/11/02 PM 08:30:16", 500),
        (True,  "2026/11/02 PM 08:30:17", 500),
        (False, "2026/11/02 PM 08:30:17", 500),
    ]

    frames: list[Image.Image] = []
    durations: list[int] = []

    for red_dot_visible, tc_text, dur in steps:
        cfg = OverlayConfig(
            color="white",
            thickness=45,
            font_key="Roboto Condensed Bold(細長)",
            dot_style="glow_red",
            rec_label="REC",
            red_dot_visible=red_dot_visible,
            battery_bars=4,
            show_timecode=True,
            timecode_text=tc_text,
            retro_effect=1,  # 微弱なCRTエフェクト
            bg_box_opacity=0.25,
        )

        frame_img = composite_with_config(base.copy(), cfg)
        frames.append(frame_img)
        durations.append(dur)

    # GIF出力 (各フレームの duration を指定・パレット最適化)
    frames[0].save(
        output_path,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    print(f"  -> Saved {output_path} ({os.path.getsize(output_path) // 1024} KB)")


def generate_retro_effect_levels(output_path: Path):
    """3. retro_effect (0〜6) の段階比較画像 (1200x520) を生成する。"""
    print(f"[3/4] Generating retro effect levels: {output_path.name}...")
    total_w, total_h = 1200, 520
    im = Image.new("RGB", (total_w, total_h), (15, 18, 24))
    draw = ImageDraw.Draw(im)

    font_path = ROOT_DIR / "fonts" / "ShareTechMono-Regular.ttf"
    title_font = ImageFont.truetype(str(font_path), 18) if font_path.is_file() else ImageFont.load_default()
    label_font = ImageFont.truetype(str(font_path), 12) if font_path.is_file() else ImageFont.load_default()
    section_font = ImageFont.truetype(str(font_path), 10) if font_path.is_file() else ImageFont.load_default()

    # タイトル
    draw.text((30, 20), "RETRO EFFECT STRENGTH COMPARISON (retro_effect: 0 ~ 6)", font=title_font, fill=(240, 245, 255))
    draw.text((30, 45), "Non-destructive pipeline: applied exclusively to UI overlay layer (RGB shift -> Bloom -> Pixelate)", font=label_font, fill=(140, 150, 170))

    levels = [
        (0, "0: OFF (Clean Vector)", "Pristine modern UI"),
        (1, "1: Subtle (Digicam)", "Early 2000s LCD screen"),
        (2, "2: Classic (Y2K)", "Default 2000s Digicam"),
        (3, "3: Medium (MiniDV)", "Handycam / Toy camera"),
        (4, "4: Heavy (VHS)", "Retro VHS tape / CRT"),
        (5, "5: Extreme (CCTV)", "Security cam / Horror"),
        (6, "6: Near Break", "Readable limit of vision"),
    ]

    card_w = 150
    card_h = 400
    start_x = 30
    start_y = 85
    spacing = 15

    for idx, (lvl, title, desc) in enumerate(levels):
        cx = start_x + idx * (card_w + spacing)
        cy = start_y

        # 高解像度 (800x450) でレンダリングし、文字とマークを大きく鮮明に描写
        sample_w, sample_h = 800, 450
        base = get_base_image(sample_w, sample_h, tone="darkened")
        cfg = OverlayConfig(
            color="white",
            thickness=45,
            font_key="Roboto Condensed Bold(細長)",
            dot_style="glow_red",
            rec_label="REC",
            battery_bars=3,
            show_timecode=True,
            timecode_text="PM 08:30:15",
            retro_effect=lvl,
            bg_box_opacity=0.35,
        )
        comp = composite_with_config(base, cfg)

        # 上段: RECマークブロック (右上 w-165..w-15, 0..130)
        rec_crop = comp.crop((sample_w - card_w - 15, 0, sample_w - 15, 130))
        # 下段: タイムコード文字ブロック (右下 w-165..w-15, h-130..h)
        tc_crop = comp.crop((sample_w - card_w - 15, sample_h - 130, sample_w - 15, sample_h))

        # カード用画像 (150x260) に上段・下段を合体
        crop_composite = Image.new("RGB", (card_w, 260), (20, 24, 30))
        crop_composite.paste(rec_crop, (0, 0))
        crop_composite.paste(tc_crop, (0, 130))

        # 上下セクションの区切り線とサブヘッダー
        d_crop = ImageDraw.Draw(crop_composite)
        d_crop.line([(0, 129), (card_w, 129)], fill=(45, 52, 70), width=1)
        # タイムコード区切りラベル
        d_crop.rectangle([0, 130, card_w, 144], fill=(12, 15, 22, 200))
        d_crop.text((8, 131), "TIMECODE DETAIL", font=section_font, fill=(110, 125, 150))

        # カード枠
        draw.rounded_rectangle([cx, cy, cx + card_w, cy + card_h], radius=6, fill=(22, 26, 36), outline=(45, 52, 70), width=1)

        # クロップ画像を貼り付け
        im.paste(crop_composite, (cx, cy))

        # レベル番号バッジ (右上または左上)
        draw.rounded_rectangle([cx + 8, cy + 8, cx + 32, cy + 28], radius=3, fill=(255, 50, 60) if lvl == 2 else (30, 36, 48))
        draw.text((cx + 14, cy + 10), str(lvl), font=label_font, fill=(255, 255, 255))

        # テキスト説明
        draw.line([(cx, cy + 270), (cx + card_w, cy + 270)], fill=(45, 52, 70), width=1)
        draw.text((cx + 10, cy + 280), title.split(":")[1].strip(), font=label_font, fill=(230, 235, 245))
        draw.text((cx + 10, cy + 305), desc, font=label_font, fill=(130, 140, 160))

    im.save(output_path, "PNG", optimize=True)
    print(f"  -> Saved {output_path} ({os.path.getsize(output_path) // 1024} KB)")


def generate_color_presets(output_path: Path):
    """4. 6色プリセット＋ドットスタイルの比較画像 (1200x360) を生成する。"""
    print(f"[4/4] Generating color presets: {output_path.name}...")
    total_w, total_h = 1200, 360
    im = Image.new("RGB", (total_w, total_h), (15, 18, 24))
    draw = ImageDraw.Draw(im)

    font_path = ROOT_DIR / "fonts" / "ShareTechMono-Regular.ttf"
    title_font = ImageFont.truetype(str(font_path), 18) if font_path.is_file() else ImageFont.load_default()
    label_font = ImageFont.truetype(str(font_path), 12) if font_path.is_file() else ImageFont.load_default()

    draw.text((30, 20), "COLOR PRESETS & RETRO GLOW DOT STYLES", font=title_font, fill=(240, 245, 255))
    draw.text((30, 45), "Seamless automatic luminance inverted background box ensures legibility on any image", font=label_font, fill=(140, 150, 170))

    presets = [
        ("white", "White (Standard)", "glow_red", (255, 255, 255)),
        ("green", "Green (Night Vision)", "glow_green", (0, 255, 80)),
        ("cyan", "Cyan (Cyber HUD)", "glow_cyan", (0, 220, 255)),
        ("red", "Red (Emergency)", "flat_red", (255, 30, 30)),
        ("yellow", "Yellow (Hazard)", "glow_amber", (255, 225, 0)),
        ("black", "Black (Inverted Box)", "flat_red", (20, 20, 20)),
    ]

    card_w = 175
    card_h = 240
    start_x = 30
    start_y = 80
    spacing = 15

    for idx, (col, label, dot, rgb) in enumerate(presets):
        cx = start_x + idx * (card_w + spacing)
        cy = start_y

        sample_w, sample_h = 320, 240
        base = get_base_image(sample_w, sample_h, tone="darkened" if col != "black" else "warm_retro")
        cfg = OverlayConfig(
            color=col,
            thickness=40,
            font_key="Share Tech Mono(等幅)" if col in ("green", "cyan") else "Roboto Condensed Bold(細長)",
            dot_style=dot,
            rec_label="LIVE" if col == "green" else "REC",
            battery_bars=3,
            show_timecode=True,
            timecode_text="12:34:56",
            retro_effect=0,
            bg_box_opacity=0.35,
        )
        comp = composite_with_config(base, cfg)

        crop_rect = (sample_w - card_w - 15, 10, sample_w - 15, 10 + 160)
        cropped = comp.crop(crop_rect)

        draw.rounded_rectangle([cx, cy, cx + card_w, cy + card_h], radius=6, fill=(22, 26, 36), outline=(45, 52, 70), width=1)
        im.paste(cropped, (cx, cy))

        # カラーチップ
        draw.rectangle([cx + 10, cy + 175, cx + 22, cy + 187], fill=rgb, outline=(100, 100, 100))
        draw.text((cx + 28, cy + 173), label, font=label_font, fill=(230, 235, 245))
        draw.text((cx + 10, cy + 200), f"dot: {dot}", font=label_font, fill=(130, 140, 160))

    im.save(output_path, "PNG", optimize=True)
    print(f"  -> Saved {output_path} ({os.path.getsize(output_path) // 1024} KB)")


def main():
    out_dir = ROOT_DIR / "assets" / "demo"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=== Generating Official Demo Assets for rec-frame-ComfyUI ===")
    generate_hero_showcase(out_dir / "hero_showcase.png")
    generate_video_playback_gif(out_dir / "video_playback.gif")
    generate_retro_effect_levels(out_dir / "retro_effect_levels.png")
    generate_color_presets(out_dir / "color_presets.png")
    print("=== All Demo Assets Generated Successfully! ===")


if __name__ == "__main__":
    main()
