"""ファインダー風オーバーレイの純粋な画像生成層。GUI非依存。

SPEC.md §3 が正本。全寸法は `s = min(w, h)` 基準の相対値で決める。
PIL の `rectangle` は inclusive 描画のため、右・下隅は `-1` 補正で
四隅の端距離をピクセル一致させる (AGENTS.md 注意点)。
"""
from __future__ import annotations

import os
from dataclasses import replace
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

try:
    from .rec_config import (
        COLOR_PRESETS,
        DEFAULT_DOT_STYLE,
        DEFAULT_EFFECT,
        DEFAULT_FONT,
        DEFAULT_RETRO_EFFECT,
        DEFAULT_THICKNESS,
        DOT_ASSET_EXTENSIONS,
        FONT_CHOICES,
        EffectKey,
        OverlayColor,
        OverlayConfig,
        ThicknessKey,
        discover_dot_assets,
        get_local_fonts_dir,
        is_valid_custom_font_path,
        is_valid_dot_asset_path,
        parse_color_to_rgba,
        resolve_bundled_font_path,
        resolve_custom_font_path,
    )
except ImportError:
    from rec_config import (
        COLOR_PRESETS,
        DEFAULT_DOT_STYLE,
        DEFAULT_EFFECT,
        DEFAULT_FONT,
        DEFAULT_RETRO_EFFECT,
        DEFAULT_THICKNESS,
        DOT_ASSET_EXTENSIONS,
        FONT_CHOICES,
        EffectKey,
        OverlayColor,
        OverlayConfig,
        ThicknessKey,
        discover_dot_assets,
        get_local_fonts_dir,
        is_valid_custom_font_path,
        is_valid_dot_asset_path,
        parse_color_to_rgba,
        resolve_bundled_font_path,
        resolve_custom_font_path,
    )

# ━━━ 四隅L字枠 (SPEC §3.1) ━━━
MARGIN_RATIO = 0.020  # 四隅の端距離 int(s*0.020)
ARM_LEN_RATIO = 0.15   # L字の一辺 int(s*0.15)
# 枠太さは大・中・小の比率で切替。中=従来値。電池線幅は連動しない(枠のみ適用)。
THICKNESS_RATIOS: dict[str, float] = {
    "small": 0.005,
    "medium": 0.008,
    "large": 0.012,
}
THICKNESS_RATIO = THICKNESS_RATIOS["medium"]  # 後方互換エイリアス
MIN_THICKNESS = 2

# ━━━ 電池マーク (SPEC §3.2) ━━━
BAT_W_RATIO = 0.075
BAT_H_RATIO = 0.045
BAT_T_RATIO = 0.005
NUB_W_RATIO = 0.12  # 本体幅に対する比率
NUB_H_RATIO = 0.45  # 本体高に対する比率
BAT_BARS = 4

# ━━━ 赤丸＋REC (SPEC §3.3) ━━━
REC_FONT_RATIO = 0.055
MIN_REC_FONT_SIZE = 10
DOT_R_RATIO = 0.022
REC_GAP_RATIO = 0.012
RED = (255, 0, 0, 255)

# ━━━ 中央十字 (SPEC §3.4・§10.2) ━━━
CROSS_HALF_RATIO = 0.035  # 片腕 int(s*0.035)
CROSS_T_RATIO = 0.002  # 線幅 max(1, int(s*0.002)) — 枠より一回り細く

# ━━━ タイムコード (SPEC §3.5) ━━━
TIMECODE_FONT_RATIO = 0.04  # REC(0.055)より一回り小さく

# ━━━ 半透明座布団ボックス (SPEC §3.7) ━━━
BOX_PAD_X_RATIO = 0.010  # ボックス内左右余白
BOX_PAD_Y_RATIO = 0.008  # ボックス内上下余白
BOX_CLEARANCE_X_RATIO = 0.012  # L字枠縦線からのクリアランス
BOX_CLEARANCE_Y_RATIO = 0.010  # L字枠横線からのクリアランス

# ━━━ UI劣化エフェクト (SPEC §3.6) ━━━
SHIFT_BASE_RATIO = 0.002  # RGBシフト基準量 max(1, int(s*0.002))。弱×1 / 強×2
BLOOM_WEAK_RATIO_WHITE = 0.006  # ブルーム弱・白枠の半径 max(1, int(s*0.006))
BLOOM_WEAK_ALPHA_WHITE = 190  # ブルーム弱・白枠の発光層α
BLOOM_WEAK_RATIO_BLACK = 0.005  # ブルーム弱・黒枠は少し抑える
BLOOM_WEAK_ALPHA_BLACK = 160
BLOOM_STRONG_RATIO = 0.008  # ブルーム強の半径 max(1, int(s*0.008))
BLOOM_STRONG_ALPHA = 220  # ブルーム強の発光層のα
PIXEL_SCALE_WEAK = 0.5  # 低解像度化 (弱・2000s標準)。縮小BILINEAR→拡大NEAREST

