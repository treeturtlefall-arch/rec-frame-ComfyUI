"""多様な実画像に対してファインダーオーバーレイを一括合成し、
インタラクティブなA/BテストHTMLビューアを生成するスクリプト。

- 元画像フォルダ (E:\\Tools\\Images) は完全読み取り専用 (改変・上書き一切なし)。
- 出力は tests/preview_gallery/ に分離。
"""
from __future__ import annotations

import json
import os
import random
import sys
from pathlib import Path
from PIL import Image, ImageOps

# プロジェクトルートを sys.path に追加
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from rec_config import OverlayConfig
from rec_overlay import create_rec_overlay_with_config

SOURCE_DIR = Path(r"E:\Tools\Images")
OUTPUT_DIR = ROOT_DIR / "tests" / "preview_gallery"
SAMPLE_COUNT = 10
VALID_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

# 比較バリエーションの定義 (ID, ラベル, ショートカットキー, 設定)
VARIATIONS = [
    {
        "id": "classic_white",
        "label": "1: classic (幾何真円・白)",
        "key": "1",
        "config": {"color": "white", "thickness": 50, "dot_style": "classic (幾何学・真円)", "rec_label": "REC"},
    },
    {
        "id": "flat_red_white",
        "label": "2: flat_red (真円素材・白)",
        "key": "2",
        "config": {"color": "white", "thickness": 50, "dot_style": "flat_red", "rec_label": "REC"},
    },
    {
        "id": "glow_red_white",
        "label": "3: glow_red (アニメ発光・白)",
        "key": "3",
        "config": {"color": "white", "thickness": 50, "dot_style": "glow_red", "rec_label": "REC"},
    },
    {
        "id": "flat_red_black",
        "label": "4: flat_red (真円素材・黒)",
        "key": "4",
        "config": {"color": "black", "thickness": 50, "dot_style": "flat_red", "rec_label": "REC"},
    },
    {
        "id": "glow_green_live",
        "label": "5: glow_green (LIVE配信風)",
        "key": "5",
        "config": {"color": "white", "thickness": 50, "dot_style": "glow_green", "rec_label": "LIVE"},
    },
    {
        "id": "thick_20_flat",
        "label": "6: 極細枠 (thickness 20)",
        "key": "6",
        "config": {"color": "white", "thickness": 20, "dot_style": "flat_red", "rec_label": "REC"},
    },
    {
        "id": "thick_80_flat",
        "label": "7: 極太枠 (thickness 80)",
        "key": "7",
        "config": {"color": "white", "thickness": 80, "dot_style": "flat_red", "rec_label": "REC"},
    },
]


def collect_source_images() -> list[Path]:
    """E:\\Tools\\Images から有効な画像ファイルを収集する。"""
    if not SOURCE_DIR.is_dir():
        raise FileNotFoundError(f"Source dir not found: {SOURCE_DIR}")
    files: list[Path] = []
    for p in SOURCE_DIR.rglob("*"):
        if p.is_file() and p.suffix.lower() in VALID_EXTS:
            files.append(p)
    return files


