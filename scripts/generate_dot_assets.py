"""アニメ調発光丸素材 (透過PNG) 生成スクリプト。

セルアニメの撮影処理（光核＋主球＋外周グロー光彩）を模した高解像度 (512x512) の
透過光球アセットを一括生成し、`assets/dots/` ディレクトリに配置する。
"""
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
from PIL import Image

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "dots"
SIZE = 512

# カラーパレット定義 (表示名/ファイル名, ベース色RGB, 光核色RGB)
PALETTES = {
    "glow_red": {
        "base": (255, 25, 35),
        "core": (255, 235, 235),
    },
    "glow_green": {
        "base": (25, 240, 90),
        "core": (230, 255, 240),
    },
    "glow_amber": {
        "base": (255, 145, 10),
        "core": (255, 245, 220),
    },
    "glow_cyan": {
        "base": (0, 220, 255),
        "core": (225, 250, 255),
    },
    "glow_white": {
        "base": (205, 225, 255),
        "core": (255, 255, 255),
    },
}


def generate_glow_ball(base_rgb: tuple[int, int, int], core_rgb: tuple[int, int, int], size: int = SIZE) -> Image.Image:
    """セルアニメ調の発光球 (RGBA) を数理計算でレンダリングする。"""
    # 座標グリッド作成 (中心を原点 0, 0、半径 R を 1.0 とする)
    y, x = np.ogrid[:size, :size]
    center = (size - 1) / 2.0
    r = np.sqrt((x - center) ** 2 + (y - center) ** 2) / center  # 0.0 (中心) 〜 1.0 (端)

    # 1. 光核 (Core) の重み: r=0..0.40 で急激に立ち上がり、中心は白く発光
    core_w = np.clip(1.0 - (r / 0.42), 0.0, 1.0) ** 1.8

    # 2. RGBカラー補間
    r_chan = np.clip(base_rgb[0] * (1.0 - core_w) + core_rgb[0] * core_w, 0, 255)
    g_chan = np.clip(base_rgb[1] * (1.0 - core_w) + core_rgb[1] * core_w, 0, 255)
    b_chan = np.clip(base_rgb[2] * (1.0 - core_w) + core_rgb[2] * core_w, 0, 255)

    # 3. アルファプロファイル (アニメ的な実体感 + 周囲の柔らかな発光オーラ)
    # - r <= 0.52: 実体球 (alpha = 1.0)
    # - 0.52 < r <= 0.68: 実体エッジの光の滲み (1.0 -> 0.6)
    # - 0.68 < r <= 1.00: 外周グローの裾野 (0.6 -> 0.0)
    alpha = np.zeros_like(r)
    mask_inner = r <= 0.52
    mask_edge = (r > 0.52) & (r <= 0.68)
    mask_halo = (r > 0.68) & (r <= 1.0)

    alpha[mask_inner] = 1.0

    t_edge = (r[mask_edge] - 0.52) / (0.68 - 0.52)
    alpha[mask_edge] = 1.0 - 0.40 * (t_edge ** 0.8)

    t_halo = (r[mask_halo] - 0.68) / (1.0 - 0.68)
    alpha[mask_halo] = 0.60 * ((1.0 - t_halo) ** 1.8)

    alpha_chan = np.clip(alpha * 255.0, 0, 255).astype(np.uint8)

    rgba = np.stack([
        r_chan.astype(np.uint8),
        g_chan.astype(np.uint8),
        b_chan.astype(np.uint8),
        alpha_chan,
    ], axis=-1)

    return Image.fromarray(rgba, mode="RGBA")


def generate_flat_circle(rgb: tuple[int, int, int], size: int = SIZE) -> Image.Image:
    """発光なし・純色フラットな真円 (RGBA、外周アンチエイリアスのみ) を生成する。"""
    y, x = np.ogrid[:size, :size]
    center = (size - 1) / 2.0
    r = np.sqrt((x - center) ** 2 + (y - center) ** 2) / center

    # 半径 0.85 まで完全不透明、0.85〜0.88 でアンチエイリアス
    r_body = 0.85
    aa_width = 2.0 / center  # 約2px分のアンチエイリアス
    alpha = np.clip(1.0 - (r - r_body) / aa_width, 0.0, 1.0)

    rgba = np.zeros((size, size, 4), dtype=np.uint8)
    rgba[..., 0] = rgb[0]
    rgba[..., 1] = rgb[1]
    rgba[..., 2] = rgb[2]
    rgba[..., 3] = (alpha * 255.0).astype(np.uint8)

    return Image.fromarray(rgba, mode="RGBA")


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generating dot assets in: {ASSETS_DIR}")

    # 発光光球
    for name, colors in PALETTES.items():
        out_path = ASSETS_DIR / f"{name}.png"
        img = generate_glow_ball(colors["base"], colors["core"])
        img.save(out_path, format="PNG", optimize=True)
        print(f"  [+] Created: {out_path.name}")

    # 発光ゼロのフラット真円 (純色アンチエイリアス)
    flat_colors = {
        "flat_red": (255, 0, 0),
        "flat_green": (0, 255, 80),
        "flat_amber": (255, 145, 0),
        "flat_cyan": (0, 220, 255),
        "flat_white": (255, 255, 255),
    }
    for name, rgb in flat_colors.items():
        out_path = ASSETS_DIR / f"{name}.png"
        img = generate_flat_circle(rgb)
        img.save(out_path, format="PNG", optimize=True)
        print(f"  [+] Created: {out_path.name}")

    print("All assets successfully generated!")


if __name__ == "__main__":
    main()
