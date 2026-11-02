# rec-frame-ComfyUI AGENTS.md

カメラのファインダー風オーバーレイ（四隅L字枠＋電池マーク＋赤丸REC＋中央十字＋日時タイムコード＋UI劣化エフェクト）を ComfyUI の画像・動画生成パイプライン上で合成・出力するカスタムノードパッケージ。

元リポジトリ: `C:\Users\coffe\Documents\rec-frame-app` ([treeturtlefall-arch/rec-frame-app](https://github.com/treeturtlefall-arch/rec-frame-app))
ComfyUI 連携先: `C:\Users\coffe\Documents\ComfyUI\custom_nodes\rec-frame-ComfyUI`（ディレクトリジャンクションで直結）

> [!NOTE]
> **ドキュメント運用ルール**:
> - **仕様・アーキテクチャ・設計思想**: 本ファイル（[`AGENTS.md`](./AGENTS.md)）および [`SPEC.md`](./SPEC.md) に集約。
> - **更新履歴・変更ログ**: [`CHANGELOG.md`](./CHANGELOG.md) に記録。

---

## 1. ディレクトリ・ファイル構成

- `__init__.py` — ComfyUI カスタムノードパッケージのエントリーポイント。`NODE_CLASS_MAPPINGS` / `NODE_DISPLAY_NAME_MAPPINGS` およびフロントエンド拡張ディレクトリ `WEB_DIRECTORY = "./web"` を公開する。
- `nodes.py` — ComfyUI ノード定義層。PyTorch `Tensor` (`[B, H, W, C]`, float32 `0..1`) と `PIL.Image` の相互変換、バッチ/動画フレーム処理、キャッシュ制御、プレビューAPIエンドポイント (`POST /rec_frame/preview`) を行う。
  - **静止画・動画の役割分離設計**:
    - `RecFrameImageOverlayNode` (`RecFrameImageOverlay` / 表示名: `REC Frame (Image) [画像用]`) — 静止画特化ノード。動画専用の点滅・FPS設定を排除したスッキリしたUIで、枠の太さ・フォント・色・電池・REC文字・日時タイムコード・座布団・エフェクトをシンプルに調整可能。全フレーム同一のオーバーレイを1回のみ生成して高速一括合成。入力画像なし時は `empty_width` / `empty_height`（既定 1280x720）により単体オーバーレイジェネレーターとして機能。
    - `RecFrameVideoOverlayNode` (`RecFrameVideoOverlay` / 表示名: `REC Frame (Video) [動画用]`) — 動画・バッチフレーム特化ノード。画像用の基本設定に加え、赤丸REC点滅間隔 (`blink_red_dot_interval`) やフレーム経過に伴うタイムコード進行 (`advance_timecode_fps`) を完備。動画生成パイプライン向け。入力画像なし時は `empty_width` / `empty_height` / `empty_frames`（既定 24フレーム）により動画用透過連番枠を単体生成可能。
    - `RecFrameOverlayNode` (`RecFrameOverlay` / 表示名: `REC Frame Overlay (All-in-One / Legacy)`) — 既存ワークフロー互換用の統合ノード（全機能内包）。
    - `RecFrameCustomOverlayNode` (`RecFrameCustomOverlay`) — 既存ワークフロー互換用のエイリアス。
    - `RecFramePreviewNode` (`RecFramePreview` / 表示名: `Preview REC Overlay (枠プレビュー)`) — プレビュー専用ノード。`RecFrameImageOverlay` / `RecFrameVideoOverlay` / `RecFrameOverlay` から出力された `overlay_rgba` を受け取り、選択した背景色（黒・白・グレー・市松模様）の上に重ねてノード内にリアルタイム表示する。後続ノードへ `IMAGE` 出力も可能。
- `web/js/rec_frame_preview.js` — フロントエンド拡張（JavaScript）。各 REC オーバーレイノード（`RecFrameImageOverlay`, `RecFrameVideoOverlay`, `RecFrameOverlay`, `RecFrameCustomOverlay`）と `RecFramePreview` 間の接続を検知し、ウィジェット変更（`show_frame` ON/OFF、スライダー、フォント、`empty_width/height` 等）に連動して Queue Prompt を押さずにダイナミックにプレビュー画像を即時更新する。
- `rec_overlay.py` — 純粋な画像生成層（GUI・ComfyUI非依存、Pillowのみ）。`create_rec_overlay_with_config()` / `composite_with_config()` / `apply_ui_effects()` / `apply_custom_ui_effects()`。
- `rec_config.py` — `OverlayConfig` データクラス＋フォント・マーク素材解決ヘルパー。
  - **フォント自己完結化（OSシステムフォルダ非依存）**:
    - フォントはすべて `fonts/` ディレクトリ内で完結し、OSのシステムフォルダ（`C:/Windows/Fonts` 等）を無断走査・参照しない。
    - 同梱フォント（SIL OFL 1.1 / Apache 2.0）:
      1. `Roboto Condensed Bold(細長)` (`RobotoCondensed-Bold.ttf`) - デフォルト・標準ファインダー
      2. `Bebas Neue(縦長大文字)` (`BebasNeue-Regular.ttf`) - 映画・タイトル調
      3. `DSEG7 Classic(7セグLED)` (`DSEG7Classic-Bold.ttf`) - 液晶デジタルタイムコード
      4. `Share Tech Mono(等幅)` (`ShareTechMono-Regular.ttf`) - 計測機器・サイバー等幅
      5. `VT323(レトロドット)` (`VT323-Regular.ttf`) - 2000s レトロビットマップ
      6. `Zen Kaku Gothic(日本語)` (`ZenKakuGothicNew-Bold.ttf`) - 日本語対応ゴシック
    - 過去の旧キー（例: `Arial Narrow Bold(細長)`）が指定された場合も、対応する同梱フォントへ安全に自動マッピング。
    - ユーザー自作フォントは `fonts/` に配置するだけでドロップダウンに自動登録される（または `custom_font_path` で直接指定）。
  - マーク素材探索 (`discover_dot_assets()`)：
    - `assets/dots/` 内の `.png` / `.webp` を自動検出し `dot_style` 候補として提供。
- `fonts/` — 同梱のオープンソースフォント（SIL OFL 1.1）およびライセンス文書。
- `scripts/` — 公式運用ツールおよび保守スクリプト。
  - `create_workflows.py` — 公式ワークフロー JSON の一括生成・同期スクリプト。
  - `generate_demo_assets.py` — 公式ビジュアルデモアセットの一括生成スクリプト。
  - `generate_dot_assets.py` — 高解像度 (512x512) 丸素材アセットの一括生成スクリプト。
  - `download_builtin_fonts.py` — 同梱フォントの一括取得スクリプト。
  - `dev/` — 開発・検証用スクリプト群。
- `workflows/` — ComfyUI Desktop 向け公式ワークフロー JSON（基本・2000sレトロ・動画バッチ）。
  - `rec_frame_basic_workflow.json` — 静止画向け基本ワークフロー（`RecFrameImageOverlay` ＋ `RecFramePreview`）。
  - `rec_frame_2000s_digicam_workflow.json` — 2000s レトロデジカメ風プリセット（`RecFrameImageOverlay` ＋ `RecFramePreview`）。
  - `rec_frame_video_batch_workflow.json` — 動画・連続フレームアニメーション（`RecFrameVideoOverlay` ＋ `RecFramePreview`）。
- `assets/dots/` — 同梱の丸マーク透過素材（`flat_*` フラット真円、`glow_*` セルアニメ調発光光球）。ユーザーの自作マーク画像もここに配置可能。
- `README.md` — 英語公式ドキュメント（グローバル・ComfyUI-Manager向け正本）。ビジュアルデモ、全パラメータ、ワークフロー、FAQを網羅。
- `README_JA.md` — 日本語公式ドキュメント。全仕様、錯視メカニズムと調整Tips、自作フォント/マーク利用ガイドを完備。
- `assets/demo/` — 公式ドキュメント用ビジュアルアセット（ヒーローバナー、点滅ループGIF、レトロエフェクト段階比較、カラープリセット）。
- `rec_i18n.py` — 日英ラベル辞書・ヘルパー。
- `SPEC.md` — オーバーレイ寸法比率・エフェクト仕様の正本。
- `CHANGELOG.md` — バージョン毎の変更履歴。
- `tests/` — `pytest` / `unittest` によるコア描画回帰テストおよび ComfyUI `Tensor` 入出力・スライダー・動画点滅・ワークフロー検証テスト。
  - `tests/test_comfy_nodes.py`: コア描画エンジン・ノード層・エフェクト・スライダー・点滅等の自動テスト。
  - `tests/test_workflows.py`: 公式ワークフロー JSON の構文・リンク整合性・ウィジェット過不足検証テスト。

---

## 2. テスト・検証コマンド

ComfyUI 本体の仮想環境 Python を使って、単体で高速に自動テスト（`unittest`）を実行できる（ComfyUI サーバーを起動しなくてもノードの Tensor 変換・描画テストが可能）。

```powershell
# ノード層・描画エンジンの自動テストを実行 (38 tests)
& "C:\Users\coffe\Documents\ComfyUI\.venv\Scripts\python.exe" "C:\Users\coffe\Documents\rec-frame-ComfyUI\tests\test_comfy_nodes.py"

# 公式ワークフロー JSON の構文・リンク検証テストを実行
& "C:\Users\coffe\Documents\ComfyUI\.venv\Scripts\python.exe" "C:\Users\coffe\Documents\rec-frame-ComfyUI\tests\test_workflows.py"

# 公式ワークフロー JSON の一括再生成および ComfyUI user ディレクトリへの同期
& "C:\Users\coffe\Documents\ComfyUI\.venv\Scripts\python.exe" "C:\Users\coffe\Documents\rec-frame-ComfyUI\scripts\create_workflows.py"
```

---

## 3. 描画エンジン上の絶対ルール（壊さないこと）

`rec-frame-app` から継承した以下のピクセル精度・視覚設計ルールを厳守すること：

1. **相対ベクター計算 (`s = min(w, h)`)**
   - すべての寸法は短辺 `s = min(w, h)` を基準とした相対値で計算する。PNG素材の引き伸ばし貼り付けは行わない。
2. **四隅の端距離ピクセル一致（`-1` 補正）**
   - PIL の `ImageDraw.rectangle` は終端座標を含む inclusive 描画のため、右隅・下隅の起点は `w - 1 - margin` / `h - 1 - margin` とし、四隅の端からの距離を 1px の狂いもなく一致させる。
3. **赤丸と REC 文字の幾何中心合わせ・マーク素材合成 (`dot_style`)**
   - 赤丸（または透過マーク素材）と REC 文字はインク中央の中心線 `cy` を共有し、`anchor="lt"` でタイトなインク高さを測って `cy - text_h // 2` に配置する（`anchor="lm"` はフォントのアセンダ/ディセンダ差で文字が浮くため使用禁止）。また `rec_dy = int(s * 0.01)` の下げ補正を維持する。
   - `dot_style="classic"` の場合は数学的真円 `(255, 0, 0, 255)` をピクセルパーフェクトに描画する。
   - `dot_style` に素材名（または `custom_dot_path`）が指定された場合は、短辺 `s` のターゲットサイズ（直径 `dot_r * 2`）に `LANCZOS` で高品質リサイズし、中心を `(block_x + dot_r, cy)` に完全に一致させてアルファ合成する。
     - 解決順は `_resolve_dot_asset_path()`：`assets/dots/` の素材キー（stem）→ 画像ファイルの直接パス。合成は `paste(mask)` ではなく `alpha_composite`（座布団上でαが薄くならないように）。
   - バッチ高速化のため、リサイズ済みアセットは `_load_and_resize_dot_asset` (LRU cache) にキャッシュされる。
4. **線幅の独立性・無段階スケーリング (`thickness: 0〜100`)**
   - `thickness` スライダー（0〜100、default 50）が連動するのは「四隅のL字枠」のみ。電池の外枠線幅、赤丸サイズ、中央十字の線幅は独立比率のため連動させない。
   - **比率マッピング（区分線形補間）**:
     - `0`: 比率 `0.0010`（短辺1000pxで約1pxの極細線）
     - `50`: 比率 `0.0080`（標準・旧mediumと完全一致）
     - `100`: 比率 `0.0200`（短辺1000pxで約20pxの極太インパクト枠）
     - 最低保証: `max(1, int(round(s * ratio)))`
   - 電池マークやREC文字の配置Y座標は `margin_y + thickness + ...` で連動するため、枠をどれだけ太く・細くしても重ならずに美しく追従する。
   - 枠色（6色プリセット `white`/`black`/`green`/`cyan`/`red`/`yellow`、または任意HEX `custom_color`）が変わるのは枠・電池・文字・十字のみ。赤丸は素材指定またはクラシック真円 `(255, 0, 0, 255)` とする。
5. **UI劣化エフェクトの非破壊適用・順序固定とレトロ強度（`retro_effect: 0〜6`）の一本化**
   - エフェクト設定は、従来のプルダウンおよび3種の個別オーバーライド（`override_shift_level`, `override_bloom`, `override_pixel_scale`）を撤廃し、直感的な **`retro_effect` スライダー（0〜6）1本に完全集約**。
     - `0`: OFF (完全クリーン・現代ベクター)
     - `1`: 微弱 (Subtle / 現代デジカメ・初期液晶)
     - `2`: 標準 (Classic 2000s / 従来の2000sデジカメ風標準値)
     - `3`: 中 (Medium / ミニDV・トイカメラ)
     - `4`: 強 (Heavy / レトロVHS・ブラウン管)
     - `5`: 超強 (Extreme / 監視カメラ・SFホラー)
     - `6`: 極限Break (Near Break / 人間の視認から見て推測をもとに読める極限境界)
   - 既存ワークフローからの `effect`（`"normal"` → 0, `"2000s"` → 2）や旧オーバーライド指定も内部で安全に自動マッピングされ後方互換性を担保。
   - エフェクトは原本画像（ベース画像）には一切かけず、**描画済みの UI オーバーレイ層（RGBA）に対してのみ適用**してから `Image.alpha_composite` で重ねる。
   - 適用順序は **「RGBシフト → ブルーム → 低解像度化」** で固定する。ブルームは白枠と黒枠で半径・アルファ値を分岐させる。
6. **バッチ処理のキャッシュ最適化と静止画/動画の分離原則**
   - **静止画ノード (`RecFrameImageOverlay`)**: 点滅やタイムコード進行を持たないため、入力画像が複数フレーム（バッチ）であってもオーバーレイ（RGBA）を最初の 1 回のみ生成し、全フレームに対して `torch.lerp` で一括高速合成する（余計なキャッシュ検索やフレーム毎の分岐をゼロ化）。
   - **動画ノード (`RecFrameVideoOverlay`)**: MiniMax-H3 / Wan / AnimateDiff 等の 56 フレーム等のバッチ入力に対し、オーバーレイを `(赤丸点灯, タイムコード文字列)` キーの辞書でキャッシュし、必要最小限の描画（例: タイムコードが秒単位進行なら24フレームに1回＋点滅2状態のみ）で済ませる。
   - 合成処理は PIL を経由せず Tensor 上 (`torch.lerp` によるストレートα over 合成) で行う。入力画像を 8bit に量子化しないこと。
   - 赤丸点滅の消灯フレームは `show_red_dot=False` ではなく `red_dot_visible=False` を使う (レイアウトを維持し、REC 文字・座布団を動かさない)。
7. **フォントの自己完結・OSシステムフォルダ非アクセス**
   - ユーザーのプライバシー保護およびクロスプラットフォーム（Linux/Mac等）での描画一貫性を担保するため、`C:/Windows/Fonts` 等のOSシステムフォルダを無断走査・参照してはならない。
   - すべてのフォント解決は `fonts/` ディレクトリ内の同梱フォント（`RobotoCondensed-Bold.ttf` 等）またはユーザーが明示的に指定したパスのみで完結させること。
8. **半透明座布団ボックス (`bg_box_opacity`) と厳密インクセンタリング・L字枠クリアランス**
   - 視認性向上のための半透明シャープ長方形ボックス（座布団）は、左上（電池）、右上（REC）、右下（タイムコード）の全3要素に統一ルールで適用される。
   - **輝度連動反転色**: 描画色の知覚輝度（`0.299R + 0.587G + 0.114B`）を計算し、暗色時（黒など輝度 < 60）は白半透明 `rgba(255, 255, 255, alpha)`、明色・蛍光色時（白・緑・シアン・黄・赤等）は黒半透明 `rgba(0, 0, 0, alpha)` を自動適用して常に可読性を確保。
   - **L字枠クリアランス**: 各ボックスは L字枠の縦線・横線内側から一定の余白比率（`BOX_CLEARANCE_X_RATIO = 0.012`, `BOX_CLEARANCE_Y_RATIO = 0.010`）を厳守して配置され、枠の太さ（`thickness`）を変更しても接触・干渉しない。
   - **厳密インクセンタリング**: 文字配置は `font.getmask2(..., anchor="lt")` を利用した `_tight_ink_metrics` により、フォント固有のアセンダ・ディセンダやサイドベアリングの空きに惑わされず、実描画インクの幾何中心をボックスおよび赤丸の中心線 `cy` にピクセル単位で一致させる。

---

## 4. ComfyUI 本体との連携・運用ルール

- 本フォルダ (`C:\Users\coffe\Documents\rec-frame-ComfyUI`) は、`C:\Users\coffe\Documents\ComfyUI\custom_nodes\rec-frame-ComfyUI` からディレクトリジャンクション（リンク）として参照される。本フォルダ内のコードを編集すれば、そのまま ComfyUI 側に反映される。
- ノードの `INPUT_TYPES` やクラス定義を変更した場合は、ComfyUI Desktop の再起動（またはノード再読込）が必要。
- ComfyUI サーバーの起動・検証を行う場合は、必ず `C:\Users\coffe\Documents\ComfyUI\AGENTS.md` の「検証用サーバー・GPUメモリの管理」ルールに従い、ユーザーの ComfyUI Desktop 環境を優先し、不要なバックグラウンドプロセスや VRAM 占有を残さないこと。