def generate_gallery() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    images_dir = OUTPUT_DIR / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    all_files = collect_source_images()
    print(f"Total source images found: {len(all_files)}")

    # ランダムサンプリング (多様性を確保)
    rng = random.Random(42)  # 再現性のある乱数シード
    chosen = rng.sample(all_files, min(SAMPLE_COUNT, len(all_files)))

    manifest: list[dict] = []

    for idx, src_path in enumerate(chosen):
        safe_name = src_path.name.encode("ascii", "replace").decode("ascii")
        print(f"[{idx+1}/{len(chosen)}] Processing: {safe_name}")
        try:
            with Image.open(src_path) as orig_im:
                # EXIF補正 & RGB変換
                im = ImageOps.exif_transpose(orig_im).convert("RGB")
        except Exception as e:
            print(f"  [!] Skip error: {e}")
            continue

        w, h = im.size
        # プレビュー表示の快適さのため、極端に巨大な画像（長辺1800px超）はアスペクト比維持でリサイズ
        max_dim = max(w, h)
        if max_dim > 1800:
            scale = 1800.0 / max_dim
            w, h = int(round(w * scale)), int(round(h * scale))
            im = im.resize((w, h), Image.Resampling.LANCZOS)

        base_id = f"sample_{idx+1:02d}"
        var_data: dict[str, str] = {}
        crops_data: dict[str, str] = {}

        # 原本（オーバーレイなし）も保存
        orig_filename = f"{base_id}_orig.webp"
        im.save(images_dir / orig_filename, format="WEBP", quality=92)
        var_data["orig"] = orig_filename

        # 各バリエーションの生成
        for var in VARIATIONS:
            v_id = var["id"]
            cfg_dict = var["config"]
            cfg = OverlayConfig(
                color=cfg_dict["color"],
                thickness=cfg_dict["thickness"],
                dot_style=cfg_dict["dot_style"],
                rec_label=cfg_dict["rec_label"],
                show_timecode=True,
                timecode_text="2026/11/01 PM 08:30",
            )
            overlay = create_rec_overlay_with_config(w, h, cfg)
            comp = Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB")

            filename = f"{base_id}_{v_id}.webp"
            comp.save(images_dir / filename, format="WEBP", quality=90)
            var_data[v_id] = filename

            # 右上 REC マーク周辺の拡大クロップ (短辺比率から計算)
            s = min(w, h)
            dot_r = int(s * 0.022)
            margin = int(s * 0.028)
            crop_w = int(s * 0.28)
            crop_h = int(s * 0.14)
            x1 = w - margin + int(s * 0.01)
            x0 = max(0, x1 - crop_w)
            y0 = max(0, margin - int(s * 0.01))
            y1 = min(h, y0 + crop_h)

            crop_im = comp.crop((x0, y0, x1, y1))
            crop_filename = f"{base_id}_{v_id}_crop.webp"
            crop_im.save(images_dir / crop_filename, format="WEBP", quality=95)
            crops_data[v_id] = crop_filename

        manifest.append({
            "id": base_id,
            "title": src_path.stem,
            "size": f"{w}x{h}",
            "variations": var_data,
            "crops": crops_data,
        })

    # HTML ギャラリー生成
    html_path = OUTPUT_DIR / "index.html"
    render_html(html_path, manifest)
    print(f"\n[+] Gallery successfully created: {html_path}")
    return html_path


