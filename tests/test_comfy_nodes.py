"""コア描画層 (`rec_overlay.py`) + ComfyUIノード層 (`nodes.py`) の自動テスト (unittest & pytest 両対応)。"""
from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
TESTS_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

import numpy as np
import torch
from PIL import Image

from conftest import BLACK, RED, TRANSPARENT, VERIFIED_SIZES, WHITE, count_color
from nodes import (
    NODE_CLASS_MAPPINGS,
    RecFrameCustomOverlayNode,
    RecFrameImageOverlayNode,
    RecFrameOverlayNode,
    RecFramePreviewNode,
    RecFrameVideoOverlayNode,
    _resolve_base_datetime,
    build_overlay_config_from_params,
    create_preview_background,
    render_overlay_preview_pil,
)
from rec_config import (
    BUNDLED_FONT_CHOICES,
    FONT_CHOICES,
    LEGACY_FONT_CHOICES,
    OverlayConfig,
    discover_dot_assets,
    get_local_fonts_dir,
    resolve_bundled_font_path,
)
from rec_overlay import (
    MARGIN_RATIO,
    create_rec_overlay,
    create_rec_overlay_with_config,
)


class TestRecFrameComfyNodes(unittest.TestCase):
    def test_output_same_size(self) -> None:
        for w, h in VERIFIED_SIZES:
            for color in ("black", "white"):
                with self.subTest(w=w, h=h, color=color):
                    ov = create_rec_overlay(w, h, color=color)
                    self.assertEqual(ov.mode, "RGBA")
                    self.assertEqual(ov.size, (w, h))

    def test_corners_equidistant_640x360(self) -> None:
        """SPEC §3.1: 640x360で四隅とも端距離7/7。右・下端は-1補正で一致。"""
        w, h = 640, 360
        s = min(w, h)
        margin = int(s * MARGIN_RATIO)
        self.assertEqual(margin, 7)
        ov = create_rec_overlay(w, h, color="black")
        px = ov.load()
        self.assertEqual(px[margin, margin], BLACK)
        self.assertEqual(px[w - 1 - margin, margin], BLACK)
        self.assertEqual(px[margin, h - 1 - margin], BLACK)
        self.assertEqual(px[w - 1 - margin, h - 1 - margin], BLACK)
        self.assertEqual(px[margin - 1, margin], TRANSPARENT)
        self.assertEqual(px[margin, margin - 1], TRANSPARENT)

    def test_all_fonts_render(self) -> None:
        """新同梱フォント6種が fonts/ に実在し描画できること、および旧互換キーも正常描画できることを検証。"""
        self.assertEqual(len(BUNDLED_FONT_CHOICES), 6)
        # 同梱フォントファイルの実在確認
        fonts_dir = get_local_fonts_dir()
        for key, filename in BUNDLED_FONT_CHOICES.items():
            font_path = fonts_dir / filename
            self.assertTrue(font_path.is_file(), f"Missing bundled font file: {font_path}")
            resolved = resolve_bundled_font_path(key)
            self.assertIsNotNone(resolved, f"Could not resolve {key}")
            self.assertEqual(resolved, font_path)

        # 全キー（新同梱6種 + 旧互換10種）でのレンダリング検証
        for key in FONT_CHOICES:
            with self.subTest(font_key=key):
                ov = create_rec_overlay(640, 360, font_key=key)
                self.assertEqual(ov.size, (640, 360))
                self.assertIsNotNone(ov.getbbox(), key)

    def test_japanese_font_rendering(self) -> None:
        """日本語フォント (Zen Kaku Gothic) で日本語のREC文字列・タイムコードが正常描画できることを検証。"""
        cfg = OverlayConfig(
            color="white",
            font_key="Zen Kaku Gothic(日本語)",
            rec_label="録画中",
            show_timecode=True,
            timecode_text="2026年11月01日 午後 08:30",
        )
        ov = create_rec_overlay_with_config(640, 360, cfg)
        self.assertEqual(ov.size, (640, 360))
        self.assertIsNotNone(ov.getbbox())

    def test_red_dot_always_red(self) -> None:
        for color in ("black", "white"):
            ov = create_rec_overlay(640, 360, color=color)
            self.assertGreater(count_color(ov, RED), 0, color)

    def test_effects_presets(self) -> None:
        clean = create_rec_overlay(640, 360, color="white", effect="normal")
        clean_off = create_rec_overlay(640, 360, color="white", effect="off")
        cam2000 = create_rec_overlay(640, 360, color="white", effect="2000s")
        # normal と off は完全に同一 (クリーン)
        self.assertEqual(clean.tobytes(), clean_off.tobytes())
        # 2000s はピクセル化・色収差により異なる
        self.assertNotEqual(clean.tobytes(), cam2000.tobytes())

        # 新 retro_effect (0..6) の段階テスト
        cfg_0 = OverlayConfig(color="white", retro_effect=0)
        cfg_2 = OverlayConfig(color="white", retro_effect=2)
        cfg_6 = OverlayConfig(color="white", retro_effect=6)
        ov_0 = create_rec_overlay_with_config(640, 360, cfg_0)
        ov_2 = create_rec_overlay_with_config(640, 360, cfg_2)
        ov_6 = create_rec_overlay_with_config(640, 360, cfg_6)

        # retro_effect=0 は clean と同一
        self.assertEqual(clean.tobytes(), ov_0.tobytes())
        # retro_effect=2 は 2000s と同一
        self.assertEqual(cam2000.tobytes(), ov_2.tobytes())
        # retro_effect=6 (極限Break) は他と異なる
        self.assertNotEqual(ov_2.tobytes(), ov_6.tobytes())

        # 全レベル 0..6 で正常に描画できること
        for lvl in range(7):
            cfg_lvl = OverlayConfig(color="white", retro_effect=lvl)
            ov_lvl = create_rec_overlay_with_config(640, 360, cfg_lvl)
            self.assertEqual(ov_lvl.size, (640, 360))
            self.assertIsNotNone(ov_lvl.getbbox())

    def test_custom_extensions_in_config(self) -> None:
        """ComfyUI用に追加した拡張フィールド (battery_bars, rec_label, show_red_dot) の動作確認。"""
        cfg_no_dot = OverlayConfig(color="white", show_red_dot=False)
        ov_no_dot = create_rec_overlay_with_config(640, 360, cfg_no_dot)
        self.assertEqual(count_color(ov_no_dot, RED), 0)

        cfg_zero_bat = OverlayConfig(color="white", battery_bars=0)
        cfg_full_bat = OverlayConfig(color="white", battery_bars=4)
        ov_zero = create_rec_overlay_with_config(640, 360, cfg_zero_bat)
        ov_full = create_rec_overlay_with_config(640, 360, cfg_full_bat)
        self.assertGreater(count_color(ov_full, WHITE), count_color(ov_zero, WHITE))

    def test_standard_comfy_node_execution(self) -> None:
        """標準ノード `RecFrameOverlayNode` の Tensor 入出力・形状・値域テスト。"""
        self.assertIn("RecFrameOverlay", NODE_CLASS_MAPPINGS)
        node = RecFrameOverlayNode()
        input_types = node.INPUT_TYPES()
        self.assertTrue("image" in input_types.get("required", {}) or "image" in input_types.get("optional", {}))

        # [B=2, H=360, W=640, C=3] のダミーテンソル
        dummy = torch.full((2, 360, 640, 3), 0.5, dtype=torch.float32)
        out_img, out_ov, out_mask = node.apply_overlay(
            image=dummy,
            color="white (白)",
            thickness="medium (中)",
            effect="normal (ノーマル)",
            show_frame=True,
            show_battery=True,
            show_rec=True,
            show_cross=True,
            show_timecode=True,
            timecode_mode="manual (手入力テキスト)",
            timecode_text="2026/11/01 PM 05:00",
        )
        self.assertEqual(tuple(out_img.shape), (2, 360, 640, 3))
        self.assertEqual(tuple(out_ov.shape), (2, 360, 640, 4))
        self.assertEqual(tuple(out_mask.shape), (2, 360, 640))
        self.assertEqual(out_img.dtype, torch.float32)
        self.assertGreater(float(out_mask.max()), 0.9)
        self.assertFalse(torch.allclose(dummy, out_img))

    def test_image_overlay_node_simplicity(self) -> None:
        """静止画用ノード `RecFrameImageOverlayNode` のシンプルUI・高速描画テスト。"""
        self.assertIn("RecFrameImageOverlay", NODE_CLASS_MAPPINGS)
        node = RecFrameImageOverlayNode()
        inputs = node.INPUT_TYPES()
        # 静止画用なので動画パラメータが存在しないことを検証
        self.assertNotIn("blink_red_dot_interval", inputs["optional"])
        self.assertNotIn("advance_timecode_fps", inputs["optional"])
        self.assertIn("image", inputs["optional"])

        # 静止画 1 枚の実行テスト
        dummy = torch.zeros((1, 360, 640, 3), dtype=torch.float32)
        out_img, out_ov, out_mask = node.apply_overlay(
            image=dummy,
            color="white (白)",
            thickness=50,
        )
        self.assertEqual(tuple(out_img.shape), (1, 360, 640, 3))
        self.assertEqual(tuple(out_ov.shape), (1, 360, 640, 4))
        self.assertEqual(tuple(out_mask.shape), (1, 360, 640))

        # バッチ入力時でも全フレーム同一のオーバーレイが高速に適用されること
        dummy_batch = torch.zeros((4, 360, 640, 3), dtype=torch.float32)
        out_b_img, out_b_ov, _ = node.apply_overlay(
            image=dummy_batch,
            color="black (黒)",
        )
        self.assertEqual(tuple(out_b_img.shape), (4, 360, 640, 3))
        # 全フレームのオーバーレイが完全に一致していること
        for i in range(1, 4):
            self.assertTrue(torch.equal(out_b_ov[0], out_b_ov[i]))

    def test_video_overlay_node_features(self) -> None:
        """動画用ノード `RecFrameVideoOverlayNode` の点滅・タイムコード進行テスト。"""
        self.assertIn("RecFrameVideoOverlay", NODE_CLASS_MAPPINGS)
        node = RecFrameVideoOverlayNode()
        inputs = node.INPUT_TYPES()
        # 動画用ノードなので動画専用パラメータが存在すること
        self.assertIn("blink_red_dot_interval", inputs["optional"])
        self.assertIn("advance_timecode_fps", inputs["optional"])
        self.assertIn("images", inputs["optional"])

        # custom_dot_path の直下に blink_red_dot_interval と advance_timecode_fps が配置されていること
        opt_keys = list(inputs["optional"].keys())
        dot_idx = opt_keys.index("custom_dot_path")
        self.assertEqual(opt_keys[dot_idx + 1], "blink_red_dot_interval")
        self.assertEqual(opt_keys[dot_idx + 2], "advance_timecode_fps")

        # 4フレームバッチで点滅（blink_red_dot_interval=2: 0,1点灯, 2,3消灯）
        dummy_video = torch.zeros((4, 360, 640, 3), dtype=torch.float32)
        out_img, out_ov, out_mask = node.apply_overlay(
            images=dummy_video,
            color="white (白)",
            blink_red_dot_interval=2,
            advance_timecode_fps=0.0,
        )
        self.assertEqual(tuple(out_img.shape), (4, 360, 640, 3))
        self.assertTrue(torch.allclose(out_ov[0], out_ov[1]))
        self.assertFalse(torch.allclose(out_ov[0], out_ov[2]))
        self.assertTrue(torch.allclose(out_ov[2], out_ov[3]))

    def test_custom_comfy_node_blink_and_override(self) -> None:
        """拡張ノード `RecFrameCustomOverlayNode` の動画赤丸点滅・カスタムパラメータテスト。"""
        self.assertIn("RecFrameCustomOverlay", NODE_CLASS_MAPPINGS)
        node = RecFrameCustomOverlayNode()

        # 4フレームのバッチで blink_red_dot_interval=2 をテスト (frame 0,1: 点灯 / frame 2,3: 消灯)
        dummy = torch.zeros((4, 360, 640, 3), dtype=torch.float32)
        out_img, out_ov, out_mask = node.apply_custom_overlay(
            image=dummy,
            color="white (白)",
            thickness="large (大)",
            battery_bars=2,
            rec_label="LIVE",
            blink_red_dot_interval=2,
            margin_ratio=0.04,
            arm_len_ratio=0.20,
        )
        self.assertEqual(tuple(out_img.shape), (4, 360, 640, 3))
        self.assertTrue(torch.allclose(out_ov[0], out_ov[1]))
        self.assertFalse(torch.allclose(out_ov[0], out_ov[2]))
        self.assertTrue(torch.allclose(out_ov[2], out_ov[3]))

    def test_thickness_slider_and_scaling(self) -> None:
        """thickness=0..100 の無段階スライダー値による描画ピクセル数とノード実行のテスト。"""
        node = RecFrameOverlayNode()
        input_types = node.INPUT_TYPES()
        self.assertEqual(input_types["required"]["thickness"][0], "INT")
        self.assertEqual(input_types["required"]["thickness"][1]["default"], 40)

        # 枠のみ描画して 0, 50, 100 で白ピクセル数が単調増加することを確認
        cfg_0 = OverlayConfig(color="white", thickness=0, show_battery=False, show_rec=False)
        cfg_50 = OverlayConfig(color="white", thickness=50, show_battery=False, show_rec=False)
        cfg_100 = OverlayConfig(color="white", thickness=100, show_battery=False, show_rec=False)

        ov_0 = create_rec_overlay_with_config(640, 360, cfg_0)
        ov_50 = create_rec_overlay_with_config(640, 360, cfg_50)
        ov_100 = create_rec_overlay_with_config(640, 360, cfg_100)

        cnt_0 = count_color(ov_0, WHITE)
        cnt_50 = count_color(ov_50, WHITE)
        cnt_100 = count_color(ov_100, WHITE)

        self.assertGreater(cnt_0, 0)
        self.assertGreater(cnt_50, cnt_0)
        self.assertGreater(cnt_100, cnt_50)

        # ノード apply_overlay に INT 値を直接渡して正常終了することを確認
        dummy = torch.zeros((1, 360, 640, 3), dtype=torch.float32)
        out_img, out_ov, out_mask = node.apply_overlay(
            image=dummy,
            thickness=80,
            color="white (白)",
        )
        self.assertEqual(tuple(out_img.shape), (1, 360, 640, 3))

    def test_dot_style_assets(self) -> None:
        """dot_style (classic, glow_*, flat_*) による描画切り替えのテスト。"""
        node = RecFrameOverlayNode()
        input_types = node.INPUT_TYPES()
        self.assertIn("dot_style", input_types["required"])
        dot_styles = input_types["required"]["dot_style"][0]
        self.assertIn("classic (幾何学・真円)", dot_styles)
        self.assertIn("glow_red", dot_styles)
        self.assertIn("flat_green", dot_styles)
        # flat -> glow -> classic の並び順を検証
        idx_flat = dot_styles.index("flat_red")
        idx_glow = dot_styles.index("glow_red")
        idx_classic = dot_styles.index("classic (幾何学・真円)")
        self.assertLess(idx_flat, idx_glow)
        self.assertLess(idx_glow, idx_classic)
        self.assertEqual(dot_styles[0], "flat_red")

        # 1. classic での描画
        cfg_classic = OverlayConfig(color="black", dot_style="classic (幾何学・真円)")
        ov_classic = create_rec_overlay_with_config(640, 360, cfg_classic)
        self.assertGreater(count_color(ov_classic, RED), 0)

        # 2. glow_red での描画
        cfg_glow = OverlayConfig(color="black", dot_style="glow_red")
        ov_glow = create_rec_overlay_with_config(640, 360, cfg_glow)
        self.assertIsNotNone(ov_glow.getbbox())

        # 3. flat_green での描画 (緑ピクセルが描かれること)
        cfg_green = OverlayConfig(color="black", dot_style="flat_green")
        ov_green = create_rec_overlay_with_config(640, 360, cfg_green)
        px = ov_green.load()
        # 画像全体で G > R かつ G > 150 のピクセルが存在することを確認
        has_green = False
        for y in range(360):
            for x in range(640):
                r, g, b, a = px[x, y]
                if a > 100 and g > 150 and g > r * 1.5:
                    has_green = True
                    break
            if has_green:
                break
        self.assertTrue(has_green, "Green dot pixels should be present for flat_green")

        # 4. ノード apply_overlay で dot_style を渡して実行
        dummy = torch.zeros((1, 360, 640, 3), dtype=torch.float32)
        out_img, out_ov, out_mask = node.apply_overlay(
            image=dummy,
            dot_style="glow_cyan",
        )
        self.assertEqual(tuple(out_img.shape), (1, 360, 640, 3))

    def test_bg_box_opacity(self) -> None:
        """半透明座布団 (bg_box_opacity) の描画・反転色・ノード実行テスト。"""
        node = RecFrameOverlayNode()
        input_types = node.INPUT_TYPES()
        self.assertIn("bg_box_opacity", input_types["optional"])
        bg_param = input_types["optional"]["bg_box_opacity"]
        self.assertEqual(bg_param[1]["default"], 0.10)
        self.assertEqual(bg_param[1]["min"], 0.0)
        self.assertEqual(bg_param[1]["max"], 1.0)

        # 1. bg_box_opacity=0.0 (デフォルト) と 0.5 の差異確認
        cfg_no_box = OverlayConfig(color="white", bg_box_opacity=0.0, show_timecode=True, timecode_text="2026/11/01")
        cfg_with_box = OverlayConfig(color="white", bg_box_opacity=0.5, show_timecode=True, timecode_text="2026/11/01")
        ov_no_box = create_rec_overlay_with_config(640, 360, cfg_no_box)
        ov_with_box = create_rec_overlay_with_config(640, 360, cfg_with_box)

        # 座布団ありの方が不透明ピクセル数が多くなる
        px_no = ov_no_box.load()
        px_with = ov_with_box.load()
        count_alpha_no = sum(1 for y in range(360) for x in range(640) if px_no[x, y][3] > 0)
        count_alpha_with = sum(1 for y in range(360) for x in range(640) if px_with[x, y][3] > 0)
        self.assertGreater(count_alpha_with, count_alpha_no)

        # 2. 白枠時の座布団が黒半透明 (RGB=0,0,0, A=128程度) であること
        has_black_box = False
        for y in range(360):
            for x in range(640):
                r, g, b, a = px_with[x, y]
                if r == 0 and g == 0 and b == 0 and 100 <= a <= 150:
                    has_black_box = True
                    break
            if has_black_box:
                break
        self.assertTrue(has_black_box, "White frame should have translucent black background box")

        # 3. 黒枠時の座布団が白半透明 (RGB=255,255,255, A=128程度) であること
        cfg_black_box = OverlayConfig(color="black", bg_box_opacity=0.5, show_timecode=True, timecode_text="2026/11/01")
        ov_black_box = create_rec_overlay_with_config(640, 360, cfg_black_box)
        px_black_box = ov_black_box.load()
        has_white_box = False
        for y in range(360):
            for x in range(640):
                r, g, b, a = px_black_box[x, y]
                if r == 255 and g == 255 and b == 255 and 100 <= a <= 150:
                    has_white_box = True
                    break
            if has_white_box:
                break
        self.assertTrue(has_white_box, "Black frame should have translucent white background box")

        # 4. ノード apply_overlay で bg_box_opacity を渡して正常に Tensor 出力されること
        dummy = torch.zeros((1, 360, 640, 3), dtype=torch.float32)
        out_img, out_ov, out_mask = node.apply_overlay(
            image=dummy,
            color="white (白)",
            bg_box_opacity=0.5,
            show_timecode=True,
            timecode_text="2026/11/01 PM 08:30",
        )
        self.assertEqual(tuple(out_img.shape), (1, 360, 640, 3))
        self.assertEqual(tuple(out_ov.shape), (1, 360, 640, 4))
        self.assertEqual(tuple(out_mask.shape), (1, 360, 640))


