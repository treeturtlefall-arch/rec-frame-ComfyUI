"""ComfyUI カスタムノード定義。

`rec-frame-app` の描画エンジン (`rec_overlay.py` / `rec_config.py`) を
ComfyUI の IMAGE / MASK パイプラインに接続し、さらにカスタム拡張ノードを提供する。
"""
from __future__ import annotations

import calendar
import io
import json
import logging
import os
import random
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image

try:
    import folder_paths
except ImportError:
    folder_paths = None

try:
    import server
    prompt_server = server.PromptServer.instance
except Exception:
    prompt_server = None

try:
    from .rec_config import (
        DEFAULT_DOT_STYLE,
        DEFAULT_EFFECT,
        DEFAULT_FONT,
        DEFAULT_RETRO_EFFECT,
        DEFAULT_THICKNESS,
        FONT_CHOICES,
        OverlayConfig,
        advance_smpte_timecode,
        discover_custom_fonts,
        get_all_dot_styles,
        get_all_font_names,
        is_valid_custom_font_path,
        is_valid_dot_asset_path,
        parse_clock_sec_text,
        parse_color_to_rgba,
        parse_smpte_text,
        parse_timecode_sec_text,
        parse_timecode_text,
    )
    from .rec_overlay import (
        ARM_LEN_RATIO,
        EFFECT_PRESETS,
        MARGIN_RATIO,
        RETRO_EFFECT_LEVELS,
        apply_custom_ui_effects,
        create_rec_overlay_with_config,
        format_photo_timecode,
        format_photo_timecode_sec,
    )
except ImportError:
    from rec_config import (
        DEFAULT_DOT_STYLE,
        DEFAULT_EFFECT,
        DEFAULT_FONT,
        DEFAULT_RETRO_EFFECT,
        DEFAULT_THICKNESS,
        FONT_CHOICES,
        OverlayConfig,
        advance_smpte_timecode,
        discover_custom_fonts,
        get_all_dot_styles,
        get_all_font_names,
        is_valid_custom_font_path,
        is_valid_dot_asset_path,
        parse_clock_sec_text,
        parse_color_to_rgba,
        parse_smpte_text,
        parse_timecode_sec_text,
        parse_timecode_text,
    )
    from rec_overlay import (
        ARM_LEN_RATIO,
        EFFECT_PRESETS,
        MARGIN_RATIO,
        RETRO_EFFECT_LEVELS,
        apply_custom_ui_effects,
        create_rec_overlay_with_config,
        format_photo_timecode,
        format_photo_timecode_sec,
    )

logger = logging.getLogger(__name__)


COLOR_MAP: dict[str, str] = {
    "white (白)": "white",
    "black (黒)": "black",
    "green (暗視グリーン)": "green",
    "cyan (サイバーHUD)": "cyan",
    "red (警告レッド)": "red",
    "yellow (ハザードイエロー)": "yellow",
    # 小文字・英語・単語キー (後方互換・API用)
    "white": "white",
    "black": "black",
    "green": "green",
    "cyan": "cyan",
    "red": "red",
    "yellow": "yellow",
    "白": "white",
    "黒": "black",
}

THICKNESS_MAP: dict[str, str] = {
    "small (小)": "small",
    "medium (中)": "medium",
    "large (大)": "large",
    "small": "small",
    "medium": "medium",
    "large": "large",
    "小": "small",
    "中": "medium",
    "大": "large",
}

EFFECT_MAP: dict[str, str] = {
    "normal (ノーマル)": "normal",
    "2000s (2000sデジカメ風)": "2000s",
    "normal": "normal",
    "2000s": "2000s",
    "ノーマル": "normal",
    "2000sデジカメ風": "2000s",
    # 後方互換用
    "off (OFF・クリーン)": "normal",
    "oled (OLED・微発光)": "normal",
    "2000s (2000sデジカメ)": "2000s",
    "off": "normal",
    "oled": "normal",
    "OFF(クリーン)": "normal",
    "OLED(微発光)": "normal",
    "2000sデジカメ": "2000s",
}

TIMECODE_MODE_MAP: dict[str, str] = {
    "manual (手入力テキスト)": "manual",
    "now (現在時刻を自動取得)": "now",
    "now_sec (現在時刻・秒単位)": "now_sec",
    "smpte (フレーム 00:00:00:00)": "smpte",
    # 後方互換・短縮キー
    "manual": "manual",
    "now": "now",
    "now_sec": "now_sec",
    "smpte": "smpte",
}

TIMECODE_CHOICES_IMAGE = [
    "manual (手入力テキスト)",
    "now (現在時刻を自動取得)",
    "now_sec (現在時刻・秒単位)",
]

TIMECODE_CHOICES_VIDEO = [
    "now_sec (現在時刻・秒単位)",
    "smpte (フレーム 00:00:00:00)",
    "now (現在時刻を自動取得)",
    "manual (手入力テキスト)",
]

BLOOM_MAP: dict[str, str] = {
    "preset (プリセットに従う)": "preset",
    "none (なし)": "none",
    "weak (弱・OLED相当)": "weak",
    "strong (強)": "strong",
    "preset": "preset",
    "none": "none",
    "weak": "weak",
    "strong": "strong",
}

BG_COLOR_MAP: dict[str, str] = {
    "black (黒)": "black",
    "white (白)": "white",
    "gray (グレー)": "gray",
    "checker (透過市松)": "checker",
    "black": "black",
    "white": "white",
    "gray": "gray",
    "checker": "checker",
}