def render_html(dest: Path, manifest: list[dict]) -> None:
    manifest_json = json.dumps(manifest, ensure_ascii=False)
    variations_json = json.dumps(VARIATIONS, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>REC Frame Overlay - Interactive A/B Comparison Gallery</title>
<style>
  :root {{
    --bg-dark: #0f1117;
    --panel-bg: #1a1d27;
    --border: #2c3143;
    --accent: #ff3344;
    --text: #e6edf3;
    --text-dim: #8b949e;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
  body {{
    background: var(--bg-dark);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Meiryo, sans-serif;
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
  }}
  header {{
    background: var(--panel-bg);
    border-bottom: 1px solid var(--border);
    padding: 10px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-shrink: 0;
  }}
  .logo {{
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 1px;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .rec-badge {{
    display: inline-block;
    width: 10px;
    height: 10px;
    background: var(--accent);
    border-radius: 50%;
    box-shadow: 0 0 8px var(--accent);
  }}
  .shortcuts-hint {{
    font-size: 13px;
    color: var(--text-dim);
  }}
  .key-badge {{
    background: #252a38;
    border: 1px solid var(--border);
    padding: 2px 6px;
    border-radius: 4px;
    color: #fff;
    font-family: monospace;
    font-size: 12px;
  }}
  main {{
    display: flex;
    flex: 1;
    min-height: 0;
    min-width: 0;
    overflow: hidden;
    position: relative;
  }}
  .preview-area {{
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 16px;
    background: #090a0f;
    min-height: 0;
    min-width: 0;
    overflow: auto;
  }}
  .preview-area.fit-mode {{
    overflow: hidden;
  }}
  .image-wrapper {{
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 10px 40px rgba(0,0,0,0.8);
    border-radius: 4px;
    background: #000;
  }}
  .preview-area.fit-mode .image-wrapper {{
    max-width: 100%;
    max-height: 100%;
  }}
  .main-image {{
    display: block;
  }}
  .preview-area.fit-mode .main-image {{
    max-width: 100%;
    max-height: calc(100vh - 140px);
    width: auto;
    height: auto;
    object-fit: contain;
  }}
  .preview-area.actual-mode .main-image {{
    max-width: none;
    max-height: none;
  }}
  .loupe-card {{
    position: absolute;
    bottom: 24px;
    right: 24px;
    background: rgba(26, 29, 39, 0.95);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px;
    box-shadow: 0 12px 30px rgba(0,0,0,0.8);
    display: flex;
    flex-direction: column;
    gap: 6px;
    backdrop-filter: blur(8px);
    z-index: 100;
    transition: opacity 0.2s ease;
  }}
  .loupe-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .loupe-title {{
    font-size: 11px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .loupe-toggle-btn {{
    background: transparent;
    border: none;
    color: var(--text-dim);
    font-size: 11px;
    cursor: pointer;
  }}
  .loupe-toggle-btn:hover {{
    color: var(--text);
  }}
  .loupe-image {{
    width: 280px;
    height: auto;
    border-radius: 4px;
    border: 1px solid rgba(255,255,255,0.1);
  }}
    height: auto;
    border-radius: 4px;
    border: 1px solid rgba(255,255,255,0.1);
  }}
  .controls-bar {{
    background: var(--panel-bg);
    border-top: 1px solid var(--border);
    padding: 12px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-shrink: 0;
  }}
  .var-buttons {{
    display: flex;
    gap: 8px;
  }}
  .btn {{
    background: #252a38;
    color: var(--text);
    border: 1px solid var(--border);
    padding: 8px 14px;
    border-radius: 6px;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.15s ease;
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .btn:hover {{
    background: #31374a;
    border-color: #4a526b;
  }}
  .btn.active {{
    background: var(--accent);
    color: #fff;
    border-color: var(--accent);
    box-shadow: 0 0 12px rgba(255, 51, 68, 0.4);
    font-weight: 600;
  }}
  .nav-buttons {{
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .counter {{
    font-size: 14px;
    color: var(--text-dim);
    font-variant-numeric: tabular-nums;
  }}
</style>
</head>
<body>

<header>
  <div class="logo">
    <span class="rec-badge"></span>
    <span>REC Frame Overlay A/B Viewer</span>
  </div>
  <div class="shortcuts-hint">
    ショートカット: <span class="key-badge">1〜7</span> バリエーション | <span class="key-badge">←</span> <span class="key-badge">→</span> 画像送り | <span class="key-badge">F</span> 全体/原寸 | <span class="key-badge">Z</span> ルーペON/OFF | <span class="key-badge">0</span> 原本
  </div>
</header>

<main>
  <div class="preview-area fit-mode" id="previewArea">
    <div class="image-wrapper">
      <img id="mainImage" class="main-image" src="" alt="preview">
    </div>

    <!-- 右下の拡大ルーペ (RECマークと被らない位置) -->
    <div class="loupe-card" id="loupeCard">
      <div class="loupe-header">
        <span class="loupe-title">REC 拡大ディテール (<span class="key-badge">Z</span>で消去)</span>
        <button class="loupe-toggle-btn" id="loupeCloseBtn" title="閉じる">✕</button>
      </div>
      <img id="loupeImage" class="loupe-image" src="" alt="crop">
    </div>
  </div>
</main>

<div class="controls-bar">
  <div class="nav-buttons">
    <button class="btn" id="prevBtn">◀ (<span class="key-badge">←</span>)</button>
    <span class="counter" id="imageCounter">1 / 10</span>
    <button class="btn" id="nextBtn">(<span class="key-badge">→</span>) ▶</button>
    <button class="btn" id="fitToggleBtn">表示: 全体収容 (<span class="key-badge">F</span>)</button>
    <span style="font-size:13px; color:#8b949e; margin-left:6px;" id="imageTitle"></span>
  </div>

  <div class="var-buttons" id="varButtonsContainer">
    <!-- JS でバリエーションボタンを生成 -->
  </div>
</div>

<script>
const manifest = {manifest_json};
const variations = {variations_json};

let currentImgIdx = 0;
let currentVarId = "flat_red_white"; // デフォルトは flat_red
let isFitMode = true;
let isLoupeVisible = true;

const mainImage = document.getElementById("mainImage");
const loupeImage = document.getElementById("loupeImage");
const loupeCard = document.getElementById("loupeCard");
const previewArea = document.getElementById("previewArea");
const imageCounter = document.getElementById("imageCounter");
const imageTitle = document.getElementById("imageTitle");
const varButtonsContainer = document.getElementById("varButtonsContainer");
const fitToggleBtn = document.getElementById("fitToggleBtn");
const loupeCloseBtn = document.getElementById("loupeCloseBtn");

// バリエーションボタン作成
variations.forEach(v => {{
  const btn = document.createElement("button");
  btn.className = "btn";
  btn.id = "btn_" + v.id;
  btn.innerHTML = `<span class="key-badge">${{v.key}}</span> ${{v.label.split(":")[1] || v.label}}`;
  btn.onclick = () => setVariation(v.id);
  varButtonsContainer.appendChild(btn);
}});

// 原本トグルボタン (0)
const origBtn = document.createElement("button");
origBtn.className = "btn";
origBtn.id = "btn_orig";
origBtn.innerHTML = `<span class="key-badge">0</span> 原本`;
origBtn.onclick = () => setVariation("orig");
varButtonsContainer.appendChild(origBtn);

function updateView() {{
  if (!manifest.length) return;
  const item = manifest[currentImgIdx];
  const filename = item.variations[currentVarId] || item.variations["flat_red_white"];
  const cropname = item.crops[currentVarId] || item.crops["flat_red_white"];

  mainImage.src = "images/" + filename;
  if (cropname && currentVarId !== "orig" && isLoupeVisible) {{
    loupeCard.style.display = "flex";
    loupeImage.src = "images/" + cropname;
  }} else {{
    loupeCard.style.display = "none";
  }}

  imageCounter.textContent = `${{currentImgIdx + 1}} / ${{manifest.length}}`;
  imageTitle.textContent = `${{item.title}} (${{item.size}})`;

  // ボタンアクティブ状態更新
  document.querySelectorAll(".var-buttons .btn").forEach(b => b.classList.remove("active"));
  const activeBtn = document.getElementById("btn_" + currentVarId);
  if (activeBtn) activeBtn.classList.add("active");
}}

function setVariation(varId) {{
  currentVarId = varId;
  updateView();
}}

function nextImage() {{
  currentImgIdx = (currentImgIdx + 1) % manifest.length;
  updateView();
}}

function prevImage() {{
  currentImgIdx = (currentImgIdx - 1 + manifest.length) % manifest.length;
  updateView();
}}

function toggleFitMode() {{
  isFitMode = !isFitMode;
  if (isFitMode) {{
    previewArea.classList.remove("actual-mode");
    previewArea.classList.add("fit-mode");
    fitToggleBtn.innerHTML = '表示: 全体収容 (<span class="key-badge">F</span>)';
  }} else {{
    previewArea.classList.remove("fit-mode");
    previewArea.classList.add("actual-mode");
    fitToggleBtn.innerHTML = '表示: 原寸100% (<span class="key-badge">F</span>)';
  }}
}}

function toggleLoupe() {{
  isLoupeVisible = !isLoupeVisible;
  updateView();
}}

document.getElementById("prevBtn").onclick = prevImage;
document.getElementById("nextBtn").onclick = nextImage;
fitToggleBtn.onclick = toggleFitMode;
loupeCloseBtn.onclick = toggleLoupe;

// キーボードイベントハンドラ
window.addEventListener("keydown", (e) => {{
  const key = e.key.toLowerCase();
  if (e.key === "ArrowRight") {{
    nextImage();
  }} else if (e.key === "ArrowLeft") {{
    prevImage();
  }} else if (key === "0") {{
    setVariation("orig");
  }} else if (key === "f") {{
    toggleFitMode();
  }} else if (key === "z") {{
    toggleLoupe();
  }} else {{
    const found = variations.find(v => v.key === e.key);
    if (found) {{
      setVariation(found.id);
    }}
  }}
}});

// 初期表示
updateView();
</script>

</body>
</html>
"""
    with open(dest, "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    generate_gallery()