# レトロエフェクト強度レベル定義 (0:OFF 〜 6:極限Break)
RETRO_EFFECT_LEVELS: dict[int, dict] = {
    0: {"name": "OFF (ノーマル)", "shift": 0, "bloom": "none", "pixel_scale": 1.0},
    1: {"name": "微弱 (Subtle)", "shift": 1, "bloom": "none", "pixel_scale": 0.8},
    2: {"name": "標準 (Classic 2000s)", "shift": 1, "bloom": "none", "pixel_scale": 0.5},
    3: {"name": "中 (Medium)", "shift": 2, "bloom": "weak", "pixel_scale": 0.4},
    4: {"name": "強 (Heavy)", "shift": 3, "bloom": "weak", "pixel_scale": 0.32},
    5: {"name": "超強 (Extreme)", "shift": 4, "bloom": "strong", "pixel_scale": 0.25},
    6: {"name": "極限Break (Near Break)", "shift": 6, "bloom": "strong", "pixel_scale": 0.18},
}

# プリセット定義 (後方互換・旧キーマッピング用)
EFFECT_PRESETS: dict[str, dict] = {
    "normal": RETRO_EFFECT_LEVELS[0],
    "2000s": RETRO_EFFECT_LEVELS[2],
    # 後方互換キー
    "off": RETRO_EFFECT_LEVELS[0],
    "oled": {"shift": 0, "bloom": "weak", "pixel_scale": 1.0},
}

