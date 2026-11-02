"""ComfyUI Desktop 向け公式ワークフロー JSON の生成スクリプト。

以下の3種類のワークフローを生成する:
1. rec_frame_basic_workflow.json: 静止画向け基本合成ワークフロー (プレビュー・透過PNG・マスク出力対応)
2. rec_frame_2000s_digicam_workflow.json: 2000s レトロデジカメ風プリセットワークフロー
3. rec_frame_video_batch_workflow.json: 動画・連続フレーム向け点滅＆タイムコード進行ワークフロー
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = REPO_ROOT / "workflows"
COMFY_USER_WORKFLOWS_DIR = Path(r"C:\Users\coffe\Documents\ComfyUI\user\default\workflows\rec-frame")


def make_rec_preview_node(
    node_id: int,
    pos: list[float],
    size: list[float],
    overlay_link_id: int,
    *,
    bg_color: str = "black (黒)",
    preview_size: str = "1280x720 (16:9 HD)",
    out_links: list[int] | None = None,
) -> dict[str, Any]:
    out_links = out_links or []
    return {
        "id": node_id,
        "type": "RecFramePreview",
        "pos": pos,
        "size": size,
        "flags": {},
        "order": 2,
        "mode": 0,
        "inputs": [
            {
                "name": "overlay_rgba",
                "type": "IMAGE",
                "link": overlay_link_id,
                "localized_name": "overlay_rgba",
            }
        ],
        "outputs": [
            {
                "name": "preview_image",
                "type": "IMAGE",
                "slot_index": 0,
                "links": out_links,
                "localized_name": "preview_image",
            }
        ],
        "properties": {
            "Node name for S&R": "RecFramePreview",
        },
        "widgets_values": [bg_color, preview_size],
        "widgets_values_named": {
            "bg_color": bg_color,
            "preview_size": preview_size,
        },
    }


def make_rec_image_node(
    node_id: int,
    pos: list[float],
    size: list[float],
    image_link_id: int,
    *,
    color: str = "white (白)",
    font_key: str = "Roboto Condensed Bold(細長)",
    retro_effect: int = 0,
    show_frame: bool = True,
    thickness: int = 40,
    show_rec: bool = True,
    dot_style: str = "flat_red",
    rec_label: str = "REC",
    show_battery: bool = True,
    battery_bars: int = 4,
    show_cross: bool = False,
    show_timecode: bool = True,
    timecode_mode: str = "now (現在時刻を自動取得)",
    timecode_text: str = "2026/11/01 PM 08:30",
    margin_ratio: float = 0.020,
    arm_len_ratio: float = 0.15,
    bg_box_opacity: float = 0.10,
    custom_font_path: str = "",
    custom_dot_path: str = "",
    out_links: dict[int, list[int]] | None = None,
) -> dict[str, Any]:
    out_links = out_links or {}

    widgets_values = [
        color,
        font_key,
        retro_effect,
        show_frame,
        thickness,
        show_rec,
        dot_style,
        rec_label,
        show_battery,
        battery_bars,
        show_cross,
        show_timecode,
        timecode_mode,
        timecode_text,
        margin_ratio,
        arm_len_ratio,
        bg_box_opacity,
        custom_font_path,
        custom_dot_path,
    ]

    widgets_values_named = {
        "color": color,
        "font_key": font_key,
        "retro_effect": retro_effect,
        "show_frame": show_frame,
        "thickness": thickness,
        "show_rec": show_rec,
        "dot_style": dot_style,
        "rec_label": rec_label,
        "show_battery": show_battery,
        "battery_bars": battery_bars,
        "show_cross": show_cross,
        "show_timecode": show_timecode,
        "timecode_mode": timecode_mode,
        "timecode_text": timecode_text,
        "margin_ratio": margin_ratio,
        "arm_len_ratio": arm_len_ratio,
        "bg_box_opacity": bg_box_opacity,
        "custom_font_path": custom_font_path,
        "custom_dot_path": custom_dot_path,
    }

    return {
        "id": node_id,
        "type": "RecFrameImageOverlay",
        "pos": pos,
        "size": size,
        "flags": {},
        "order": 1,
        "mode": 0,
        "inputs": [
            {
                "name": "image",
                "type": "IMAGE",
                "link": image_link_id,
                "localized_name": "image",
            }
        ],
        "outputs": [
            {
                "name": "image",
                "type": "IMAGE",
                "slot_index": 0,
                "links": out_links.get(0, []),
                "localized_name": "image",
            },
            {
                "name": "overlay_rgba",
                "type": "IMAGE",
                "slot_index": 1,
                "links": out_links.get(1, []),
                "localized_name": "overlay_rgba",
            },
            {
                "name": "overlay_mask",
                "type": "MASK",
                "slot_index": 2,
                "links": out_links.get(2, []),
                "localized_name": "overlay_mask",
            },
        ],
        "properties": {
            "Node name for S&R": "RecFrameImageOverlay",
        },
        "widgets_values": widgets_values,
        "widgets_values_named": widgets_values_named,
    }


def make_rec_video_node(
    node_id: int,
    pos: list[float],
    size: list[float],
    images_link_id: int,
    *,
    color: str = "white (白)",
    font_key: str = "Share Tech Mono(等幅)",
    retro_effect: int = 0,
    show_frame: bool = True,
    thickness: int = 40,
    show_rec: bool = True,
    dot_style: str = "flat_red",
    rec_label: str = "REC",
    show_battery: bool = True,
    battery_bars: int = 3,
    show_cross: bool = False,
    show_timecode: bool = True,
    timecode_mode: str = "now (現在時刻を自動取得)",
    timecode_text: str = "2026/11/01 PM 08:30",
    margin_ratio: float = 0.020,
    arm_len_ratio: float = 0.15,
    bg_box_opacity: float = 0.0,
    custom_font_path: str = "",
    custom_dot_path: str = "",
    blink_red_dot_interval: int = 24,
    advance_timecode_fps: float = 24.0,
    out_links: dict[int, list[int]] | None = None,
) -> dict[str, Any]:
    out_links = out_links or {}

    widgets_values = [
        color,
        font_key,
        retro_effect,
        show_frame,
        thickness,
        show_rec,
        dot_style,
        rec_label,
        show_battery,
        battery_bars,
        show_cross,
        show_timecode,
        timecode_mode,
        timecode_text,
        margin_ratio,
        arm_len_ratio,
        bg_box_opacity,
        custom_font_path,
        custom_dot_path,
        blink_red_dot_interval,
        advance_timecode_fps,
    ]

    widgets_values_named = {
        "color": color,
        "font_key": font_key,
        "retro_effect": retro_effect,
        "show_frame": show_frame,
        "thickness": thickness,
        "show_rec": show_rec,
        "dot_style": dot_style,
        "rec_label": rec_label,
        "show_battery": show_battery,
        "battery_bars": battery_bars,
        "show_cross": show_cross,
        "show_timecode": show_timecode,
        "timecode_mode": timecode_mode,
        "timecode_text": timecode_text,
        "margin_ratio": margin_ratio,
        "arm_len_ratio": arm_len_ratio,
        "bg_box_opacity": bg_box_opacity,
        "custom_font_path": custom_font_path,
        "custom_dot_path": custom_dot_path,
        "blink_red_dot_interval": blink_red_dot_interval,
        "advance_timecode_fps": advance_timecode_fps,
    }

    return {
        "id": node_id,
        "type": "RecFrameVideoOverlay",
        "pos": pos,
        "size": size,
        "flags": {},
        "order": 1,
        "mode": 0,
        "inputs": [
            {
                "name": "images",
                "type": "IMAGE",
                "link": images_link_id,
                "localized_name": "images",
            }
        ],
        "outputs": [
            {
                "name": "images",
                "type": "IMAGE",
                "slot_index": 0,
                "links": out_links.get(0, []),
                "localized_name": "images",
            },
            {
                "name": "overlay_rgba",
                "type": "IMAGE",
                "slot_index": 1,
                "links": out_links.get(1, []),
                "localized_name": "overlay_rgba",
            },
            {
                "name": "overlay_mask",
                "type": "MASK",
                "slot_index": 2,
                "links": out_links.get(2, []),
                "localized_name": "overlay_mask",
            },
        ],
        "properties": {
            "Node name for S&R": "RecFrameVideoOverlay",
        },
        "widgets_values": widgets_values,
        "widgets_values_named": widgets_values_named,
    }


def make_rec_frame_node(
    node_id: int,
    pos: list[float],
    size: list[float],
    image_link_id: int,
    *,
    color: str = "white (白)",
    font_key: str = "Roboto Condensed Bold(細長)",
    effect: str = "normal (ノーマル)",
    show_frame: bool = True,
    thickness: int = 40,
    show_rec: bool = True,
    dot_style: str = "flat_red",
    rec_label: str = "REC",
    show_battery: bool = True,
    battery_bars: int = 4,
    show_cross: bool = False,
    show_timecode: bool = True,
    timecode_mode: str = "now (現在時刻を自動取得)",
    timecode_text: str = "2026/11/01 PM 08:30",
    margin_ratio: float = 0.020,
    arm_len_ratio: float = 0.15,
    bg_box_opacity: float = 0.10,
    custom_font_path: str = "",
    custom_dot_path: str = "",
    blink_red_dot_interval: int = 0,
    advance_timecode_fps: float = 0.0,
    override_shift_level: int = -1,
    override_bloom: str = "preset (プリセットに従う)",
    override_pixel_scale: float = 0.0,
    out_links: dict[int, list[int]] | None = None,
) -> dict[str, Any]:
    out_links = out_links or {}

    widgets_values = [
        color,
        font_key,
        effect,
        show_frame,
        thickness,
        show_rec,
        dot_style,
        rec_label,
        show_battery,
        battery_bars,
        show_cross,
        show_timecode,
        timecode_mode,
        timecode_text,
        margin_ratio,
        arm_len_ratio,
        bg_box_opacity,
        custom_font_path,
        custom_dot_path,
        blink_red_dot_interval,
        advance_timecode_fps,
        override_shift_level,
        override_bloom,
        override_pixel_scale,
    ]

    widgets_values_named = {
        "color": color,
        "font_key": font_key,
        "effect": effect,
        "show_frame": show_frame,
        "thickness": thickness,
        "show_rec": show_rec,
        "dot_style": dot_style,
        "rec_label": rec_label,
        "show_battery": show_battery,
        "battery_bars": battery_bars,
        "show_cross": show_cross,
        "show_timecode": show_timecode,
        "timecode_mode": timecode_mode,
        "timecode_text": timecode_text,
        "margin_ratio": margin_ratio,
        "arm_len_ratio": arm_len_ratio,
        "bg_box_opacity": bg_box_opacity,
        "custom_font_path": custom_font_path,
        "custom_dot_path": custom_dot_path,
        "blink_red_dot_interval": blink_red_dot_interval,
        "advance_timecode_fps": advance_timecode_fps,
        "override_shift_level": override_shift_level,
        "override_bloom": override_bloom,
        "override_pixel_scale": override_pixel_scale,
    }

    return {
        "id": node_id,
        "type": "RecFrameOverlay",
        "pos": pos,
        "size": size,
        "flags": {},
        "order": 1,
        "mode": 0,
        "inputs": [
            {
                "name": "image",
                "type": "IMAGE",
                "link": image_link_id,
                "localized_name": "image",
            }
        ],
        "outputs": [
            {
                "name": "image",
                "type": "IMAGE",
                "slot_index": 0,
                "links": out_links.get(0, []),
                "localized_name": "image",
            },
            {
                "name": "overlay_rgba",
                "type": "IMAGE",
                "slot_index": 1,
                "links": out_links.get(1, []),
                "localized_name": "overlay_rgba",
            },
            {
                "name": "overlay_mask",
                "type": "MASK",
                "slot_index": 2,
                "links": out_links.get(2, []),
                "localized_name": "overlay_mask",
            },
        ],
        "properties": {
            "Node name for S&R": "RecFrameOverlay",
        },
        "widgets_values": widgets_values,
        "widgets_values_named": widgets_values_named,
    }


def build_basic_workflow() -> dict[str, Any]:
    """静止画向け基本ワークフロー。"""
    nodes = [
        # Note
        {
            "id": 10,
            "type": "Note",
            "pos": [-380, 50],
            "size": [340, 500],
            "flags": {},
            "order": 0,
            "mode": 0,
            "inputs": [],
            "outputs": [],
            "properties": {"Node name for S&R": "Note"},
            "widgets_values": [
                "【REC Frame Overlay 基本ワークフロー】\n\n"
                "カメラのファインダー風UIオーバーレイを画像に合成する公式ワークフローです。\n\n"
                "■ 主な設定項目:\n"
                "- color: 白 (white) または 黒 (black)\n"
                "- font_key: 同梱の6フォントから選択\n"
                "  ・Roboto Condensed (標準)\n"
                "  ・Bebas Neue (縦長シネマ調)\n"
                "  ・DSEG7 Classic (7セグLED)\n"
                "  ・Share Tech Mono (等幅)\n"
                "  ・VT323 (レトロドット)\n"
                "  ・Zen Kaku Gothic (日本語)\n"
                "- thickness: 枠の太さ (0〜100、40が初期値)\n"
                "- bg_box_opacity: 文字・マーク背後の半透明座布団の濃さ (0.0=なし、0.10=おすすめ初期値)\n"
                "- timecode_mode: 'now' で現在日時、'manual' で自由設定\n"
                "- retro_effect: レトロエフェクト強度 (0=OFF・クリーン 〜 6=極限Break)\n\n"
                "■ リアルタイム枠プレビュー:\n"
                "- RecFrameImageOverlay の直下に 'Preview REC Overlay' が接続されています。\n"
                "- 枠の太さ・フォント・表示ON/OFF・背景色などを変更すると、Queue Prompt を押さずにその場でダイナミックにプレビュー画像が変化します。\n\n"
                "■ 出力スロットについて:\n"
                "- 通常は一番上の 'image' 出力（完成画像）を使用します。\n"
                "- 必要に応じて 'overlay_rgba'（背景透明の枠単体PNG）や 'overlay_mask'（枠マスク）を取り出して外部ソフトや後段ノードで活用することも可能です。"
            ],
            "color": "#233",
            "bgcolor": "#355",
        },
        # LoadImage
        {
            "id": 1,
            "type": "LoadImage",
            "pos": [20, 50],
            "size": [380, 500],
            "flags": {},
            "order": 0,
            "mode": 0,
            "inputs": [],
            "outputs": [
                {"name": "IMAGE", "type": "IMAGE", "slot_index": 0, "links": [1], "localized_name": "IMAGE"},
                {"name": "MASK", "type": "MASK", "links": None, "localized_name": "MASK"},
            ],
            "properties": {"Node name for S&R": "LoadImage"},
            "widgets_values": ["example.png", "image"],
        },
        # RecFrameImageOverlay
        make_rec_image_node(
            node_id=2,
            pos=[450, 50],
            size=[400, 640],
            image_link_id=1,
            color="white (白)",
            font_key="Roboto Condensed Bold(細長)",
            retro_effect=0,
            show_frame=True,
            thickness=40,
            show_rec=True,
            dot_style="flat_red",
            rec_label="REC",
            show_battery=True,
            battery_bars=4,
            show_cross=False,
            show_timecode=True,
            timecode_mode="now (現在時刻を自動取得)",
            timecode_text="2026/11/01 PM 08:30",
            margin_ratio=0.020,
            arm_len_ratio=0.15,
            bg_box_opacity=0.10,
            out_links={0: [2, 3], 1: [4]},
        ),
        # Preview REC Overlay (直下のリアルタイムプレビュー)
        make_rec_preview_node(
            node_id=5,
            pos=[450, 770],
            size=[400, 360],
            overlay_link_id=4,
            bg_color="black (黒)",
            preview_size="1280x720 (16:9 HD)",
        ),
        # Preview & Save (Main Image)
        {
            "id": 3,
            "type": "PreviewImage",
            "pos": [910, 50],
            "size": [480, 480],
            "flags": {},
            "order": 2,
            "mode": 0,
            "inputs": [
                {"name": "images", "type": "IMAGE", "link": 2, "localized_name": "images"}
            ],
            "outputs": [],
            "properties": {"Node name for S&R": "PreviewImage"},
            "widgets_values": [],
        },
        {
            "id": 4,
            "type": "SaveImage",
            "pos": [910, 570],
            "size": [480, 260],
            "flags": {},
            "order": 3,
            "mode": 0,
            "inputs": [
                {"name": "images", "type": "IMAGE", "link": 3, "localized_name": "images"}
            ],
            "outputs": [],
            "properties": {"Node name for S&R": "SaveImage"},
            "widgets_values": ["rec_frame"],
            "widgets_values_named": {"filename_prefix": "rec_frame"},
        },
    ]

    links = [
        [1, 1, 0, 2, 0, "IMAGE"],
        [2, 2, 0, 3, 0, "IMAGE"],
        [3, 2, 0, 4, 0, "IMAGE"],
        [4, 2, 1, 5, 0, "IMAGE"],
    ]

    groups = [
        {
            "id": 1,
            "title": "1. ガイド (Guide & Controls)",
            "bounding": [-400, 0, 380, 600],
            "color": "#3f51b5",
            "font_size": 22,
        },
        {
            "id": 2,
            "title": "2. 入力画像 (Input Image)",
            "bounding": [0, 0, 420, 600],
            "color": "#3f789e",
            "font_size": 22,
        },
        {
            "id": 3,
            "title": "3. ファインダー枠合成 & リアルタイムプレビュー (REC Frame Overlay & Preview)",
            "bounding": [430, 0, 440, 1180],
            "color": "#2e7d32",
            "font_size": 22,
        },
        {
            "id": 4,
            "title": "4. 完成画像出力 (Final Composite Preview & Save)",
            "bounding": [890, 0, 510, 860],
            "color": "#c2185b",
            "font_size": 22,
        },
    ]

    return {
        "id": "rec-frame-basic-workflow",
        "revision": 0,
        "last_node_id": 10,
        "last_link_id": 4,
        "nodes": nodes,
        "links": links,
        "groups": groups,
        "config": {},
        "extra": {"ds": {"scale": 0.85, "offset": [450, 60]}},
        "version": 0.4,
    }


def build_2000s_digicam_workflow() -> dict[str, Any]:
    """2000s レトロデジカメ風プリセットワークフロー。"""
    nodes = [
        # Note
        {
            "id": 10,
            "type": "Note",
            "pos": [-380, 50],
            "size": [340, 540],
            "flags": {},
            "order": 0,
            "mode": 0,
            "inputs": [],
            "outputs": [],
            "properties": {"Node name for S&R": "Note"},
            "widgets_values": [
                "【2000s レトロデジカメ風ワークフロー】\n\n"
                "2000年代初頭のコンパクトデジタルカメラや液晶ファインダー特有の質感を再現する黄金比プリセットです。\n\n"
                "■ 最適化されたレトロ演出プリセット:\n"
                "- retro_effect: 2 (2000sデジカメ風標準)\n"
                "- font_key: 'Share Tech Mono(等幅)' (または 'VT323(レトロドット)')\n"
                "- dot_style: 'flat_red' / rec_label: 'STBY'\n"
                "- battery_bars: 3 (残量3目盛りリアル演出)\n"
                "- timecode_mode: 'manual' (例: 2004/08/15 PM 02:45)\n"
                "- bg_box_opacity: 0.10 (半透明座布団で視認性向上)\n\n"
                "■ リアルタイム枠プレビュー:\n"
                "- 直下の 'Preview REC Overlay' で、パラメータ調整結果を Queue を押さずにダイナミック確認できます。"
            ],
            "color": "#233",
            "bgcolor": "#355",
        },
        # LoadImage
        {
            "id": 1,
            "type": "LoadImage",
            "pos": [20, 50],
            "size": [380, 500],
            "flags": {},
            "order": 0,
            "mode": 0,
            "inputs": [],
            "outputs": [
                {"name": "IMAGE", "type": "IMAGE", "slot_index": 0, "links": [1], "localized_name": "IMAGE"},
                {"name": "MASK", "type": "MASK", "links": None, "localized_name": "MASK"},
            ],
            "properties": {"Node name for S&R": "LoadImage"},
            "widgets_values": ["example.png", "image"],
        },
        # RecFrameImageOverlay (Retro 2000s preset)
        make_rec_image_node(
            node_id=2,
            pos=[450, 50],
            size=[400, 680],
            image_link_id=1,
            color="white (白)",
            font_key="Share Tech Mono(等幅)",
            retro_effect=2,
            show_frame=True,
            thickness=45,
            show_rec=True,
            dot_style="flat_red",
            rec_label="STBY",
            show_battery=True,
            battery_bars=3,
            show_cross=False,
            show_timecode=True,
            timecode_mode="manual (手入力テキスト)",
            timecode_text="2004/08/15 PM 02:45",
            margin_ratio=0.02,
            arm_len_ratio=0.15,
            bg_box_opacity=0.10,
            out_links={0: [2, 3], 1: [4]},
        ),
        # Preview REC Overlay (直下のリアルタイムプレビュー)
        make_rec_preview_node(
            node_id=5,
            pos=[450, 770],
            size=[400, 360],
            overlay_link_id=4,
            bg_color="black (黒)",
            preview_size="1280x720 (16:9 HD)",
        ),
        # Preview & Save
        {
            "id": 3,
            "type": "PreviewImage",
            "pos": [910, 50],
            "size": [520, 520],
            "flags": {},
            "order": 2,
            "mode": 0,
            "inputs": [
                {"name": "images", "type": "IMAGE", "link": 2, "localized_name": "images"}
            ],
            "outputs": [],
            "properties": {"Node name for S&R": "PreviewImage"},
            "widgets_values": [],
        },
        {
            "id": 4,
            "type": "SaveImage",
            "pos": [910, 610],
            "size": [520, 260],
            "flags": {},
            "order": 3,
            "mode": 0,
            "inputs": [
                {"name": "images", "type": "IMAGE", "link": 3, "localized_name": "images"}
            ],
            "outputs": [],
            "properties": {"Node name for S&R": "SaveImage"},
            "widgets_values": ["rec_2000s_digicam"],
            "widgets_values_named": {"filename_prefix": "rec_2000s_digicam"},
        },
    ]

    links = [
        [1, 1, 0, 2, 0, "IMAGE"],
        [2, 2, 0, 3, 0, "IMAGE"],
        [3, 2, 0, 4, 0, "IMAGE"],
        [4, 2, 1, 5, 0, "IMAGE"],
    ]

    groups = [
        {
            "id": 1,
            "title": "1. ガイド (Guide & Retro Tips)",
            "bounding": [-400, 0, 380, 640],
            "color": "#3f51b5",
            "font_size": 22,
        },
        {
            "id": 2,
            "title": "2. 入力画像 (Input Image)",
            "bounding": [0, 0, 420, 640],
            "color": "#3f789e",
            "font_size": 22,
        },
        {
            "id": 3,
            "title": "3. 2000s デジカメ合成 & リアルタイムプレビュー (2000s Digicam Overlay & Preview)",
            "bounding": [430, 0, 440, 1180],
            "color": "#e65100",
            "font_size": 22,
        },
        {
            "id": 4,
            "title": "4. 完成画像出力 (Final Result)",
            "bounding": [890, 0, 560, 900],
            "color": "#c2185b",
            "font_size": 22,
        },
    ]

    return {
        "id": "rec-frame-2000s-digicam-workflow",
        "revision": 0,
        "last_node_id": 10,
        "last_link_id": 4,
        "nodes": nodes,
        "links": links,
        "groups": groups,
        "config": {},
        "extra": {"ds": {"scale": 0.85, "offset": [450, 60]}},
        "version": 0.4,
    }


def build_video_batch_workflow() -> dict[str, Any]:
    """動画ファイル向け点滅＆タイムコード進行ワークフロー (Load Video -> REC Overlay -> Save Video)。"""
    nodes = [
        # Note
        {
            "id": 10,
            "type": "Note",
            "pos": [-380, 50],
            "size": [340, 600],
            "flags": {},
            "order": 0,
            "mode": 0,
            "inputs": [],
            "outputs": [],
            "properties": {"Node name for S&R": "Note"},
            "widgets_values": [
                "【動画・バッチフレーム用 REC枠合成ワークフロー】\n\n"
                "動画ファイル (.mp4 / .webm 等) を読み込み、ファインダー枠・赤丸REC点滅・\n"
                "リアルタイム進行タイムコードをオーバーレイ合成して動画出力します。\n\n"
                "■ 動画の指定・読み込み:\n"
                "- '2. 入力動画' グループの 'Load Video' で動画ファイルを指定（ドラッグ＆ドロップまたは選択）。\n"
                "- 'Get Video Components' がフレーム画像・音声・FPSを自動抽出して後続へ渡します。\n\n"
                "■ 設定済みの動画用パラメータ:\n"
                "- blink_red_dot_interval: 24\n"
                "  ・赤丸RECマークの点滅間隔 (フレーム数)\n"
                "  ・24fps設定時、24フレーム (1.0秒) ごとに点灯と消灯を繰り返します。\n"
                "  ・消灯時もレイアウト崩れや文字ズレは起きません。\n"
                "- advance_timecode_fps: 24.0\n"
                "  ・フレーム進行に伴うタイムコード秒数の自動加算 FPS\n"
                "  ・24フレーム経過するごとにタイムコードが1秒ずつリアルに進みます。\n"
                "- timecode_mode: 'now (現在時刻を自動取得)'\n"
                "  ・撮影開始日時を現在時刻から自動取得し、秒単位でカウントアップします。\n\n"
                "■ リアルタイム枠プレビュー:\n"
                "- RecFrameVideoOverlay 直下の 'Preview REC Overlay' で、Queue を押さずに枠の太さやフォントをその場でダイナミック確認できます。\n\n"
                "■ 動画の保存 & 出力:\n"
                "- 'Create Video' と 'Save Video' により、元の音声とフレームレートを維持したまま、完成動画 (MP4等) として自動保存されます。"
            ],
            "color": "#233",
            "bgcolor": "#355",
        },
        # LoadVideo (Video file input)
        {
            "id": 1,
            "type": "LoadVideo",
            "pos": [20, 50],
            "size": [380, 280],
            "flags": {},
            "order": 0,
            "mode": 0,
            "inputs": [],
            "outputs": [
                {"name": "VIDEO", "type": "VIDEO", "slot_index": 0, "links": [1], "localized_name": "VIDEO"}
            ],
            "properties": {"Node name for S&R": "LoadVideo"},
            "widgets_values": ["example.mp4"],
            "widgets_values_named": {"file": "example.mp4"},
        },
        # GetVideoComponents (Extract frames, audio, fps)
        {
            "id": 11,
            "type": "GetVideoComponents",
            "pos": [20, 380],
            "size": [380, 240],
            "flags": {},
            "order": 1,
            "mode": 0,
            "inputs": [
                {"name": "video", "type": "VIDEO", "link": 1, "localized_name": "video"}
            ],
            "outputs": [
                {"name": "images", "type": "IMAGE", "slot_index": 0, "links": [2], "localized_name": "images"},
                {"name": "audio", "type": "AUDIO", "slot_index": 1, "links": [6], "localized_name": "audio"},
                {"name": "fps", "type": "FLOAT", "slot_index": 2, "links": [5], "localized_name": "fps"},
                {"name": "bit_depth", "type": "COMBO", "slot_index": 3, "links": None, "localized_name": "bit_depth"},
                {"name": "color_space", "type": "COMBO", "slot_index": 4, "links": None, "localized_name": "color_space"},
            ],
            "properties": {"Node name for S&R": "GetVideoComponents"},
            "widgets_values": [],
            "widgets_values_named": {},
        },
        # RecFrameVideoOverlay (Video Batch Animation)
        make_rec_video_node(
            node_id=2,
            pos=[450, 50],
            size=[400, 680],
            images_link_id=2,
            color="white (白)",
            font_key="Share Tech Mono(等幅)",
            retro_effect=0,
            show_frame=True,
            thickness=40,
            show_rec=True,
            dot_style="flat_red",
            rec_label="REC",
            show_battery=True,
            battery_bars=3,
            show_cross=False,
            show_timecode=True,
            timecode_mode="now (現在時刻を自動取得)",
            timecode_text="2026/11/01 PM 08:30",
            margin_ratio=0.02,
            arm_len_ratio=0.15,
            bg_box_opacity=0.0,
            blink_red_dot_interval=24,
            advance_timecode_fps=24.0,
            out_links={0: [3], 1: [4]},
        ),
        # Preview REC Overlay (直下のリアルタイムプレビュー)
        make_rec_preview_node(
            node_id=5,
            pos=[450, 770],
            size=[400, 360],
            overlay_link_id=4,
            bg_color="black (黒)",
            preview_size="1280x720 (16:9 HD)",
        ),
        # CreateVideo
        {
            "id": 20,
            "type": "CreateVideo",
            "pos": [910, 50],
            "size": [280, 160],
            "flags": {},
            "order": 3,
            "mode": 0,
            "inputs": [
                {"name": "images", "type": "IMAGE", "link": 3, "localized_name": "images"},
                {"name": "fps", "type": "FLOAT", "link": 5, "localized_name": "fps"},
                {"name": "audio", "type": "AUDIO", "link": 6, "localized_name": "audio", "shape": 7},
                {"name": "bit_depth", "type": "COMBO", "link": None, "localized_name": "bit_depth", "shape": 7, "widget": {"name": "bit_depth"}},
                {"name": "color_space", "type": "COMBO", "link": None, "localized_name": "color_space", "shape": 7, "widget": {"name": "color_space"}},
                {"name": "codec", "type": "COMBO", "link": None, "localized_name": "codec", "shape": 7, "widget": {"name": "codec"}},
            ],
            "outputs": [
                {"name": "VIDEO", "type": "VIDEO", "slot_index": 0, "links": [7], "localized_name": "VIDEO"}
            ],
            "properties": {"Node name for S&R": "CreateVideo"},
            "widgets_values": [24, 8, "sRGB", "none"],
            "widgets_values_named": {"fps": 24, "bit_depth": 8, "color_space": "sRGB", "codec": "none"},
        },
        # SaveVideo
        {
            "id": 21,
            "type": "SaveVideo",
            "pos": [1230, 50],
            "size": [520, 600],
            "flags": {},
            "order": 4,
            "mode": 0,
            "inputs": [
                {"name": "video", "type": "VIDEO", "link": 7, "localized_name": "video"},
                {"name": "filename_prefix", "type": "STRING", "link": None, "localized_name": "filename_prefix", "widget": {"name": "filename_prefix"}},
                {"name": "format", "type": "COMFY_DYNAMICCOMBO_V3", "link": None, "localized_name": "format", "widget": {"name": "format"}},
                {"name": "codec", "type": "COMFY_DYNAMICCOMBO_V3", "link": None, "localized_name": "codec", "widget": {"name": "format.codec"}},
            ],
            "outputs": [
                {"name": "video", "type": "VIDEO", "slot_index": 0, "links": None, "localized_name": "video"}
            ],
            "properties": {"Node name for S&R": "SaveVideo"},
            "widgets_values": ["video/rec_overlay", "auto", "auto", "auto"],
            "widgets_values_named": {"filename_prefix": "video/rec_overlay", "format": "auto", "format.codec": "auto", "codec": "auto"},
        },
    ]

    links = [
        [1, 1, 0, 11, 0, "VIDEO"],
        [2, 11, 0, 2, 0, "IMAGE"],
        [3, 2, 0, 20, 0, "IMAGE"],
        [4, 2, 1, 5, 0, "IMAGE"],
        [5, 11, 2, 20, 1, "FLOAT"],
        [6, 11, 1, 20, 2, "AUDIO"],
        [7, 20, 0, 21, 0, "VIDEO"],
    ]

    groups = [
        {
            "id": 1,
            "title": "1. ガイド (Video Animation Guide)",
            "bounding": [-400, 0, 380, 680],
            "color": "#3f51b5",
            "font_size": 22,
        },
        {
            "id": 2,
            "title": "2. 入力動画 (Input Video & Split)",
            "bounding": [0, 0, 420, 680],
            "color": "#3f789e",
            "font_size": 22,
        },
        {
            "id": 3,
            "title": "3. 動画用REC枠合成 & リアルタイムプレビュー (Video Animation Overlay & Preview)",
            "bounding": [430, 0, 440, 1180],
            "color": "#00838f",
            "font_size": 22,
        },
        {
            "id": 4,
            "title": "4. 完成動画出力 & 保存 (Final Video Combine & Save)",
            "bounding": [890, 0, 880, 720],
            "color": "#c2185b",
            "font_size": 22,
        },
    ]

    return {
        "id": "rec-frame-video-batch-workflow",
        "revision": 0,
        "last_node_id": 21,
        "last_link_id": 7,
        "nodes": nodes,
        "links": links,
        "groups": groups,
        "config": {},
        "extra": {"ds": {"scale": 0.85, "offset": [450, 60]}},
        "version": 0.4,
    }


def main() -> None:
    WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
    COMFY_USER_WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)

    workflows = {
        "rec_frame_basic_workflow.json": build_basic_workflow(),
        "rec_frame_2000s_digicam_workflow.json": build_2000s_digicam_workflow(),
        "rec_frame_video_batch_workflow.json": build_video_batch_workflow(),
    }

    for filename, data in workflows.items():
        repo_dest = WORKFLOWS_DIR / filename
        comfy_dest = COMFY_USER_WORKFLOWS_DIR / filename

        content = json.dumps(data, ensure_ascii=False, indent=2)
        repo_dest.write_text(content, encoding="utf-8")
        comfy_dest.write_text(content, encoding="utf-8")
        print(f"Generated: {repo_dest}")
        print(f"Installed to ComfyUI: {comfy_dest}")


if __name__ == "__main__":
    main()