class TestRefactorRegressions(unittest.TestCase):
    """リファクタリング時に修正した不具合の回帰テスト。"""

    def setUp(self) -> None:
        self.node = RecFrameOverlayNode()
        self.img = torch.zeros((1, 360, 640, 3), dtype=torch.float32)

    def test_custom_dot_path_is_applied(self) -> None:
        """custom_dot_path に画像パスを指定するとその素材で描画される (以前は常に赤い幾何円になっていた)。"""
        green_path = discover_dot_assets()["flat_green"]
        _, ov, _ = self.node.apply_overlay(image=self.img, custom_dot_path=f'"{green_path}"')
        o = ov[0]
        green = ((o[..., 1] > 0.6) & (o[..., 0] < 0.4) & (o[..., 3] > 0.4)).sum().item()
        red = ((o[..., 0] > 0.9) & (o[..., 1] < 0.1) & (o[..., 3] > 0.9)).sum().item()
        self.assertGreater(green, 0)
        self.assertEqual(red, 0)

    def test_missing_custom_dot_path_falls_back_to_dot_style(self) -> None:
        _, ov_missing, _ = self.node.apply_overlay(
            image=self.img, dot_style="flat_green", custom_dot_path="C:/no/such/dot.png")
        _, ov_style, _ = self.node.apply_overlay(image=self.img, dot_style="flat_green")
        self.assertTrue(torch.equal(ov_missing, ov_style))

    def test_effect_overrides_run(self) -> None:
        """エフェクト個別オーバーライドが例外なく適用される (以前は関数内相対importで失敗し得た)。"""
        _, ov_plain, _ = self.node.apply_overlay(image=self.img, color="white (白)")
        _, ov_bloom, _ = self.node.apply_overlay(
            image=self.img, color="white (白)", override_bloom="strong (強)",
            override_shift_level=2, override_pixel_scale=0.5)
        self.assertFalse(torch.equal(ov_plain, ov_bloom))

    def test_manual_date_end_of_month_preserved(self) -> None:
        """29〜31日の手入力日付がタイムコード進行時に28日へ丸められない。"""
        dt = _resolve_base_datetime("manual", "2026/10/31 PM 11:59")
        self.assertEqual(dt, datetime(2026, 10, 31, 23, 59))
        dt_feb = _resolve_base_datetime("manual", "2026/02/31 AM 12:05")
        self.assertEqual(dt_feb, datetime(2026, 2, 28, 0, 5))
        self.assertIsNone(_resolve_base_datetime("manual", "自由テキスト"))

    def test_advance_timecode_rolls_over(self) -> None:
        """1fps で 61 フレーム目 (60秒後) は 1 分進んだタイムコード (日付も繰り上がる) になる。"""
        batch = torch.zeros((61, 120, 200, 3), dtype=torch.float32)
        _, ov, _ = self.node.apply_overlay(
            image=batch, show_timecode=True, timecode_text="2026/10/31 PM 11:59",
            advance_timecode_fps=1.0)
        self.assertTrue(torch.equal(ov[0], ov[59]))
        self.assertFalse(torch.equal(ov[0], ov[60]))

    def test_free_text_timecode_not_replaced_when_advancing(self) -> None:
        """日時として解釈できない文字列は進行対象外で、入力どおり固定表示される。"""
        batch = torch.zeros((2, 360, 640, 3), dtype=torch.float32)
        kwargs = dict(show_timecode=True, timecode_text="TAKE 01", color="white (白)")
        _, ov_adv, _ = self.node.apply_overlay(image=batch, advance_timecode_fps=1.0, **kwargs)
        _, ov_fix, _ = self.node.apply_overlay(image=batch, **kwargs)
        self.assertTrue(torch.equal(ov_adv, ov_fix))

    def test_blink_keeps_text_layout(self) -> None:
        """赤丸点滅の消灯フレームでも REC 文字・座布団の位置/サイズが変わらない。"""
        batch = torch.zeros((2, 1080, 1920, 3), dtype=torch.float32)
        _, ov, _ = self.node.apply_overlay(
            image=batch, color="white (白)", blink_red_dot_interval=1,
            dot_style="classic (幾何学・真円)", bg_box_opacity=0.5, show_frame=False,
            show_battery=False)
        on, off = ov[0], ov[1]
        white_on = (on[..., :3].min(dim=-1).values > 0.99) & (on[..., 3] > 0.99)
        white_off = (off[..., :3].min(dim=-1).values > 0.99) & (off[..., 3] > 0.99)
        self.assertTrue(torch.equal(white_on, white_off), "REC 文字の位置が点滅で動いている")
        self.assertTrue(torch.equal(on[..., 3] > 0, off[..., 3] > 0), "座布団の範囲が点滅で変化している")
        red_on = ((on[..., 0] > 0.99) & (on[..., 1] < 0.01)).sum().item()
        red_off = ((off[..., 0] > 0.99) & (off[..., 1] < 0.01)).sum().item()
        self.assertGreater(red_on, 0)
        self.assertEqual(red_off, 0)

    def test_thickness_numeric_string(self) -> None:
        out_img, _, _ = self.node.apply_overlay(image=self.img, thickness="70")
        self.assertEqual(tuple(out_img.shape), (1, 360, 640, 3))

    def test_tensor_composite_matches_pil(self) -> None:
        """Tensor 上の合成が PIL alpha_composite と ±1/255 以内で一致する。"""
        torch.manual_seed(0)
        img = torch.rand((1, 360, 640, 3), dtype=torch.float32)
        out_img, out_ov, _ = self.node.apply_overlay(
            image=img, color="white (白)", effect="2000s (2000sデジカメ風)", bg_box_opacity=0.4,
            show_timecode=True)
        base = Image.fromarray((img[0].numpy() * 255).round().astype(np.uint8), "RGB").convert("RGBA")
        ov = Image.fromarray((out_ov[0].numpy() * 255).round().astype(np.uint8), "RGBA")
        ref = np.asarray(Image.alpha_composite(base, ov).convert("RGB"), dtype=np.float32) / 255.0
        diff = np.abs(out_img[0].numpy() - ref).max()
        self.assertLessEqual(diff, 1.5 / 255.0)

    def test_grayscale_and_rgba_inputs(self) -> None:
        for c in (1, 4):
            with self.subTest(channels=c):
                out_img, _, out_mask = self.node.apply_overlay(image=torch.zeros((2, 64, 96, c)))
                self.assertEqual(tuple(out_img.shape), (2, 64, 96, 3))
                self.assertEqual(tuple(out_mask.shape), (2, 64, 96))

    def test_tiny_images_do_not_crash(self) -> None:
        # (200,120)/(160,100): 電池残量バーの内高不足で ValueError になっていたサイズ帯 (短辺 94〜133px)
        for w, h in ((1, 1), (8, 8), (17, 9), (200, 120), (160, 100), (133, 133)):
            with self.subTest(w=w, h=h):
                out_img, _, _ = self.node.apply_overlay(
                    image=torch.zeros((1, h, w, 3)), show_timecode=True, show_cross=True,
                    bg_box_opacity=0.5, dot_style="glow_red")
                self.assertEqual(tuple(out_img.shape), (1, h, w, 3))


    def test_overlay_optional_image_standalone(self) -> None:
        """image=None でも 1280x720 の黒背景を生成して単体動作すること。"""
        out_img, out_ov, out_mask = self.node.apply_overlay(image=None)
        self.assertEqual(tuple(out_img.shape), (1, 720, 1280, 3))
        self.assertEqual(tuple(out_ov.shape), (1, 720, 1280, 4))
        self.assertEqual(tuple(out_mask.shape), (1, 720, 1280))

    def test_custom_resolution_standalone(self) -> None:
        """empty_width / empty_height / empty_frames によるカスタム解像度・フレーム数単体生成の検証。"""
        # 1. 静止画ノード (RecFrameImageOverlayNode): 9:16 (1080x1920) 縦長ショート枠
        img_node = RecFrameImageOverlayNode()
        out_img, out_ov, out_mask = img_node.apply_overlay(
            image=None, empty_width=1080, empty_height=1920)
        self.assertEqual(tuple(out_img.shape), (1, 1920, 1080, 3))
        self.assertEqual(tuple(out_ov.shape), (1, 1920, 1080, 4))
        self.assertEqual(tuple(out_mask.shape), (1, 1920, 1080))

        # 2. 動画ノード (RecFrameVideoOverlayNode): 1:1 (1024x1024) 16フレーム正方形バッチ
        vid_node = RecFrameVideoOverlayNode()
        out_imgs, out_vov, out_vmask = vid_node.apply_overlay(
            images=None, empty_width=1024, empty_height=1024, empty_frames=16)
        self.assertEqual(tuple(out_imgs.shape), (16, 1024, 1024, 3))
        self.assertEqual(tuple(out_vov.shape), (16, 1024, 1024, 4))
        self.assertEqual(tuple(out_vmask.shape), (16, 1024, 1024))

        # 3. 入力画像が存在する場合は empty_width / empty_height に惑わされず入力サイズ優先
        dummy = torch.zeros((1, 360, 640, 3), dtype=torch.float32)
        out_orig, _, _ = img_node.apply_overlay(
            image=dummy, empty_width=1080, empty_height=1920)
        self.assertEqual(tuple(out_orig.shape), (1, 360, 640, 3))

    def test_preview_node_standalone_and_composite(self) -> None:
        """RecFramePreviewNode の単体実行および overlay_rgba 合成の検証。"""
        prev_node = RecFramePreviewNode()

        # 1. overlay_rgba 未接続時
        res_empty = prev_node.preview_overlay(bg_color="black (黒)", overlay_rgba=None, preview_size="1280x720 (16:9 HD)")
        self.assertIn("ui", res_empty)
        self.assertIn("images", res_empty["ui"])
        self.assertEqual(len(res_empty["ui"]["images"]), 1)
        self.assertIn("result", res_empty)
        self.assertEqual(tuple(res_empty["result"][0].shape), (1, 720, 1280, 3))

        # 2. overlay_rgba 接続時 (各背景色)
        _, ov_rgba, _ = self.node.apply_overlay(image=self.img, color="white (白)")
        for bg in ("black (黒)", "white (白)", "gray (グレー)", "checker (透過市松)"):
            with self.subTest(bg=bg):
                res = prev_node.preview_overlay(bg_color=bg, overlay_rgba=ov_rgba)
                self.assertIn("ui", res)
                self.assertEqual(tuple(res["result"][0].shape), (1, 360, 640, 3))

    def test_render_overlay_preview_pil_dynamic_tracking(self) -> None:
        """リアルタイムプレビュー描画でパラメータ変更（show_frame ON/OFF等）が画像に反映されること。"""
        # show_frame=True
        img_on = render_overlay_preview_pil(
            {"show_frame": True, "color": "white (白)", "thickness": 50},
            w=640, h=360, bg_color="black"
        )
        # show_frame=False
        img_off = render_overlay_preview_pil(
            {"show_frame": False, "color": "white (白)", "thickness": 50},
            w=640, h=360, bg_color="black"
        )
        self.assertEqual(img_on.size, (640, 360))
        self.assertEqual(img_off.size, (640, 360))
        # 枠の有無でピクセルが異なることを検証
        arr_on = np.asarray(img_on)
        arr_off = np.asarray(img_off)
        self.assertFalse(np.array_equal(arr_on, arr_off), "show_frame の変更がプレビュー画像に反映されていない")

        # 背景色の反映検証
        img_white_bg = render_overlay_preview_pil({}, w=100, h=100, bg_color="white")
        arr_white = np.asarray(img_white_bg)
        # 四隅近辺が白 (255, 255, 255) であること
        self.assertTrue((arr_white[0, 0] > 250).all())

    def test_preview_pil_matches_alpha_composite_with_translucent_box(self) -> None:
        """render_overlay_preview_pil が paste(mask) による二重乗算を起こさず alpha_composite と一致すること。"""
        params = {
            "color": "white (白)",
            "bg_box_opacity": 0.5,
            "show_frame": False,
            "show_battery": True,
            "show_rec": False,
        }
        pil_prev = render_overlay_preview_pil(params, w=200, h=120, bg_color="white")
        prev_node = RecFramePreviewNode()
        img_node = RecFrameImageOverlayNode()
        _, ov_rgba, _ = img_node.apply_overlay(image=torch.ones((1, 120, 200, 3)), **params)
        res = prev_node.preview_overlay(bg_color="white (白)", overlay_rgba=ov_rgba)
        tensor_out = res["result"][0][0].numpy() * 255.0
        pil_out = np.asarray(pil_prev, dtype=np.float32)
        self.assertLessEqual(np.abs(tensor_out - pil_out).max(), 1.5)

    def test_param_coercion_resilience(self) -> None:
        """API や JSON 経由で float / 文字列数値 / None が渡されても例外を出さず安全に正規化されること。"""
        cfg, _, _, _, _ = build_overlay_config_from_params({
            "battery_bars": 2.8,
            "margin_ratio": "0.03",
            "arm_len_ratio": None,
            "bg_box_opacity": "-0.5",
            "thickness": "45.2",
        })
        self.assertEqual(cfg.battery_bars, 3)
        self.assertAlmostEqual(cfg.margin_ratio or 0.0, 0.03)
        self.assertAlmostEqual(cfg.arm_len_ratio or 0.0, 0.15)
        self.assertEqual(cfg.bg_box_opacity, 0.0)
        self.assertEqual(cfg.thickness, 45)

    def test_security_path_traversal_and_invalid_extensions(self) -> None:
        """非許可拡張子や存在しないファイル、ヌルバイト等の不正パスが安全にフォールバックされること。"""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"not a font or image")
            text_file_path = f.name

        try:
            # 1. custom_font_path に .txt (非許可拡張子) を指定
            cfg_font, _, _, _, _ = build_overlay_config_from_params({
                "custom_font_path": text_file_path,
                "font_key": "Roboto Condensed Bold(細長)",
            })
            self.assertEqual(cfg_font.font_key, "Roboto Condensed Bold(細長)")

            # 2. custom_dot_path に .txt (非許可拡張子) を指定
            cfg_dot, _, _, _, _ = build_overlay_config_from_params({
                "custom_dot_path": text_file_path,
                "dot_style": "flat_red",
            })
            self.assertEqual(cfg_dot.dot_style, "flat_red")

            # 3. ヌルバイトを含む不正パス文字列
            cfg_null, _, _, _, _ = build_overlay_config_from_params({
                "custom_font_path": "invalid\x00path.ttf",
                "custom_dot_path": "invalid\x00path.png",
            })
            self.assertNotEqual(cfg_null.font_key, "__direct_custom__")
            self.assertNotEqual(cfg_null.dot_style, "invalid\x00path.png")

            # 4. レンダリングが一切クラッシュしないこと
            pil_img = render_overlay_preview_pil({
                "custom_font_path": text_file_path,
                "custom_dot_path": text_file_path,
            }, w=320, h=180)
            self.assertEqual(pil_img.size, (320, 180))
        finally:
            Path(text_file_path).unlink(missing_ok=True)

    def test_corrupted_custom_asset_graceful_degradation(self) -> None:
        """破損した画像やフォントが指定されても例外で中断せず安全に縮退描画されること。"""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"corrupted png bytes")
            bad_png = f.name

        with tempfile.NamedTemporaryFile(suffix=".ttf", delete=False) as f:
            f.write(b"corrupted ttf bytes")
            bad_ttf = f.name

        try:
            node = RecFrameImageOverlayNode()
            # 破損ファイルを指定してオーバーレイ実行
            out_img, out_ov, out_mask = node.apply_overlay(
                image=torch.zeros((1, 120, 160, 3), dtype=torch.float32),
                custom_font_path=bad_ttf,
                custom_dot_path=bad_png,
            )
            self.assertEqual(out_img.shape, (1, 120, 160, 3))
            self.assertEqual(out_ov.shape, (1, 120, 160, 4))
            self.assertEqual(out_mask.shape, (1, 120, 160))
        finally:
            Path(bad_png).unlink(missing_ok=True)
            Path(bad_ttf).unlink(missing_ok=True)

    def test_color_presets_rendering(self) -> None:
        """6種すべてのプリセットカラー (white, black, green, cyan, red, yellow) で枠が正しいRGBで描画されること。"""
        from rec_config import COLOR_PRESETS
        w, h = 640, 360
        s = min(w, h)
        margin = int(s * MARGIN_RATIO)

        for color_key, expected_rgba in COLOR_PRESETS.items():
            cfg = OverlayConfig(color=color_key, show_battery=False, show_rec=False, show_timecode=False, show_cross=False)
            ov = create_rec_overlay_with_config(w, h, cfg)
            # 左上L字枠の角ピクセル (margin, margin) を検査
            pixel = ov.getpixel((margin, margin))
            self.assertEqual(pixel, expected_rgba, f"プリセット {color_key} の枠描画色が一致しません")

    def test_custom_hex_color(self) -> None:
        """custom_color による HEX 指定 (#00FF50, #FF007F, #0F6, 00DCFF) が正しく反映されること。"""
        w, h = 640, 360
        s = min(w, h)
        margin = int(s * MARGIN_RATIO)

        hex_tests = [
            ("#00FF50", (0, 255, 80, 255)),
            ("#FF007F", (255, 0, 127, 255)),
            ("#0F6", (0, 255, 102, 255)),
            ("00DCFF", (0, 220, 255, 255)),
        ]
        for hex_str, expected_rgba in hex_tests:
            cfg = OverlayConfig(custom_color=hex_str, show_battery=False, show_rec=False)
            ov = create_rec_overlay_with_config(w, h, cfg)
            pixel = ov.getpixel((margin, margin))
            self.assertEqual(pixel, expected_rgba, f"custom_color {hex_str} の描画色が一致しません")

    def test_bg_box_luminance_auto_switch(self) -> None:
        """色の輝度に応じて座布団ボックス (bg_box) の色が白/黒半透明に自動反転すること。"""
        from rec_overlay import _bg_box_color

        # 明色・蛍光色 (白、緑、シアン、黄色) -> 黒半透明 (0, 0, 0, alpha)
        for bright_color in ["white", "green", "cyan", "yellow", "#00FF66", "#FFFFFF"]:
            col = _bg_box_color(bright_color, opacity=0.5)
            self.assertIsNotNone(col)
            self.assertEqual(col[:3], (0, 0, 0), f"{bright_color} は黒半透明座布団であるべき")
            self.assertEqual(col[3], 128)

        # 暗色 (黒、極暗色) -> 白半透明 (255, 255, 255, alpha)
        for dark_color in ["black", "#000000", "#101010", "#222222"]:
            col = _bg_box_color(dark_color, opacity=0.5)
            self.assertIsNotNone(col)
            self.assertEqual(col[:3], (255, 255, 255), f"{dark_color} は白半透明座布団であるべき")
            self.assertEqual(col[3], 128)

    def test_invalid_color_fallback(self) -> None:
        """不正な色指定文字列が渡されてもクラッシュせず安全にフォールバックすること。"""
        cfg, _, c_key, _, _ = build_overlay_config_from_params({
            "color": "non_existent_color",
            "custom_color": "not_a_hex",
        })
        self.assertEqual(cfg.color, "black")
        self.assertEqual(cfg.custom_color, "")

        # レンダリングが正常に行われること
        ov = render_overlay_preview_pil({
            "color": "unknown",
            "custom_color": "invalid_hex",
        }, w=320, h=180)
        self.assertEqual(ov.size, (320, 180))

    def test_node_color_widgets_and_custom_color(self) -> None:
        """ノード層 (RecFrameImageOverlayNode / RecFrameVideoOverlayNode) での新カラー指定の動作検証。"""
        img_node = RecFrameImageOverlayNode()
        dummy_img = torch.zeros((1, 120, 160, 3), dtype=torch.float32)

        # プリセット名指定
        out_img, out_ov, _ = img_node.apply_overlay(image=dummy_img, color="green (暗視グリーン)")
        self.assertEqual(out_img.shape, (1, 120, 160, 3))
        self.assertEqual(out_ov.shape, (1, 120, 160, 4))

        # custom_color 指定
        out_img2, out_ov2, _ = img_node.apply_overlay(image=dummy_img, custom_color="#FFE100")
        self.assertEqual(out_img2.shape, (1, 120, 160, 3))


if __name__ == "__main__":
    unittest.main(verbosity=2)