PREVIEW_SIZE_MAP: dict[str, tuple[int, int]] = {
    "1280x720 (16:9 HD)": (1280, 720),
    "1920x1080 (16:9 FHD)": (1920, 1080),
    "1024x1024 (1:1 正方形)": (1024, 1024),
    "720x1280 (9:16 縦動画)": (720, 1280),
    "1280x720": (1280, 720),
    "1920x1080": (1920, 1080),
    "1024x1024": (1024, 1024),
    "720x1280": (720, 1280),
}


def create_preview_background(w: int, h: int, bg_color: str = "black") -> Image.Image:
    """指定された背景色（黒・白・グレー・市松模様）の RGB PIL 画像を生成する。"""
    c = BG_COLOR_MAP.get(bg_color, "black")
    if c == "white":
        return Image.new("RGB", (w, h), (255, 255, 255))
    elif c == "gray":
        return Image.new("RGB", (w, h), (128, 128, 128))
    elif c == "checker":
        tile = max(16, min(w, h) // 32)
        c1 = np.array([235, 235, 235], dtype=np.uint8)
        c2 = np.array([190, 190, 190], dtype=np.uint8)
        y, x = np.ogrid[:h, :w]
        mask = ((x // tile) + (y // tile)) % 2 == 0
        arr = np.where(mask[..., None], c1, c2)
        return Image.fromarray(arr, mode="RGB")
    return Image.new("RGB", (w, h), (0, 0, 0))


def tensor_to_pil(img_tensor: torch.Tensor) -> Image.Image:
    """単一フレーム Tensor [H, W, C] (float 0..1) を PIL Image (RGB or RGBA) に変換する。"""
    arr = np.clip(img_tensor.detach().cpu().numpy() * 255.0, 0, 255).round().astype(np.uint8)
    if arr.ndim == 2:
        return Image.fromarray(arr, mode="L").convert("RGB")
    if arr.shape[2] == 4:
        return Image.fromarray(arr, mode="RGBA")
    return Image.fromarray(arr[:, :, :3], mode="RGB")


def pil_rgb_to_tensor(img: Image.Image) -> torch.Tensor:
    """PIL Image を RGB Tensor [H, W, 3] (float32 0..1) に変換する。"""
    rgb = img.convert("RGB")
    arr = np.asarray(rgb, dtype=np.float32) / 255.0
    return torch.from_numpy(arr)


def pil_rgba_to_tensor_and_mask(img: Image.Image) -> tuple[torch.Tensor, torch.Tensor]:
    """PIL Image (RGBA) を RGBA Tensor [H, W, 4] と Alpha MASK [H, W] (float32 0..1) に変換する。"""
    rgba = img.convert("RGBA")
    arr = np.asarray(rgba, dtype=np.float32) / 255.0
    rgba_tensor = torch.from_numpy(arr)
    mask_tensor = torch.from_numpy(arr[:, :, 3])
    return rgba_tensor, mask_tensor


def _strip_path(raw: str | None) -> str:
    """ウィジェット入力のパス文字列から前後空白・引用符を除去する。"""
    return (raw or "").strip().strip('"').strip("'").strip()


def _parse_thickness(thickness: Any) -> int | str:
    """thickness 入力 (INT スライダー / 旧ワークフローの小中大文字列 / 数値文字列) を正規化する。"""
    if isinstance(thickness, (int, float)) and not isinstance(thickness, bool):
        return max(0, min(100, int(round(thickness))))
    if isinstance(thickness, str):
        key = THICKNESS_MAP.get(thickness.strip())
        if key is not None:
            return key
        try:
            return max(0, min(100, int(round(float(thickness)))))
        except ValueError:
            pass
    return DEFAULT_THICKNESS


class OverlayBuildResult(tuple):
    """5要素タプル互換かつ tc_kind / tc_val 属性を持つビルド結果コンテナ。"""

    def __new__(
        cls,
        base_config: OverlayConfig,
        effect_params: dict[str, Any] | None,
        c_key: str,
        base_tc_text: str,
        base_dt: datetime | None,
        tc_kind: str = "static",
        tc_val: Any = None,
    ) -> OverlayBuildResult:
        return super().__new__(
            cls,
            (base_config, effect_params, c_key, base_tc_text, base_dt),
        )

    def __init__(
        self,
        base_config: OverlayConfig,
        effect_params: dict[str, Any] | None,
        c_key: str,
        base_tc_text: str,
        base_dt: datetime | None,
        tc_kind: str = "static",
        tc_val: Any = None,
    ) -> None:
        self.tc_kind = tc_kind
        self.tc_val = tc_val


def _resolve_timecode_info(mode: str, manual_text: str) -> tuple[str, Any, str]:
    """タイムコードの進行モードと初期基準値を解決する。

    返り値: (kind, base_val, initial_text)
    kind: "now" | "now_sec" | "smpte" | "datetime_min" | "datetime_sec" | "static"
    """
    manual_clean = (manual_text or "").strip()

    if mode == "now":
        now = datetime.now()
        return ("now", now, format_photo_timecode(now))
    elif mode == "now_sec":
        now = datetime.now()
        return ("now_sec", now, format_photo_timecode_sec(now))
    elif mode == "smpte":
        parsed_smpte = parse_smpte_text(manual_clean)
        smpte_tuple = parsed_smpte if parsed_smpte is not None else (0, 0, 0, 0)
        init_text = f"{smpte_tuple[0]:02d}:{smpte_tuple[1]:02d}:{smpte_tuple[2]:02d}:{smpte_tuple[3]:02d}"
        return ("smpte", smpte_tuple, init_text)

    # mode == "manual" の場合: 入力テキストの形式を自動判別
    # 1. SMPTE (HH:MM:SS:FF / HH:MM:SS;FF)
    parsed_smpte = parse_smpte_text(manual_clean)
    if parsed_smpte is not None:
        init_text = f"{parsed_smpte[0]:02d}:{parsed_smpte[1]:02d}:{parsed_smpte[2]:02d}:{parsed_smpte[3]:02d}"
        return ("smpte", parsed_smpte, init_text)

    # 2. 秒付き日時 (YYYY/MM/DD AM/PM HH:MM:SS)
    parsed_sec = parse_timecode_sec_text(manual_clean)
    if parsed_sec is not None:
        year, month, day, ampm, hour, minute, second = parsed_sec
        h24 = hour % 12 + (12 if ampm == "PM" else 0)
        year = max(1, min(9999, year))
        month = max(1, min(12, month))
        day = max(1, min(calendar.monthrange(year, month)[1], day))
        dt = datetime(year, month, day, h24, max(0, min(59, minute)), max(0, min(59, second)))
        return ("datetime_sec", dt, format_photo_timecode_sec(dt))

    # 3. 分単位日時 (YYYY/MM/DD AM/PM HH:MM)
    parsed_min = parse_timecode_text(manual_clean)
    if parsed_min is not None:
        year, month, day, ampm, hour, minute = parsed_min
        h24 = hour % 12 + (12 if ampm == "PM" else 0)
        year = max(1, min(9999, year))
        month = max(1, min(12, month))
        day = max(1, min(calendar.monthrange(year, month)[1], day))
        dt = datetime(year, month, day, h24, max(0, min(59, minute)))
        return ("datetime_min", dt, format_photo_timecode(dt))

    # 4. 時刻のみ HH:MM:SS
    parsed_clock = parse_clock_sec_text(manual_clean)
    if parsed_clock is not None:
        h, m_val, s = parsed_clock
        init_smpte = (h, m_val, s, 0)
        init_text = f"{h:02d}:{m_val:02d}:{s:02d}:00"
        return ("smpte", init_smpte, init_text)

    # 5. 上記以外の自由文字列 (固定表示)
    return ("static", None, manual_clean)


def _compute_frame_timecode(
    kind: str,
    base_val: Any,
    initial_text: str,
    frame_idx: int,
    fps: float,
) -> str:
    """フレーム番号と進行モードに応じたタイムコード文字列を算出する。"""
    if kind == "static" or fps <= 0.0:
        return initial_text

    if kind == "smpte":
        h, m, s, f = base_val
        return advance_smpte_timecode(h, m, s, f, frame_idx, fps)
    elif kind in ("datetime_sec", "now_sec"):
        elapsed_sec = frame_idx / float(fps)
        return format_photo_timecode_sec(base_val + timedelta(seconds=elapsed_sec))
    elif kind in ("datetime_min", "now"):
        elapsed_sec = frame_idx / float(fps)
        return format_photo_timecode(base_val + timedelta(seconds=elapsed_sec))
    return initial_text


def _resolve_base_datetime(mode: str, manual_text: str) -> datetime | None:
    """タイムコード基準時刻を解決する（後方互換用）。"""
    kind, val, _ = _resolve_timecode_info(mode, manual_text)
    if isinstance(val, datetime):
        return val
    return None


def build_overlay_config_from_params(
    params: dict[str, Any],
) -> tuple[OverlayConfig, dict[str, Any] | None, str, str, datetime | None]:
    """ウィジェット引数辞書から OverlayConfig とエフェクトパラメータを共通解決する。"""
    color = params.get("color", "black (黒)")
    font_key = params.get("font_key", DEFAULT_FONT)
    raw_retro = params.get("retro_effect")
    if raw_retro is not None:
        try:
            retro_eff = max(0, min(6, int(round(float(raw_retro)))))
        except (ValueError, TypeError):
            retro_eff = 0
    else:
        # 旧パラメータ effect からの後方互換変換
        effect_val = params.get("effect", "normal (ノーマル)")
        e_key = EFFECT_MAP.get(str(effect_val), "normal")
        retro_eff = 2 if e_key == "2000s" else 0

    show_frame = params.get("show_frame", True)
    thickness = params.get("thickness", DEFAULT_THICKNESS)
    show_rec = params.get("show_rec", True)
    dot_style = params.get("dot_style", DEFAULT_DOT_STYLE)
    rec_label = params.get("rec_label", "REC")
    show_battery = params.get("show_battery", True)
    battery_bars = params.get("battery_bars", 4)
    show_cross = params.get("show_cross", False)
    show_timecode = params.get("show_timecode", False)
    timecode_mode = params.get("timecode_mode", "manual (手入力テキスト)")
    timecode_text = params.get("timecode_text", "")
    margin_ratio = params.get("margin_ratio", MARGIN_RATIO)
    arm_len_ratio = params.get("arm_len_ratio", ARM_LEN_RATIO)
    bg_box_opacity = params.get("bg_box_opacity", 0.10)
    custom_font_path = params.get("custom_font_path", "")
    custom_dot_path = params.get("custom_dot_path", "")
    override_shift_level = params.get("override_shift_level", -1)
    override_bloom = params.get("override_bloom", "preset (プリセットに従う)")
    override_pixel_scale = params.get("override_pixel_scale", 0.0)

    c_key = COLOR_MAP.get(str(color), "black")
    custom_color = params.get("custom_color", "")
    direct_color = _strip_path(custom_color)
    if direct_color:
        if parse_color_to_rgba(direct_color) is not None:
            c_key = direct_color
        else:
            logger.warning("[RecFrameOverlay] custom_color が無効です: %s (color プリセットを使用)", direct_color)
            direct_color = ""
    t_val = _parse_thickness(thickness)
    tc_mode = TIMECODE_MODE_MAP.get(str(timecode_mode), "manual")
    b_key = BLOOM_MAP.get(str(override_bloom), "preset")

    custom_fonts = discover_custom_fonts()
    active_font_key = str(font_key)
    direct_font = _strip_path(custom_font_path)
    if direct_font and is_valid_custom_font_path(direct_font):
        custom_fonts["__direct_custom__"] = direct_font
        active_font_key = "__direct_custom__"
    else:
        if direct_font:
            logger.warning("[RecFrameOverlay] custom_font_path が無効または見つかりません: %s (font_key を使用)", direct_font)
        if active_font_key not in custom_fonts and active_font_key not in FONT_CHOICES:
            active_font_key = DEFAULT_FONT

    resolved_dot_style = str(dot_style)
    direct_dot = _strip_path(custom_dot_path)
    if direct_dot:
        if is_valid_dot_asset_path(direct_dot):
            resolved_dot_style = direct_dot
        else:
            logger.warning("[RecFrameOverlay] custom_dot_path が無効または見つかりません: %s (dot_style を使用)", direct_dot)

    tc_kind, tc_val, base_tc_text = _resolve_timecode_info(tc_mode, str(timecode_text))
    base_dt = tc_val if isinstance(tc_val, datetime) else None

    try:
        shift_lvl = int(override_shift_level)
    except (ValueError, TypeError):
        shift_lvl = -1

    try:
        px_scale = float(override_pixel_scale)
    except (ValueError, TypeError):
        px_scale = 0.0

    use_custom_effect_override = (
        shift_lvl >= 0
        or b_key != "preset"
        or px_scale > 0.0
    )
    effect_params: dict[str, Any] | None = None
    if use_custom_effect_override:
        # 旧オーバーライド指定がある場合のみ個別パラメータ辞書を構築
        preset_dict = RETRO_EFFECT_LEVELS.get(retro_eff, RETRO_EFFECT_LEVELS[0])
        effect_params = {
            "shift_level": shift_lvl if shift_lvl >= 0 else preset_dict["shift"],
            "bloom_strength": b_key if b_key != "preset" else preset_dict["bloom"],
            "pixel_scale": px_scale if px_scale > 0.0 else preset_dict["pixel_scale"],
        }

    try:
        bat_bars = max(0, min(4, int(round(float(battery_bars))))) if not isinstance(battery_bars, bool) else 4
    except (ValueError, TypeError):
        bat_bars = 4

    try:
        m_ratio = max(0.0, min(0.45, float(margin_ratio))) if margin_ratio is not None else MARGIN_RATIO
    except (ValueError, TypeError):
        m_ratio = MARGIN_RATIO

    try:
        a_ratio = max(0.01, min(0.50, float(arm_len_ratio))) if arm_len_ratio is not None else ARM_LEN_RATIO
    except (ValueError, TypeError):
        a_ratio = ARM_LEN_RATIO

    try:
        box_opacity = max(0.0, min(1.0, float(bg_box_opacity))) if bg_box_opacity is not None else 0.10
    except (ValueError, TypeError):
        box_opacity = 0.10

    base_config = OverlayConfig(
        color=c_key,  # type: ignore[arg-type]
        custom_color=direct_color,
        font_key=active_font_key,
        thickness=t_val,  # type: ignore[arg-type]
        show_frame=bool(show_frame),
        show_battery=bool(show_battery),
        show_rec=bool(show_rec),
        show_cross=bool(show_cross),
        show_timecode=bool(show_timecode),
        timecode_text=base_tc_text,
        effect="2000s" if retro_eff == 2 else "normal",  # type: ignore[arg-type]
        retro_effect=0 if use_custom_effect_override else retro_eff,
        custom_fonts=custom_fonts,
        rec_label=str(rec_label if rec_label is not None else "REC"),
        show_red_dot=True,
        dot_style=resolved_dot_style,
        battery_bars=bat_bars,
        margin_ratio=m_ratio,
        arm_len_ratio=a_ratio,
        bg_box_opacity=box_opacity,
    )
    return OverlayBuildResult(
        base_config=base_config,
        effect_params=effect_params,
        c_key=c_key,
        base_tc_text=base_tc_text,
        base_dt=base_dt,
        tc_kind=tc_kind,
        tc_val=tc_val,
    )


def render_overlay_preview_pil(
    params: dict[str, Any],
    w: int = 1280,
    h: int = 720,
    bg_color: str = "black",
) -> Image.Image:
    """ウィジェットパラメータから指定解像度・背景色で合成したプレビュー用 PIL Image を生成する。"""
    bg_img = create_preview_background(w, h, bg_color).convert("RGBA")
    base_config, effect_params, c_key, _, _ = build_overlay_config_from_params(params)
    overlay_pil = create_rec_overlay_with_config(w, h, base_config)
    if effect_params is not None:
        color_hint = base_config.custom_color or c_key
        overlay_pil = apply_custom_ui_effects(overlay_pil, s=min(w, h), color=color_hint, **effect_params)
    return Image.alpha_composite(bg_img, overlay_pil).convert("RGB")


def _get_common_required_inputs() -> dict[str, Any]:
    """画像・動画ノード共通の必須ウィジェット定義。"""
    font_list = get_all_font_names()
    default_font = DEFAULT_FONT if DEFAULT_FONT in font_list else font_list[0]
    dot_styles = get_all_dot_styles()
    default_dot = DEFAULT_DOT_STYLE if DEFAULT_DOT_STYLE in dot_styles else dot_styles[0]
    return {
        # 1. 全体共通 (Theme / Global)
        "color": (list(COLOR_MAP.keys())[:6], {"default": "black (黒)"}),
        "font_key": (font_list, {"default": default_font}),
        "retro_effect": ("INT", {"default": DEFAULT_RETRO_EFFECT, "min": 0, "max": 6, "step": 1, "display": "slider"}),
        # 2. 四隅のL字枠 (Frame)
        "show_frame": ("BOOLEAN", {"default": True}),
        "thickness": ("INT", {"default": DEFAULT_THICKNESS, "min": 0, "max": 100, "step": 1}),
        # 3. RECマーク＆文字 (REC Indicator)
        "show_rec": ("BOOLEAN", {"default": True}),
        "dot_style": (dot_styles, {"default": default_dot}),
        "rec_label": ("STRING", {"default": "REC", "multiline": False}),
        # 4. 電池マーク (Battery)
        "show_battery": ("BOOLEAN", {"default": True}),
        "battery_bars": ("INT", {"default": 4, "min": 0, "max": 4, "step": 1}),
        # 5. 中央十字 (Crosshair)
        "show_cross": ("BOOLEAN", {"default": False}),
        # 6. 日時タイムコード (Timecode)
        "show_timecode": ("BOOLEAN", {"default": False}),
        "timecode_mode": (TIMECODE_CHOICES_IMAGE, {"default": "manual (手入力テキスト)"}),
        "timecode_text": ("STRING", {"default": "2026/11/01 PM 08:30", "multiline": False}),
    }


def _get_common_optional_inputs() -> dict[str, Any]:
    """画像・動画ノード共通のオプションウィジェット定義。"""
    return {
        "custom_color": ("STRING", {"default": "", "multiline": False}),
        "margin_ratio": ("FLOAT", {"default": MARGIN_RATIO, "min": 0.0, "max": 0.20, "step": 0.002}),
        "arm_len_ratio": ("FLOAT", {"default": ARM_LEN_RATIO, "min": 0.02, "max": 0.45, "step": 0.01}),
        "bg_box_opacity": ("FLOAT", {"default": 0.10, "min": 0.0, "max": 1.0, "step": 0.05}),
        "custom_font_path": ("STRING", {"default": "", "multiline": False}),
        "custom_dot_path": ("STRING", {"default": "", "multiline": False}),
        "empty_width": ("INT", {"default": 1280, "min": 64, "max": 8192, "step": 8}),
        "empty_height": ("INT", {"default": 720, "min": 64, "max": 8192, "step": 8}),
    }


def _render_and_composite(
    image: torch.Tensor | None,
    params: dict[str, Any],
    is_video: bool = False,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """画像または動画バッチに対するオーバーレイ描画および Tensor 合成の共通処理。"""
    if image is None:
        try:
            empty_w = max(64, min(8192, int(round(float(params.get("empty_width", 1280))))))
        except (ValueError, TypeError):
            empty_w = 1280
        try:
            empty_h = max(64, min(8192, int(round(float(params.get("empty_height", 720))))))
        except (ValueError, TypeError):
            empty_h = 720

        if is_video:
            try:
                batch_size = max(1, min(1024, int(round(float(params.get("empty_frames", 1))))))
            except (ValueError, TypeError):
                batch_size = 1
        else:
            batch_size = 1

        # 入力画像が未接続の場合は指定解像度・フレーム数の黒背景を生成して単体動作
        image = torch.zeros((batch_size, empty_h, empty_w, 3), dtype=torch.float32)

    build_res = build_overlay_config_from_params(params)
    base_config, effect_params, c_key, base_tc_text, base_dt = build_res
    tc_kind = getattr(build_res, "tc_kind", "static")
    tc_val = getattr(build_res, "tc_val", base_dt)

    show_rec = params.get("show_rec", True)
    try:
        raw_blink = params.get("blink_red_dot_interval", 0)
        blink_interval = max(0, int(round(float(raw_blink)))) if (show_rec and is_video and raw_blink is not None) else 0
    except (ValueError, TypeError):
        blink_interval = 0

    try:
        raw_fps = params.get("advance_timecode_fps", 0.0)
        advance_timecode_fps = max(0.0, float(raw_fps)) if (is_video and raw_fps is not None) else 0.0
    except (ValueError, TypeError):
        advance_timecode_fps = 0.0

    # 外部 fps 入力ピンが接続されている場合はウィジェット値より優先して上書き
    raw_input_fps = params.get("fps")
    if is_video and raw_input_fps is not None and not isinstance(raw_input_fps, bool):
        try:
            val_fps = float(raw_input_fps)
            if val_fps > 0.0:
                advance_timecode_fps = val_fps
        except (ValueError, TypeError):
            pass

    show_timecode = params.get("show_timecode", False)
    advance_tc = is_video and bool(show_timecode) and advance_timecode_fps > 0.0 and tc_kind != "static"

    batch_size, h, w, channels = image.shape
    device = image.device
    s = min(w, h)

    # (赤丸点灯, タイムコード文字列) ごとに描画済みオーバーレイをキャッシュする。
    # 毎フレーム変化するタイムコードでも VRAM/RAM が肥大化しないよう上限 (32) を設定。
    MAX_CACHE_SIZE = 32
    overlay_cache: dict[tuple[bool, str], torch.Tensor] = {}

    def get_overlay(dot_visible: bool, tc_text: str) -> torch.Tensor:
        key = (dot_visible, tc_text)
        cached = overlay_cache.get(key)
        if cached is not None:
            return cached
        frame_cfg = replace(base_config, red_dot_visible=dot_visible, timecode_text=tc_text)
        overlay_pil = create_rec_overlay_with_config(w, h, frame_cfg)
        if effect_params is not None:
            overlay_pil = apply_custom_ui_effects(overlay_pil, s=s, color=c_key, **effect_params)
        rgba_t, _ = pil_rgba_to_tensor_and_mask(overlay_pil)
        rgba_t = rgba_t.to(device=device, dtype=torch.float32)

        if len(overlay_cache) >= MAX_CACHE_SIZE:
            first_key = next(iter(overlay_cache))
            del overlay_cache[first_key]

        overlay_cache[key] = rgba_t
        return rgba_t

    if channels >= 3:
        base_rgb = image[..., :3]
    else:
        base_rgb = image[..., :1].expand(-1, -1, -1, 3)

    if base_rgb.dtype != torch.float32:
        base_rgb = base_rgb.to(dtype=torch.float32)

    # 静止画かつアニメーション無しの場合は 1 回だけ生成してブロードキャスト一括高速合成
    if not is_video or (blink_interval == 0 and not advance_tc):
        single_ov = get_overlay(True, base_tc_text)
        alpha = single_ov[..., 3:4]
        ov_rgb = single_ov[..., :3]
        out_images = torch.lerp(base_rgb, ov_rgb, alpha)
        out_overlays = single_ov.unsqueeze(0).expand(batch_size, -1, -1, -1).contiguous()
    else:
        out_images = torch.empty((batch_size, h, w, 3), dtype=torch.float32, device=device)
        out_overlays = torch.empty((batch_size, h, w, 4), dtype=torch.float32, device=device)
        for idx in range(batch_size):
            dot_visible = True
            if blink_interval > 0:
                dot_visible = ((idx // blink_interval) % 2) == 0

            frame_tc_text = base_tc_text
            if advance_tc:
                frame_tc_text = _compute_frame_timecode(
                    tc_kind, tc_val, base_tc_text, idx, advance_timecode_fps
                )

            ov = get_overlay(dot_visible, frame_tc_text)
            alpha = ov[..., 3:4]
            torch.lerp(base_rgb[idx], ov[..., :3], alpha, out=out_images[idx])
            out_overlays[idx] = ov

    out_images.clamp_(0.0, 1.0)
    out_masks = out_overlays[..., 3].clone()
    return out_images, out_overlays, out_masks


class RecFrameImageOverlayNode:
    """ファインダー風REC枠合成ノード（画像用・静止画特化）。"""

    CATEGORY = "image/overlay"
    FUNCTION = "apply_overlay"
    RETURN_TYPES = ("IMAGE", "IMAGE", "MASK")
    RETURN_NAMES = ("image", "overlay_rgba", "overlay_mask")

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        optional_inputs: dict[str, Any] = {"image": ("IMAGE",)}
        optional_inputs.update(_get_common_optional_inputs())
        return {
            "required": _get_common_required_inputs(),
            "optional": optional_inputs,
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs: Any) -> Any:
        mode = TIMECODE_MODE_MAP.get(kwargs.get("timecode_mode", ""), "manual")
        if kwargs.get("show_timecode") and mode in ("now", "now_sec"):
            return float("nan")
        return False

    def apply_overlay(
        self,
        image: torch.Tensor | None = None,
        **kwargs: Any,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        return _render_and_composite(image, kwargs, is_video=False)


class RecFrameVideoOverlayNode:
    """ファインダー風REC枠合成ノード（動画用・赤丸点滅＆タイムコード進行対応）。"""

    CATEGORY = "image/overlay"
    FUNCTION = "apply_overlay"
    RETURN_TYPES = ("IMAGE", "IMAGE", "MASK")
    RETURN_NAMES = ("images", "overlay_rgba", "overlay_mask")

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        font_list = get_all_font_names()
        pref_font = "Share Tech Mono(等幅)"
        default_font = pref_font if pref_font in font_list else (DEFAULT_FONT if DEFAULT_FONT in font_list else font_list[0])
        dot_styles = get_all_dot_styles()
        pref_dot = "flat_red"
        default_dot = pref_dot if pref_dot in dot_styles else (DEFAULT_DOT_STYLE if DEFAULT_DOT_STYLE in dot_styles else dot_styles[0])

        required_inputs: dict[str, Any] = {
            # 1. 全体共通 (Theme / Global)
            "color": (list(COLOR_MAP.keys())[:2], {"default": "white (白)"}),
            "font_key": (font_list, {"default": default_font}),
            "retro_effect": ("INT", {"default": DEFAULT_RETRO_EFFECT, "min": 0, "max": 6, "step": 1, "display": "slider"}),
            # 2. 四隅のL字枠 (Frame)
            "show_frame": ("BOOLEAN", {"default": True}),
            "thickness": ("INT", {"default": 40, "min": 0, "max": 100, "step": 1}),
            # 3. RECマーク＆文字 (REC Indicator)
            "show_rec": ("BOOLEAN", {"default": True}),
            "dot_style": (dot_styles, {"default": default_dot}),
            "rec_label": ("STRING", {"default": "REC", "multiline": False}),
            # 4. 電池マーク (Battery)
            "show_battery": ("BOOLEAN", {"default": True}),
            "battery_bars": ("INT", {"default": 3, "min": 0, "max": 4, "step": 1}),
            # 5. 中央十字 (Crosshair)
            "show_cross": ("BOOLEAN", {"default": False}),
            # 6. 日時タイムコード (Timecode)
            "show_timecode": ("BOOLEAN", {"default": True}),
            "timecode_mode": (TIMECODE_CHOICES_VIDEO, {"default": "now (現在時刻を自動取得)"}),
            "timecode_text": ("STRING", {"default": "2026/11/01 PM 08:30", "multiline": False}),
        }

        optional_inputs: dict[str, Any] = {
            "images": ("IMAGE",),
            "fps": ("FLOAT", {"forceInput": True}),
            "margin_ratio": ("FLOAT", {"default": 0.020, "min": 0.0, "max": 0.20, "step": 0.002}),
            "arm_len_ratio": ("FLOAT", {"default": 0.15, "min": 0.02, "max": 0.45, "step": 0.01}),
            "bg_box_opacity": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.05}),
            "custom_font_path": ("STRING", {"default": "", "multiline": False}),
            "custom_dot_path": ("STRING", {"default": "", "multiline": False}),
            "blink_red_dot_interval": ("INT", {"default": 24, "min": 0, "max": 120, "step": 1}),
            "advance_timecode_fps": ("FLOAT", {"default": 24.0, "min": 0.0, "max": 120.0, "step": 1.0}),
            "empty_width": ("INT", {"default": 1280, "min": 64, "max": 8192, "step": 8}),
            "empty_height": ("INT", {"default": 720, "min": 64, "max": 8192, "step": 8}),
            "empty_frames": ("INT", {"default": 24, "min": 1, "max": 1024, "step": 1}),
        }
        return {
            "required": required_inputs,
            "optional": optional_inputs,
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs: Any) -> Any:
        mode = TIMECODE_MODE_MAP.get(kwargs.get("timecode_mode", ""), "manual")
        if kwargs.get("show_timecode") and mode in ("now", "now_sec"):
            return float("nan")
        return False

    def apply_overlay(
        self,
        images: torch.Tensor | None = None,
        image: torch.Tensor | None = None,
        fps: float | int | None = None,
        **kwargs: Any,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        target_tensor = images if images is not None else image
        kwargs.setdefault("empty_frames", 24)
        if fps is not None:
            kwargs["fps"] = fps
        return _render_and_composite(target_tensor, kwargs, is_video=True)


class RecFrameOverlayNode:
    """ファインダー風REC枠合成ノード（後方互換・静止画および動画両用）。"""

    CATEGORY = "image/overlay"
    FUNCTION = "apply_overlay"
    RETURN_TYPES = ("IMAGE", "IMAGE", "MASK")
    RETURN_NAMES = ("image", "overlay_rgba", "overlay_mask")

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        optional_inputs: dict[str, Any] = {
            "image": ("IMAGE",),
            "fps": ("FLOAT", {"forceInput": True}),
            "margin_ratio": ("FLOAT", {"default": MARGIN_RATIO, "min": 0.0, "max": 0.20, "step": 0.002}),
            "arm_len_ratio": ("FLOAT", {"default": ARM_LEN_RATIO, "min": 0.02, "max": 0.45, "step": 0.01}),
            "bg_box_opacity": ("FLOAT", {"default": 0.10, "min": 0.0, "max": 1.0, "step": 0.05}),
            "custom_font_path": ("STRING", {"default": "", "multiline": False}),
            "custom_dot_path": ("STRING", {"default": "", "multiline": False}),
            "blink_red_dot_interval": ("INT", {"default": 0, "min": 0, "max": 120, "step": 1}),
            "advance_timecode_fps": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 120.0, "step": 1.0}),
            "empty_width": ("INT", {"default": 1280, "min": 64, "max": 8192, "step": 8}),
            "empty_height": ("INT", {"default": 720, "min": 64, "max": 8192, "step": 8}),
            "empty_frames": ("INT", {"default": 1, "min": 1, "max": 1024, "step": 1}),
        }
        return {
            "required": _get_common_required_inputs(),
            "optional": optional_inputs,
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs: Any) -> Any:
        mode = TIMECODE_MODE_MAP.get(kwargs.get("timecode_mode", ""), "manual")
        if kwargs.get("show_timecode") and mode in ("now", "now_sec"):
            return float("nan")
        return False

    def apply_overlay(
        self,
        image: torch.Tensor | None = None,
        fps: float | int | None = None,
        **kwargs: Any,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        if fps is not None:
            kwargs["fps"] = fps
        return _render_and_composite(image, kwargs, is_video=True)

    # 互換エイリアスメソッド
    apply_custom_overlay = apply_overlay


class RecFramePreviewNode:
    """ファインダー枠プレビューノード（黒/白/グレー/市松背景での確認用）。"""

    CATEGORY = "image/overlay"
    FUNCTION = "preview_overlay"
    OUTPUT_NODE = True
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("preview_image",)

    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "bg_color": (list(BG_COLOR_MAP.keys())[:4], {"default": "black (黒)"}),
            },
            "optional": {
                "overlay_rgba": ("IMAGE",),
                "preview_size": (list(PREVIEW_SIZE_MAP.keys())[:4], {"default": "1280x720 (16:9 HD)"}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    def preview_overlay(
        self,
        bg_color: str = "black (黒)",
        overlay_rgba: torch.Tensor | None = None,
        preview_size: str = "1280x720 (16:9 HD)",
        **kwargs: Any,
    ) -> dict[str, Any]:
        c_bg = BG_COLOR_MAP.get(bg_color, "black")
        if overlay_rgba is None:
            w, h = PREVIEW_SIZE_MAP.get(preview_size, (1280, 720))
            bg_pil = create_preview_background(w, h, c_bg)
            out_tensor = pil_rgb_to_tensor(bg_pil).unsqueeze(0)
            pil_list = [bg_pil]
        else:
            batch_size, h, w, channels = overlay_rgba.shape
            device = overlay_rgba.device
            bg_pil_template = create_preview_background(w, h, c_bg)
            bg_tensor = pil_rgb_to_tensor(bg_pil_template).to(device=device, dtype=torch.float32)

            if channels >= 4:
                rgb = overlay_rgba[..., :3].to(dtype=torch.float32)
                alpha = overlay_rgba[..., 3:4].to(dtype=torch.float32)
            elif channels >= 3:
                rgb = overlay_rgba[..., :3].to(dtype=torch.float32)
                alpha = torch.ones_like(rgb[..., :1])
            else:
                rgb = overlay_rgba[..., :1].expand(-1, -1, -1, 3).to(dtype=torch.float32)
                alpha = torch.ones_like(rgb[..., :1])

            out_tensor = torch.lerp(bg_tensor.unsqueeze(0), rgb, alpha).clamp_(0.0, 1.0)
            # 枠デザイン確認用プレビューは先頭1フレームのみ PIL 化（大量フレーム時のタイルグリッド化と負荷を防止）
            pil_list = [tensor_to_pil(out_tensor[0])] if batch_size > 0 else []

        results = []
        if folder_paths is not None:
            temp_dir = folder_paths.get_temp_directory()
            subfolder = ""
        else:
            import tempfile
            temp_dir = tempfile.gettempdir()
            subfolder = ""

        prefix = f"rec_preview_{random.randint(10000, 99999)}"
        for idx, pil_img in enumerate(pil_list):
            filename = f"{prefix}_{idx:02d}.png"
            full_path = os.path.join(temp_dir, filename)
            pil_img.save(full_path, compress_level=1)
            results.append({
                "filename": filename,
                "subfolder": subfolder,
                "type": "temp",
            })

        return {
            "ui": {"images": results},
            "result": (out_tensor.cpu(),),
        }


# リアルタイムプレビュー用 API ルートの登録
if prompt_server is not None:
    try:
        from aiohttp import web

        @prompt_server.routes.post("/rec_frame/preview")
        async def rec_frame_preview_api(request: web.Request) -> web.Response:
            """リアルタイムプレビュー用 API エンドポイント。"""
            try:
                data = await request.json()
            except Exception:
                data = {}

            if not isinstance(data, dict):
                data = {}

            try:
                bg_color = data.get("bg_color", "black (黒)")
                preview_size = data.get("preview_size", "1280x720 (16:9 HD)")
                preset_w, preset_h = PREVIEW_SIZE_MAP.get(preview_size, (1280, 720))

                # empty_width / empty_height が指定され、デフォルト以外に変更されているか、または preview_size がデフォルトのときは empty を優先
                raw_ew = data.get("empty_width")
                raw_eh = data.get("empty_height")
                if raw_ew is not None and raw_eh is not None:
                    try:
                        ew = max(64, min(8192, int(round(float(raw_ew)))))
                        eh = max(64, min(8192, int(round(float(raw_eh)))))
                        if (ew != 1280 or eh != 720) or preview_size.startswith("1280x720"):
                            w, h = ew, eh
                        else:
                            w, h = preset_w, preset_h
                    except (ValueError, TypeError):
                        w, h = preset_w, preset_h
                else:
                    w, h = preset_w, preset_h

                pil_img = render_overlay_preview_pil(data, w=w, h=h, bg_color=bg_color)
                buf = io.BytesIO()
                pil_img.save(buf, format="PNG", compress_level=1)
                return web.Response(body=buf.getvalue(), content_type="image/png")
            except Exception as e:
                logger.error("[rec-frame-ComfyUI] プレビュー API 描画エラー: %s", e)
                return web.Response(status=500, text=f"Preview generation failed: {e}")
    except Exception as e:
        logger.warning("[rec-frame-ComfyUI] プレビュー API の登録をスキップしました: %s", e)


# 後方互換用エイリアスクラス (一本化により RecFrameOverlayNode と同一)
RecFrameCustomOverlayNode = RecFrameOverlayNode


NODE_CLASS_MAPPINGS: dict[str, Any] = {
    "RecFrameImageOverlay": RecFrameImageOverlayNode,
    "RecFrameVideoOverlay": RecFrameVideoOverlayNode,
    "RecFrameOverlay": RecFrameOverlayNode,
    "RecFrameCustomOverlay": RecFrameCustomOverlayNode,
    "RecFramePreview": RecFramePreviewNode,
}

NODE_DISPLAY_NAME_MAPPINGS: dict[str, str] = {
    "RecFrameImageOverlay": "REC Frame (Image) [画像用]",
    "RecFrameVideoOverlay": "REC Frame (Video) [動画用]",
    "RecFramePreview": "Preview REC Overlay (枠プレビュー)",
    "RecFrameOverlay": "REC Frame Overlay (All-in-One / Legacy)",
    "RecFrameCustomOverlay": "REC Frame Overlay (Legacy Alias)",
}
