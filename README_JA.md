# rec-frame-ComfyUI

[English Documentation (README.md)](./README.md) | **日本語**

カメラのファインダー風オーバーレイ（四隅L字枠・電池マーク・赤丸REC・中央フォーカス十字・日時タイムコード・半透明座布団・レトロUI劣化エフェクト）を ComfyUI の画像・動画生成パイプライン上で合成・出力するカスタムノードパッケージです。

単体アプリ版 [treeturtlefall-arch/rec-frame-app](https://github.com/treeturtlefall-arch/rec-frame-app) の高精度描画エンジンを ComfyUI パイプライン向けに移植・最適化し、静止画はもちろん、動画生成（AnimateDiff / Wan / MiniMax 等）における**赤丸RECの点滅**や**タイムコードの自動進行**にも完全対応しています。

---

## ビジュアルプレビュー (Showcase)

### 4つの代表的なスタイル
![Hero Showcase](./assets/demo/hero_showcase.png)

### 動画パイプラインでの動作 (赤丸REC点滅 ＋ タイムコード進行)
![Video Playback Demo](./assets/demo/video_playback.gif)

---

## 主な特長

1. **短辺基準の相対ベクター計算 (`s = min(w, h)`)**
   - どんなアスペクト比（16:9, 4:3, 1:1, 9:16縦型等）や解像度でも、素材の引き伸ばし歪みが生じず、常に均整のとれたファインダー枠を描画します。
2. **ピクセルパーフェクトな四隅等長描画**
   - PIL の仕様（inclusive描画）を `-1` 補正し、四隅すべてのL字枠が1ピクセルの狂いもなく完全に等長・均等マージンで配置されます。
3. **静止画と動画の役割分離設計**
   - 静止画向けの `RecFrameImageOverlay` と、動画・連続フレーム特化の `RecFrameVideoOverlay` に分離。動画ノードでは点滅・タイムコードキャッシュにより数十フレームのバッチも一瞬で合成します。
4. **Queue Prompt 不要のリアルタイムプレビュー (`RecFramePreview`)**
   - ウィジェットの値（枠の太さ、フォント、色、ON/OFF等）を変更した瞬間、ComfyUIの生成キューを走らせることなくノード内でダイナミックに即座に枠のプレビューが更新されます。
5. **直感的なレトロUI劣化スライダー (`retro_effect: 0〜6`)**
   - 色収差（RGBシフト）→ ブルーム（CRT発光）→ 低解像度化の順でUIオーバーレイ層にのみ非破壊で適用。現代のクリアなベクター（0）から2000年代デジカメ（2）、極限VHS（6）まで無段階に質感をコントロールできます。
6. **フォントの自己完結（プライバシー保護 & 環境非依存）**
   - OSのシステムフォルダ（`C:/Windows/Fonts` 等）を無断走査・参照せず、同梱のオープンソースフォント（SIL OFL）および `fonts/` 内のみで完結。Linux / Mac / Windows 全環境で同一の描画結果を保証します。

---

## 収録ノード（カテゴリ: `image/overlay`）

### 1. `REC Frame (Image) [画像用]` (`RecFrameImageOverlay`)
静止画パイプライン特化ノード。動画専用の点滅・FPS設定を省いたスッキリしたUIで、枠の太さ・フォント・色・電池・REC文字・日時・座布団・エフェクトをシンプルに調整できます。
- 全フレーム同一のオーバーレイを1回のみ生成して高速一括合成。
- 入力画像未接続時は `empty_width` / `empty_height`（既定 1280x720）により**単体オーバーレイジェネレーター**として機能します。

### 2. `REC Frame (Video) [動画用]` (`RecFrameVideoOverlay`)
動画・連続フレームバッチ特化ノード。画像用の基本設定に加え、以下の動画専用機能を完備しています：
- **赤丸REC点滅間隔 (`blink_red_dot_interval`)**: 指定フレーム周期で赤丸を点滅（例: 24fps動画で `12` なら0.5秒点灯/0.5秒消灯）。消灯時もレイアウトを崩さずREC文字と座布団の位置を固定。
- **タイムコード自動加算 (`advance_timecode_fps`)**: 指定FPSに基づき、フレーム経過に合わせてタイムコードの秒数を自動でカウントアップ。
- 入力画像未接続時は `empty_width` / `empty_height` / `empty_frames`（既定 24フレーム）により、**動画用透過連番オーバーレイを単体生成**可能です。

### 3. `Preview REC Overlay (枠プレビュー)` (`RecFramePreview`)
リアルタイムプレビュー専用ノード。各RECノードから出力された `overlay_rgba` を接続することで、**Queue Prompt を押さずにウィジェット変更をその場でダイナミックに確認**できます。
- 背景色を4種類（黒・白・グレー・透過市松模様）から切り替え可能。
- 表示解像度比率（Full, 1/2, 1/4）の切り替えに対応。
- 後続の画像保存ノードへ `IMAGE` 出力も可能。

### 4. `REC Frame Overlay (All-in-One / Legacy)` (`RecFrameOverlay` / `RecFrameCustomOverlay`)
既存ワークフローとの完全互換性を維持するためのレガシー統合ノードです。

---

## 設定パラメータ一覧

### 基本設定 (Required)
| パラメータ | 型 / 選択肢 | 既定値 | 説明 |
|---|---|---|---|
| `color` | `white`, `black`, `green`, `cyan`, `red`, `yellow` | `white` | 枠・電池・文字・十字のテーマカラー（6色プリセット） |
| `font_key` | ドロップダウン (同梱6種＋自作) | `Roboto Condensed Bold(細長)` | 同梱のオープンソースフォントまたは `fonts/` に配置した自作フォント |
| `retro_effect` | `INT` (スライダー 0〜6) | `0` | UI劣化エフェクト強度（0: OFF 〜 2: 2000s標準 〜 6: 極限Break） |
| `show_frame` | `BOOLEAN` | `True` | 四隅のL字ファインダー枠の表示/非表示 |
| `thickness` | `INT` (スライダー 0〜100) | `50` | 枠の太さ（0で極細1px、50で標準、100で極太インパクト枠） |
| `show_rec` | `BOOLEAN` | `True` | RECインジケーター（赤丸＋文字）の表示/非表示 |
| `dot_style` | ドロップダウン (アセット一覧) | `flat_red` | マーク素材（`flat_*` 真円、`glow_*` 発光光球、`classic` 幾何真円） |
| `rec_label` | `STRING` | `"REC"` | 表示文字列（`"LIVE"`, `"PLAY"`, `"STBY"`, `"ALERT"` 等に変更可能） |
| `show_battery`| `BOOLEAN` | `True` | 電池マークの表示/非表示 |
| `battery_bars`| `INT` (0〜4) | `4` | バッテリー残量バー本数（0で空バッテリー・要充電表現） |
| `show_cross`  | `BOOLEAN` | `False` | 中央フォーカス十字（センタークロス）の表示/非表示 |
| `show_timecode`| `BOOLEAN` | `False` | タイムコード（日時）の表示/非表示 |
| `timecode_mode`| `manual`, `now` | `manual` | 手入力文字列 / 現在時刻の自動取得 |
| `timecode_text`| `STRING` | `""` | 表示日時（`YYYY/MM/DD AM/PM HH:MM` 形式、または自由テキスト） |

### 詳細調整・動画向け設定 (Optional)
| パラメータ | 型 | 既定値 | 説明 |
|---|---|---|---|
| `images` / `image` | `IMAGE` | 未接続可 | 入力画像または動画フレームバッチ（未接続時は単体オーバーレイを生成） |
| `custom_color` | `STRING` | `""` | 任意の色指定（`#00FF50` 等のHEXコード）。指定時は `color` より最優先 |
| `custom_font_path` | `STRING` | `""` | 外部フォント（`.ttf`, `.otf`, `.ttc`）のフルパス直接指定（再起動不要） |
| `custom_dot_path` | `STRING` | `""` | 外部マーク画像（透過PNG/WebP）のフルパス直接指定（再起動不要） |
| `bg_box_opacity` | `FLOAT` (0.0〜1.0) | `0.10` | 文字・電池背後の半透明座布団の不透明度（輝度連動で白/黒自動反転） |
| `margin_ratio` | `FLOAT` (0.0〜0.2) | `0.020` | 四隅枠の外側マージン比率（短辺基準） |
| `arm_len_ratio` | `FLOAT` (0.01〜0.5) | `0.15` | L字枠の腕の長さ比率（0.18〜0.20に広げるとより伸びやかな枠に） |
| `blink_red_dot_interval` | `INT` (動画用) | `0` | 赤丸点滅フレーム周期（0で常時点灯、24fps動画で12なら0.5秒点滅） |
| `advance_timecode_fps` | `FLOAT` (動画用) | `0.0` | フレーム経過に伴うタイムコード進行FPS（0.0で固定） |
| `empty_width` / `empty_height` | `INT` | 1280x720 | 入力画像未接続時の生成キャンバス解像度 |
| `empty_frames` | `INT` (動画用) | `24` | 入力画像未接続時の生成フレーム数 |

---

## ビジュアル詳細比較

### レトロUI劣化エフェクト (`retro_effect: 0〜6`)
![Retro Effect Levels](./assets/demo/retro_effect_levels.png)

* **`0: OFF (Clean Vector)`**: 現代的な高精細ベクター描画。にじみ・ノイズのないクリーンな仕上がり。
* **`1: Subtle (Digicam)`**: 2000年代初期液晶ディスプレイの微かなにじみ。現代の生成AI画像にも自然に馴染みます。
* **`2: Classic (Y2K)`**: 標準プリセット。適度な色収差（RGBシフト）とブルームによる2000sデジカメ質感。
* **`3: Medium (MiniDV)`**: ハンディカムやトイカメラ風のやや強めな液晶劣化。
* **`4: Heavy (VHS)`**: ブラウン管モニターやレトロVHSテープの強い走査線・光のにじみ。
* **`5: Extreme (CCTV)`**: 監視カメラ・ファウンドフッテージ・SFホラー調の荒廃した質感。
* **`6: Near Break`**: 人間の知覚から見て文字やマークを推測・判読できる極限境界。

### カラープリセット & 発光ドット素材
![Color Presets](./assets/demo/color_presets.png)

6色のカラープリセット（`white`, `green`, `cyan`, `red`, `yellow`, `black`）および任意HEXカラーに対応。背景座布団（`bg_box_opacity`）は描画色の知覚輝度を自動判定し、暗い色の時は白半透明、明るい色の時は黒半透明が敷かれるため、どんな背景画像の上でも常に高い可読性を維持します。

---

## 同梱フォント一覧（オープンソース / OS非依存）

すべて `fonts/` ディレクトリ内に同梱されており、OSのシステムフォントを一切参照しません。

1. **`Roboto Condensed Bold(細長)`** (SIL OFL 1.1) — 標準・現代カメラファインダー
2. **`Bebas Neue(縦長大文字)`** (SIL OFL 1.1) — 映画風・力強いシネマタイトル調
3. **`DSEG7 Classic(7セグLED)`** (SIL OFL 1.1) — 液晶デジタル時計・カウンター表現
4. **`Share Tech Mono(等幅)`** (SIL OFL 1.1) — ナイトビジョン・計測機器・サイバーHUD
5. **`VT323(レトロドット)`** (SIL OFL 1.1) — 2000s Y2K レトロビットマップ・オールドデジカメ
6. **`Zen Kaku Gothic(日本語)`** (SIL OFL 1.1) — 日本語テキスト対応の視認性に優れた角ゴシック

---

## 公式ワークフロー（ComfyUI Desktop 対応）

[`workflows/`](./workflows/) フォルダに、ドラッグ＆ドロップですぐに試せる公式ワークフローを**日本語版（`_ja.json`）と英語版（`_en.json`）の完全分離形式**で同梱しています。また、ComfyUI Desktop の左側メニュー「Workflows」ブラウザ（`rec-frame/` フォルダ）からも直接開くことができます。

1. **基本・静止画ワークフロー** ([`rec_frame_basic_workflow_ja.json`](./workflows/rec_frame_basic_workflow_ja.json) / [EN](workflows/rec_frame_basic_workflow_en.json))
   - 画像読込 → `RecFrameImageOverlay` ＆ `RecFramePreview` → 画像プレビュー＆保存
2. **2000s レトロデジカメ風ワークフロー** ([`rec_frame_2000s_digicam_workflow_ja.json`](./workflows/rec_frame_2000s_digicam_workflow_ja.json) / [EN](workflows/rec_frame_2000s_digicam_workflow_en.json))
   - `Share Tech Mono` / `VT323` フォント、`retro_effect: 2`、`STBY`表示、バッテリー3本、半透明座布団プリセット
3. **動画・バッチアニメーションワークフロー** ([`rec_frame_video_batch_workflow_ja.json`](./workflows/rec_frame_video_batch_workflow_ja.json) / [EN](workflows/rec_frame_video_batch_workflow_en.json))
   - `Load Video` → `RecFrameVideoOverlay` (`blink_red_dot_interval: 24`, `advance_timecode_fps: 24.0`) → `Save Video`

---

## インストール方法

### 方法 1: ComfyUI-Manager（推奨）
1. ComfyUI 画面内の **Manager** ボタンを開く。
2. **Custom Nodes Manager** を選択し、検索欄に `rec-frame` または `REC Frame` と入力。
3. **Install** をクリックし、ComfyUI を再起動する。

### 方法 2: 手動インストール (Git Clone)
ComfyUI の `custom_nodes/` ディレクトリ内で以下のコマンドを実行してください：

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/treeturtlefall-arch/rec-frame-ComfyUI.git
```

必要な依存ライブラリ（Pillow, PyTorch, torchvision 等）は ComfyUI 本体の環境に含まれているため、追加の `pip install` は不要です。

---

## よくある質問とTips (FAQ)

### Q. 上部のL字枠が下部よりも短く見える気がします。不具合ですか？
**A. 四隅すべてのL字枠は、1ピクセルの狂いもなく完全に同一の長さ（等長）で描画されています。**  
上部には電池マークやREC文字などの横長UI要素が隣接しているため、人間の脳の対比錯視および水平垂直錯視（垂直線の方が長く知覚される錯覚）により横棒が詰まって見えやすくなります。  
もし横棒をもっと長く伸びやかに見せたい場合は、ノードの **`arm_len_ratio`（既定 0.15）を `0.18` 〜 `0.20`** に広げて調整することをおすすめします。

### Q. 好きなフォントやオリジナルのマーク画像を使いたい
**A. 以下の2通りの使い方が可能です。用途に合わせて使い分けてください：**
* **方法A: パス直接入力方式（ComfyUIの再起動不要・即座にお試し）**
  * ノードの `custom_font_path`（フォント）または `custom_dot_path`（画像）に、PC内のファイルフルパスを入力すると、ComfyUIを再起動せずにその場で即時反映されます。
* **方法B: フォルダ配置方式（定番登録・ワークフロー共有に最適）**
  * フォントファイル（`.ttf`/`.otf`/`.ttc`）は本ノードの `fonts/` フォルダへ、マーク画像（透過PNG/WebP）は `assets/dots/` フォルダへ配置してください。
  * ComfyUI を再起動すると、ノードのドロップダウンメニューに自動登録され、いつでもリストから選択できるようになります。

---

## ライセンス & クレジット

- **rec-frame-ComfyUI**: [MIT License](./LICENSE)
- 元リポジトリ: [treeturtlefall-arch/rec-frame-app](https://github.com/treeturtlefall-arch/rec-frame-app)
- **同梱フォント**:
  - Roboto Condensed, Bebas Neue, DSEG7 Classic, Share Tech Mono, VT323, Zen Kaku Gothic: [SIL Open Font License 1.1](./fonts/OFL.txt)