@lru_cache(maxsize=64)
def _load_font(
    size: int,
    font_key: str = DEFAULT_FONT,
    custom_path: str | None = None,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """選択フォントを読み込む。OSシステムフォルダには一切アクセスせず同梱 fonts/ を優先。

    lru_cache で同一サイズ・フォントの再読込を避ける (描画結果は同一)。
    1. custom_path (絶対パス直接指定)
    2. resolve_bundled_font_path(font_key) (同梱 fonts/ ディレクトリ内)
    3. デフォルト同梱フォント (fonts/RobotoCondensed-Bold.ttf)
    4. fonts/ 内にある任意の .ttf/.otf
    5. ImageFont.load_default()
    """
    if custom_path:
        try:
            if Path(custom_path).is_file():
                return ImageFont.truetype(custom_path, size)
        except Exception:
            pass

    # 同梱フォント (fonts/ 内)
    bundled = resolve_bundled_font_path(font_key)
    if bundled is not None and bundled.is_file():
        try:
            return ImageFont.truetype(str(bundled), size)
        except Exception:
            pass

    # デフォルト同梱フォントへのフォールバック
    default_font_file = get_local_fonts_dir() / "RobotoCondensed-Bold.ttf"
    if default_font_file.is_file():
        try:
            return ImageFont.truetype(str(default_font_file), size)
        except Exception:
            pass

    # fonts/ ディレクトリ内にある任意のフォント
    local_dir = get_local_fonts_dir()
    if local_dir.is_dir():
        for p in local_dir.iterdir():
            if p.is_file() and p.suffix.lower() in (".ttf", ".otf", ".ttc"):
                try:
                    return ImageFont.truetype(str(p), size)
                except Exception:
                    continue

    return ImageFont.load_default()


def _custom_path_for(font_key: str, custom_fonts: dict[str, str] | None) -> str | None:
    """描画用のカスタム実パス。有効なフォントファイルのみ返す (欠落・非許可拡張子はNone→fallback)。"""
    p = resolve_custom_font_path(font_key, custom_fonts)
    if p is None:
        return None
    try:
        return str(p) if is_valid_custom_font_path(str(p)) else None
    except OSError:
        return None


@lru_cache(maxsize=32)
def _load_and_resize_dot_asset(asset_path: str, target_size: int) -> Image.Image | None:
    """丸マーク透過素材を読み込み、指定ピクセルサイズ (正方形) に高精度リサイズする。"""
    if not is_valid_dot_asset_path(asset_path):
        return None
    try:
        p = Path(asset_path)
        with Image.open(p) as im:
            rgba = im.convert("RGBA")
            # ターゲットサイズが1px未満にならないようガード
            safe_size = max(1, target_size)
            return rgba.resize((safe_size, safe_size), Image.Resampling.LANCZOS)
    except Exception:
        return None


def _is_classic_dot_style(dot_style: str | None) -> bool:
    return not dot_style or dot_style.startswith("classic") or dot_style == "default"


def _resolve_dot_asset_path(dot_style: str) -> str | None:
    """dot_style を素材ファイルパスへ解決する。

    1. `assets/dots/` 内の素材キー (ファイル stem、例: "flat_red")
    2. 画像ファイルの直接パス指定 (ノードの `custom_dot_path`)
    見つからない場合は None (呼び出し側で幾何円へフォールバック)。
    """
    asset = discover_dot_assets().get(dot_style)
    if asset:
        return asset
    if is_valid_dot_asset_path(dot_style):
        return str(Path(dot_style))
    return None


def _composite_dot_asset(overlay: Image.Image, asset_img: Image.Image, x: int, y: int) -> None:
    """マーク素材を overlay にアルファ合成する (座布団ボックス上でも正しい over 合成)。"""
    if x >= 0 and y >= 0:
        overlay.alpha_composite(asset_img, dest=(x, y))
        return
    # 極小画像で左上がはみ出す場合は、はみ出し部分を切り取って合成する
    sx, sy = max(0, -x), max(0, -y)
    if sx >= asset_img.width or sy >= asset_img.height:
        return
    overlay.alpha_composite(asset_img, dest=(max(0, x), max(0, y)), source=(sx, sy))


def _mono_color(color: OverlayColor | str, custom_color: str = "") -> tuple[int, int, int, int]:
    """枠・文字・十字などの描画色 (RGBA) を解決する。custom_color を最優先。"""
    if custom_color and isinstance(custom_color, str) and custom_color.strip():
        parsed = parse_color_to_rgba(custom_color.strip())
        if parsed is not None:
            return parsed
    parsed = parse_color_to_rgba(color)
    if parsed is not None:
        return parsed
    return (255, 255, 255, 255) if str(color).lower() == "white" else (0, 0, 0, 255)


def _color_luminance(color_rgba: tuple[int, int, int, int]) -> float:
    """描画色の知覚輝度 (0..255) を計算する (ITU-R BT.601)。"""
    return 0.299 * color_rgba[0] + 0.587 * color_rgba[1] + 0.114 * color_rgba[2]


def _bg_box_color(
    color_rgba: tuple[int, int, int, int] | OverlayColor | str,
    opacity: float,
) -> tuple[int, int, int, int] | None:
    """座布団ボックスの背景色を解決する。

    輝度連動: 極端に暗い色 (黒など輝度 < 60) は白半透明、それ以外 (白・緑・シアン・黄・赤など) は黒半透明。
    """
    if opacity <= 0.0:
        return None
    alpha = max(0, min(255, int(round(255 * opacity))))
    if isinstance(color_rgba, (tuple, list)) and len(color_rgba) >= 3:
        lum = _color_luminance(tuple(color_rgba[:4]))  # type: ignore[arg-type]
    else:
        parsed = parse_color_to_rgba(color_rgba)
        lum = _color_luminance(parsed) if parsed is not None else (255.0 if str(color_rgba).lower() == "white" else 0.0)

    # 暗色なら白半透明座布団、明色・蛍光色なら黒半透明座布団
    rgb = (255, 255, 255) if lum < 60.0 else (0, 0, 0)
    return (*rgb, alpha)


def _tight_ink_metrics(
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    text: str,
) -> tuple[int, int, int, int]:
    """anchor='lt' 描画時の厳密なインク左上オフセット (dx, dy) とインク寸法 (w, h) を返す。
    
    フォント固有のアセンダ・ディセンダ余白やサイドベアリングに影響されず、
    実際の描画ピクセル範囲に基づいたピクセルパーフェクトなセンタリングを実現する。
    """
    if not text or not text.strip():
        return 0, 0, 0, 0
    try:
        mask, offset = font.getmask2(text, anchor="lt")
        mb = mask.getbbox()
        if mb is not None:
            return offset[0] + mb[0], offset[1] + mb[1], mb[2] - mb[0], mb[3] - mb[1]
    except Exception:
        pass
    bbox = font.getbbox(text, anchor="lt")
    return bbox[0], bbox[1], bbox[2] - bbox[0], bbox[3] - bbox[1]


def _thickness_to_ratio(thickness: int | float | str = DEFAULT_THICKNESS) -> float:
    """0..100 の数値 (または small/medium/large 文字列) を短辺比率に換算する。

    - 0: 0.0010 (極細・短辺1000pxで約1px)
    - 50: 0.0080 (標準・旧mediumと完全一致)
    - 100: 0.0200 (極太・短辺1000pxで約20px)
    """
    if isinstance(thickness, (int, float)):
        val = max(0.0, min(100.0, float(thickness)))
        if val <= 50.0:
            return 0.0010 + (0.0080 - 0.0010) * (val / 50.0)
        return 0.0080 + (0.0200 - 0.0080) * ((val - 50.0) / 50.0)
    if isinstance(thickness, str):
        key = thickness.lower().strip()
        if key in THICKNESS_RATIOS:
            return THICKNESS_RATIOS[key]
        try:
            return _thickness_to_ratio(float(key))
        except ValueError:
            pass
    return THICKNESS_RATIOS["medium"]


def _frame_thickness(s: int, thickness: int | str = DEFAULT_THICKNESS) -> int:
    """四隅L字枠の線太さ。0..100 (または小中大) の比率で計算、最低1px。"""
    ratio = _thickness_to_ratio(thickness)
    return max(1, int(round(s * ratio)))


def _draw_corner_frames(
    d: ImageDraw.ImageDraw, w: int, h: int, s: int,
    mono: tuple[int, int, int, int],
    margin_x: int, margin_y: int, arm_len: int, thickness: int,
) -> None:
    # 左上 / 右上 / 左下 / 右下 のL字を4本の線分ではなく矩形で描く (角が綺麗)
    corners = [
        (margin_x, margin_y, 1, 1),                          # 左上
        (w - 1 - margin_x, margin_y, -1, 1),                 # 右上
        (margin_x, h - 1 - margin_y, 1, -1),                 # 左下
        (w - 1 - margin_x, h - 1 - margin_y, -1, -1),        # 右下
    ]
    for cx, cy, sx, sy in corners:
        # 横棒
        x0 = min(cx, cx + sx * arm_len)
        x1 = max(cx, cx + sx * arm_len)
        y0 = cy if sy > 0 else cy - thickness
        y1 = cy + thickness if sy > 0 else cy
        d.rectangle([x0, y0, x1, y1], fill=mono)
        # 縦棒
        x0 = cx if sx > 0 else cx - thickness
        x1 = cx + thickness if sx > 0 else cx
        y0 = min(cy, cy + sy * arm_len)
        y1 = max(cy, cy + sy * arm_len)
        d.rectangle([x0, y0, x1, y1], fill=mono)


def _draw_battery(
    d: ImageDraw.ImageDraw, s: int,
    margin_x: int, margin_y: int, thickness: int,
    mono: tuple[int, int, int, int],
    active_bars: int = BAT_BARS,
    bg_box_opacity: float = 0.0,
    bg_box_color: tuple[int, int, int, int] | None = None,
) -> None:
    bat_w = int(s * BAT_W_RATIO)
    bat_h = int(s * BAT_H_RATIO)
    nub_w = int(bat_w * NUB_W_RATIO)
    nub_h = int(bat_h * NUB_H_RATIO)
    total_w = bat_w + nub_w

    pad_x = max(2, int(round(s * BOX_PAD_X_RATIO)))
    pad_y = max(2, int(round(s * BOX_PAD_Y_RATIO)))
    clearance_x = max(2, int(round(s * BOX_CLEARANCE_X_RATIO)))
    clearance_y = max(2, int(round(s * BOX_CLEARANCE_Y_RATIO)))

    box_w = total_w + pad_x * 2
    box_h = bat_h + pad_y * 2

    # 左上L字枠の内側基準からクリアランスを確保
    box_x0 = (margin_x + thickness) + clearance_x
    box_y0 = (margin_y + thickness) + clearance_y
    box_x1 = box_x0 + box_w
    box_y1 = box_y0 + box_h

    if bg_box_opacity > 0 and bg_box_color is not None:
        d.rectangle([box_x0, box_y0, box_x1, box_y1], fill=bg_box_color)

    bat_x = box_x0 + pad_x
    bat_y = box_y0 + pad_y
    bat_t = max(MIN_THICKNESS, int(s * BAT_T_RATIO))
    d.rectangle([bat_x, bat_y, bat_x + bat_w, bat_y + bat_h],
                outline=mono, width=bat_t)
    # 電池の突起 (右側)
    nub_x = bat_x + bat_w
    nub_y = bat_y + (bat_h - nub_h) // 2
    d.rectangle([nub_x, nub_y, nub_x + nub_w, nub_y + nub_h],
                fill=mono)
    # 電池残量バー (4本スロット中、先頭 active_bars 本を描画)
    pad = bat_t + 1
    avail = bat_w - pad * 2
    if avail <= 0 or bat_h - pad * 2 < 0:
        # 極小画像では内幅・内高が取れないため残量バーを省略 (外枠・突起は描画済み)。
        # 内高チェックが無いと短辺 94〜133px 程度で y1 < y0 となり ValueError で落ちる。
        return
    pitch = avail / BAT_BARS
    bar_w = pitch * 0.5
    bars_to_draw = max(0, min(BAT_BARS, active_bars))
    for i in range(bars_to_draw):
        bx0 = bat_x + pad + i * pitch
        by0 = bat_y + pad
        bx1 = bx0 + bar_w
        by1 = bat_y + bat_h - pad
        d.rectangle([bx0, by0, bx1, by1], fill=mono)


def _draw_rec_indicator(
    overlay: Image.Image,
    d: ImageDraw.ImageDraw, w: int, s: int,
    margin_x: int, margin_y: int, thickness: int,
    mono: tuple[int, int, int, int], font_key: str,
    custom_fonts: dict[str, str] | None = None,
    rec_text: str = "REC",
    show_red_dot: bool = True,
    dot_style: str = DEFAULT_DOT_STYLE,
    bg_box_opacity: float = 0.0,
    bg_box_color: tuple[int, int, int, int] | None = None,
    red_dot_visible: bool = True,
) -> None:
    rec_font_size = max(MIN_REC_FONT_SIZE, int(s * REC_FONT_RATIO))
    font = _load_font(rec_font_size, font_key, _custom_path_for(font_key, custom_fonts))
    label = rec_text if rec_text else "REC"
    dot_r = int(s * DOT_R_RATIO)
    dot_diam = dot_r * 2
    gap = int(s * REC_GAP_RATIO)

    pad_x = max(2, int(round(s * BOX_PAD_X_RATIO)))
    pad_y = max(2, int(round(s * BOX_PAD_Y_RATIO)))
    clearance_x = max(2, int(round(s * BOX_CLEARANCE_X_RATIO)))
    clearance_y = max(2, int(round(s * BOX_CLEARANCE_Y_RATIO)))

    has_text = bool(label.strip())
    if has_text:
        ink_dx, ink_dy, text_w, text_h = _tight_ink_metrics(font, label)
    else:
        ink_dx, ink_dy, text_w, text_h = 0, 0, 0, 0

    content_w = (dot_diam if show_red_dot else 0) + (gap if show_red_dot and has_text else 0) + (text_w if has_text else 0)
    content_h = max(dot_diam if show_red_dot else 0, text_h if has_text else 0)

    box_w = content_w + pad_x * 2
    box_h = content_h + pad_y * 2

    # 右上L字枠の内側基準からクリアランスを確保
    box_x1 = (w - 1 - margin_x - thickness) - clearance_x
    box_x0 = box_x1 - box_w
    box_y0 = (margin_y + thickness) + clearance_y
    box_y1 = box_y0 + box_h

    if bg_box_opacity > 0 and bg_box_color is not None:
        d.rectangle([box_x0, box_y0, box_x1, box_y1], fill=bg_box_color)

    cy = box_y0 + box_h // 2
    curr_x = box_x0 + pad_x

    if show_red_dot and red_dot_visible:
        dot_y0 = cy - dot_r
        asset_img = None
        if not _is_classic_dot_style(dot_style):
            target_path = _resolve_dot_asset_path(dot_style)
            if target_path:
                asset_img = _load_and_resize_dot_asset(target_path, dot_diam)
        if asset_img is not None:
            # 透過素材を over 合成 (paste だと座布団上でαが補間され薄くなる)
            _composite_dot_asset(overlay, asset_img, curr_x, dot_y0)
        else:
            # classic 指定、または素材が見つからない場合は幾何円 (常に赤)
            d.ellipse([curr_x, dot_y0, curr_x + dot_diam, dot_y0 + dot_diam], fill=RED)
    if show_red_dot:
        # 点滅の消灯時 (red_dot_visible=False) も赤丸分の幅を確保し、文字位置を固定する
        curr_x += dot_diam + gap

    # REC文字 (枠色に連動、インク中心を cy に一致)
    if has_text:
        text_ink_y0 = cy - text_h // 2
        draw_x = curr_x - ink_dx
        draw_y = text_ink_y0 - ink_dy
        d.text((draw_x, draw_y), label, font=font, fill=mono, anchor="lt")


def _draw_center_cross(
    d: ImageDraw.ImageDraw, w: int, h: int, s: int,
    mono: tuple[int, int, int, int],
) -> None:
    """画像センターの十字マーク。枠色に連動、枠太さには連動しない。"""
    half = int(s * CROSS_HALF_RATIO)
    t = max(1, int(s * CROSS_T_RATIO))
    cx, cy = w // 2, h // 2
    d.rectangle([cx - half, cy - t // 2, cx + half, cy + t // 2], fill=mono)
    d.rectangle([cx - t // 2, cy - half, cx + t // 2, cy + half], fill=mono)


def _draw_timecode(
    d: ImageDraw.ImageDraw, w: int, h: int, s: int,
    margin_x: int, margin_y: int, thickness: int,
    mono: tuple[int, int, int, int], font_key: str, text: str,
    custom_fonts: dict[str, str] | None = None,
    bg_box_opacity: float = 0.0,
    bg_box_color: tuple[int, int, int, int] | None = None,
) -> None:
    """右下の日時表示。枠色・RECフォントに連動、枠太さには連動しない。

    手入力テキストを単一行で描画する。
    空文字・空白のみの場合は何も描画しない。
    """
    if not text or not text.strip():
        return
    font_size = max(MIN_REC_FONT_SIZE, int(s * TIMECODE_FONT_RATIO))
    font = _load_font(font_size, font_key, _custom_path_for(font_key, custom_fonts))
    tc_dx, tc_dy, tc_w, tc_h = _tight_ink_metrics(font, text)

    pad_x = max(2, int(round(s * BOX_PAD_X_RATIO)))
    pad_y = max(2, int(round(s * BOX_PAD_Y_RATIO)))
    clearance_x = max(2, int(round(s * BOX_CLEARANCE_X_RATIO)))
    clearance_y = max(2, int(round(s * BOX_CLEARANCE_Y_RATIO)))

    tc_box_w = tc_w + pad_x * 2
    tc_box_h = tc_h + pad_y * 2

    # 右下隅のL字枠の内側基準からクリアランスを確保
    tc_box_x1 = (w - 1 - margin_x - thickness) - clearance_x
    tc_box_x0 = tc_box_x1 - tc_box_w
    tc_box_y1 = (h - 1 - margin_y - thickness) - clearance_y
    tc_box_y0 = tc_box_y1 - tc_box_h

    if bg_box_opacity > 0 and bg_box_color is not None:
        d.rectangle([tc_box_x0, tc_box_y0, tc_box_x1, tc_box_y1], fill=bg_box_color)

    tc_cy = tc_box_y0 + tc_box_h // 2
    tc_ink_x0 = tc_box_x0 + pad_x
    tc_ink_y0 = tc_cy - tc_h // 2
    tc_draw_x = tc_ink_x0 - tc_dx
    tc_draw_y = tc_ink_y0 - tc_dy
    d.text((tc_draw_x, tc_draw_y), text, font=font, fill=mono, anchor="lt")


# ━━━ 撮影日時モード (SPEC §3.5) ━━━
EXIF_DATETIME_TAGS: tuple[int, ...] = (36867, 36868, 306)


def parse_exif_datetimestr(value: str | bytes | None) -> datetime | None:
    """EXIF日時文字列 `YYYY:MM:DD HH:MM:SS` をパースする。不正はNone。"""
    if isinstance(value, bytes):
        try:
            value = value.decode("ascii", "ignore")
        except Exception:
            return None
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value.strip().rstrip("\x00").strip(), "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None


def format_photo_timecode(dt: datetime) -> str:
    """撮影日時をタイムコード書式 `YYYY/MM/DD AM/PM HH:MM` に整形する。"""
    ampm = "AM" if dt.hour < 12 else "PM"
    h12 = dt.hour % 12 or 12
    return f"{dt.year:04d}/{dt.month:02d}/{dt.day:02d} {ampm} {h12:02d}:{dt.minute:02d}"


def photo_timecode_text(
    img: Image.Image | None = None,
    path: str | Path | None = None,
    fallback: str = "",
) -> str:
    """写真毎の日文字列を `EXIF→ファイルmtime→固定文` の順で解決する。"""
    if img is not None:
        try:
            exif = img.getexif()
            if exif:
                for tag in EXIF_DATETIME_TAGS:
                    dt = parse_exif_datetimestr(exif.get(tag))
                    if dt is not None:
                        return format_photo_timecode(dt)
        except Exception:
            pass
    if path is not None:
        try:
            dt = datetime.fromtimestamp(os.stat(path).st_mtime)
            return format_photo_timecode(dt)
        except (OSError, ValueError, OverflowError):
            pass
    return fallback


def resolve_timecode_text(
    config: OverlayConfig,
    img: Image.Image | None = None,
    path: str | Path | None = None,
) -> str:
    """描画に使う日時文。撮影日時モードONなら写真毎に解決、OFFなら固定文。"""
    if config.timecode_from_exif:
        return photo_timecode_text(img, path, config.timecode_text)
    return config.timecode_text


def resolve_photo_config(
    config: OverlayConfig,
    img: Image.Image | None = None,
    path: str | Path | None = None,
) -> OverlayConfig:
    """写真毎の日時を反映した描画用設定。元の設定は変更しない。"""
    text = resolve_timecode_text(config, img, path)
    if text == config.timecode_text:
        return config
    return replace(config, timecode_text=text)


def _shift_channel(ch: Image.Image, dx: int) -> Image.Image:
    """1ch画像を水平シフトする。はみ出しは0クリア (wrapさせない)。"""
    if dx == 0:
        return ch
    return ch.transform(ch.size, Image.AFFINE, (1, 0, dx, 0, 1, 0),
                        fillcolor=0)


def _apply_rgb_shift(overlay: Image.Image, level: int, s: int) -> Image.Image:
    """色収差: Rを左へ・Bを右へずらす。GとAは固定。level 1=弱 / 2=強。"""
    if level <= 0:
        return overlay
    d = max(1, int(s * SHIFT_BASE_RATIO)) * level
    r, g, b, a = overlay.split()
    return Image.merge("RGBA", (_shift_channel(r, d), g,
                                _shift_channel(b, -d), a))


def _apply_bloom(overlay: Image.Image, strength: str, s: int,
                 color: OverlayColor | str = "white") -> Image.Image:
    """発光: ぼかし複製を背後に敷き、元のUIを上に重ねる。"""
    if strength == "none":
        return overlay
    if strength == "strong":
        ratio, alpha = BLOOM_STRONG_RATIO, BLOOM_STRONG_ALPHA
    else:
        # 暗色判定: black または 輝度 < 60
        parsed = parse_color_to_rgba(color) if isinstance(color, str) else color
        is_dark = (parsed is not None and _color_luminance(parsed) < 60.0) if parsed else (str(color).lower() == "black")
        if is_dark:
            ratio, alpha = BLOOM_WEAK_RATIO_BLACK, BLOOM_WEAK_ALPHA_BLACK
        else:
            ratio, alpha = BLOOM_WEAK_RATIO_WHITE, BLOOM_WEAK_ALPHA_WHITE
    radius = max(1, int(s * ratio))
    glow = overlay.filter(ImageFilter.GaussianBlur(radius))
    r, g, b, a = glow.split()
    a = a.point(lambda v: v * alpha // 255)
    glow = Image.merge("RGBA", (r, g, b, a))
    return Image.alpha_composite(glow, overlay)


def _apply_pixelation(overlay: Image.Image, scale: float) -> Image.Image:
    """低解像度化: 縮小 (BILINEARで細線消失を抑える) →等倍復元 (NEAREST)。"""
    if scale >= 1.0:
        return overlay
    w, h = overlay.size
    small = overlay.resize((max(1, round(w * scale)), max(1, round(h * scale))),
                           Image.Resampling.BILINEAR)
    return small.resize((w, h), Image.Resampling.NEAREST)


def apply_ui_effects(
    overlay: Image.Image,
    preset: int | EffectKey | str = DEFAULT_RETRO_EFFECT,
    s: int | None = None,
    color: OverlayColor | str = "white",
) -> Image.Image:
    """描画済みUIレイヤーにレトロエフェクト（0〜6）またはプリセットを適用して返す (SPEC §3.6)."""
    p: dict | None = None
    if isinstance(preset, int):
        p = RETRO_EFFECT_LEVELS.get(max(0, min(6, preset)), RETRO_EFFECT_LEVELS[0])
    elif isinstance(preset, str):
        # 数値文字列 "0".."6" の解釈
        try:
            val = int(round(float(preset.strip())))
            p = RETRO_EFFECT_LEVELS.get(max(0, min(6, val)), RETRO_EFFECT_LEVELS[0])
        except ValueError:
            p = EFFECT_PRESETS.get(preset.strip().lower(), EFFECT_PRESETS["normal"])
    else:
        p = RETRO_EFFECT_LEVELS[0]

    if p is None or (p["shift"] <= 0 and p["bloom"] == "none" and p["pixel_scale"] >= 1.0):
        return overlay

    if s is None:
        s = min(overlay.size)
    overlay = _apply_rgb_shift(overlay, p["shift"], s)
    overlay = _apply_bloom(overlay, p["bloom"], s, color)
    overlay = _apply_pixelation(overlay, p["pixel_scale"])
    return overlay


def apply_custom_ui_effects(
    overlay: Image.Image,
    shift_level: int = 0,
    bloom_strength: str = "none",
    pixel_scale: float = 1.0,
    s: int | None = None,
    color: OverlayColor | str = "white",
) -> Image.Image:
    """ComfyUI 詳細ノード用: 個別パラメータでUI劣化エフェクトを適用する。

    順序は RGBシフト→ブルーム→低解像度化で固定。
    """
    if shift_level <= 0 and bloom_strength == "none" and pixel_scale >= 1.0:
        return overlay
    if s is None:
        s = min(overlay.size)
    overlay = _apply_rgb_shift(overlay, shift_level, s)
    overlay = _apply_bloom(overlay, bloom_strength, s, color)
    overlay = _apply_pixelation(overlay, pixel_scale)
    return overlay


def create_rec_overlay(w: int, h: int, color: OverlayColor | str = "black",
                       font_key: str = DEFAULT_FONT,
                       thickness: int | ThicknessKey | str = DEFAULT_THICKNESS,
                       show_frame: bool = True,
                       show_battery: bool = True,
                       show_rec: bool = True,
                       show_cross: bool = False,
                       show_timecode: bool = False,
                       timecode_text: str = "",
                       effect: EffectKey | str = DEFAULT_EFFECT,
                       custom_fonts: dict[str, str] | None = None,
                       dot_style: str = DEFAULT_DOT_STYLE,
                       bg_box_opacity: float = 0.10,
                       custom_color: str = "") -> Image.Image:
    """指定サイズと同寸の透過オーバーレイ(RGBA)を生成する。"""
    return create_rec_overlay_with_config(
        w, h, OverlayConfig(color=color, custom_color=custom_color, font_key=font_key, thickness=thickness,
                            show_frame=show_frame, show_battery=show_battery,
                            show_rec=show_rec, show_cross=show_cross,
                            show_timecode=show_timecode, timecode_text=timecode_text,
                            effect=effect,
                            custom_fonts=dict(custom_fonts or {}),
                            dot_style=dot_style,
                            bg_box_opacity=bg_box_opacity))


def create_rec_overlay_with_config(w: int, h: int, config: OverlayConfig) -> Image.Image:
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    s = min(w, h)  # 基準スケール
    m_ratio = config.margin_ratio if config.margin_ratio is not None else MARGIN_RATIO
    a_ratio = config.arm_len_ratio if config.arm_len_ratio is not None else ARM_LEN_RATIO
    margin = int(s * m_ratio)
    margin_x = margin
    margin_y = margin
    arm_len = int(s * a_ratio)
    thickness = _frame_thickness(s, config.thickness)
    mono = _mono_color(config.color, config.custom_color)
    bg_box_col = _bg_box_color(mono, config.bg_box_opacity)

    if config.show_frame:
        _draw_corner_frames(d, w, h, s, mono, margin_x, margin_y, arm_len, thickness)
    if config.show_battery:
        _draw_battery(d, s, margin_x, margin_y, thickness, mono,
                      active_bars=config.battery_bars,
                      bg_box_opacity=config.bg_box_opacity,
                      bg_box_color=bg_box_col)
    if config.show_rec:
        _draw_rec_indicator(overlay, d, w, s, margin_x, margin_y, thickness, mono,
                            config.font_key, config.custom_fonts,
                            rec_text=config.rec_label, show_red_dot=config.show_red_dot,
                            dot_style=config.dot_style,
                            bg_box_opacity=config.bg_box_opacity,
                            bg_box_color=bg_box_col,
                            red_dot_visible=config.red_dot_visible)
    if config.show_cross:
        _draw_center_cross(d, w, h, s, mono)
    if config.show_timecode:
        _draw_timecode(d, w, h, s, margin_x, margin_y, thickness,
                       mono, config.font_key, config.timecode_text,
                       config.custom_fonts,
                       bg_box_opacity=config.bg_box_opacity,
                       bg_box_color=bg_box_col)

    # UI劣化エフェクトはベクター描画の完了後にUI層へ適用し、合成は不変 (SPEC §3.6)。
    # retro_effect (0..6) を最優先し、未指定(0)かつ旧 effect が設定されている場合は旧 effect を適用
    eff_key: int | str = config.retro_effect
    if eff_key == 0 and config.effect not in ("normal", "off"):
        eff_key = config.effect
    color_hint = "black" if _color_luminance(mono) < 60.0 else "white"
    overlay = apply_ui_effects(overlay, eff_key, s, color_hint)

    return overlay


def composite_with_overlay(base: Image.Image, color: OverlayColor | str = "black",
                           font_key: str = DEFAULT_FONT,
                           thickness: int | ThicknessKey | str = DEFAULT_THICKNESS,
                           show_frame: bool = True,
                           show_battery: bool = True,
                           show_rec: bool = True,
                           show_cross: bool = False,
                           show_timecode: bool = False,
                           timecode_text: str = "",
                           effect: EffectKey | str = DEFAULT_EFFECT,
                           custom_fonts: dict[str, str] | None = None,
                           dot_style: str = DEFAULT_DOT_STYLE,
                           bg_box_opacity: float = 0.10) -> Image.Image:
    """ベース画像にREC枠を合成したRGBA画像を返す。"""
    return composite_with_config(
        base, OverlayConfig(color=color, font_key=font_key, thickness=thickness,
                            show_frame=show_frame, show_battery=show_battery,
                            show_rec=show_rec, show_cross=show_cross,
                            show_timecode=show_timecode, timecode_text=timecode_text,
                            effect=effect,
                            custom_fonts=dict(custom_fonts or {}),
                            dot_style=dot_style,
                            bg_box_opacity=bg_box_opacity))


def composite_with_config(base: Image.Image, config: OverlayConfig) -> Image.Image:
    w, h = base.size
    overlay = create_rec_overlay_with_config(w, h, config)
    bg = base.convert("RGBA")
    return Image.alpha_composite(bg, overlay)


def load_base_image(path: str | Path) -> Image.Image:
    """EXIF Orientationを反映して開く (外部ビューア表示と一致させる)。"""
    return ImageOps.exif_transpose(Image.open(path))


def prepare_image_for_save(img: Image.Image, dest_path: str | Path) -> Image.Image:
    """保存先拡張子に応じた変換。JPEGはRGB変換、それ以外はそのまま。"""
    if str(dest_path).lower().endswith((".jpg", ".jpeg")):
        return img.convert("RGB")
    return img


def save_composited_image(img: Image.Image, dest_path: str | Path) -> None:
    """合成済み画像を拡張子に応じて保存。JPEGは quality=95。"""
    is_jpeg = str(dest_path).lower().endswith((".jpg", ".jpeg"))
    out = prepare_image_for_save(img, dest_path)
    if is_jpeg:
        out.save(dest_path, quality=95)
    else:
        out.save(dest_path)
