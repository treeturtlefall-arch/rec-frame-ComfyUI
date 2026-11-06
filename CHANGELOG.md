# CHANGELOG

`rec-frame-ComfyUI` の更新履歴。
仕様の正本は [`AGENTS.md`](./AGENTS.md) および [`SPEC.md`](./SPEC.md) を参照してください。

---

## [1.1.1] - 2026-11-06

### ドキュメント全面刷新 (Documentation Full Polish)
- **公式ドキュメント（README.md / README_JA.md）のフルブラッシュアップ**:
  - 先行プロジェクト FilmDateStamp の成功フォーマット（中央揃えヘッダー、統一フラットバッジ群、目次ジャンプリンク、キラーフレーズ、アンチテーゼ比較表）を完全適用。
  - **「なぜ幾何学ベクターなのか？（固定PNG枠 vs 一般HUDノード vs rec-frame-ComfyUI）」** の差別化比較表を新設。短辺基準ベクター計算 (s = min(w, h))、PIL -1 inclusive 補正、実インク幾何中心センタリング (_tight_ink_metrics) の優位性を論理的・数学的に解説。
  - **3段階レトロUI劣化パイプラインのアーキテクチャ図解**: 「RGB色収差シフト → CRTブルーム → 低解像度化」の厳密な非破壊適用パイプラインをASCIIアート構造図（<details> 折りたたみ）および段階別詳細表（0: Clean 〜 6: Near Break）として明文化。
  - **同梱6フォントのスペック表拡充**: フォント名、ライセンス、幾何・タイポグラフィ特徴、代表的な用途・モチーフを整理した一覧表を配備。
  - **知覚輝度連動座布団ボックスの数理解説**: 知覚輝度計算式 (Luminance = 0.299R + 0.587G + 0.114B) による白/黒半透明ボックスの自動反転メカニズムを解説。
  - 英語正本（README.md）と日本語版（README_JA.md）の全リンク・画像パス・仕様記述の100%整合性を担保。

---

## [1.1.0] - 2026-11-02

### 外部FPS自動同期 & タイムコード拡張 (Video FPS Sync & SMPTE Timecode)
- **外部 `fps` 入力ソケットの新設 (`RecFrameVideoOverlayNode` / `RecFrameOverlayNode`)**:
  - `forceInput: True` の `fps` 入力ピンを新設（ウィジェット順序21個を一切崩さず100%後方互換を維持）。
  - `GetVideoComponents` や動画生成AIノード（Wan 16fps, MiniMax 24fps, AnimateDiff 8/16fps 等）の FPS 出力を直結することで、ノード内のタイムコード進行と赤丸点滅が動画のネイティブ再生速度に自動完全同期。
- **タイムコード書式の拡張（秒表示 `:SS` ＆ SMPTE `:FF` カウンター対応）**:
  - `timecode_mode` の選択肢を拡充：
    - `now_sec (現在時刻・秒単位)`: `YYYY/MM/DD AM/PM HH:MM:SS` 形式で1秒ごとにカウントアップ。
    - `smpte (フレーム 00:00:00:00)`: 毎フレーム `FF` カウンターが正確にインクリメントし、動画FPSに達すると秒が繰り上がるSMPTE規格のタイムコード進行をサポート。
    - `manual (手入力テキスト)`: 入力テキストから書式（分単位、秒付き、SMPTE `HH:MM:SS:FF`、時刻 `HH:MM:SS`、または固定文字列）を自動判別して適切にカウントアップ。
- **フレームキャッシュ上限とメモリ保護 (`overlay_cache`)**:
  - 毎フレーム変化するタイムコードでも VRAM/RAM が肥大化しないよう、`_render_and_composite` 内の `overlay_cache` に上限（32件）を設け、FIFOで古いフレームオーバーレイを安全に自動回収。
- **公式動画ワークフローの更新 & ベストプラクティス案内**:
  - `GetVideoComponents` の `fps` 出力を `RecFrameVideoOverlay` の `fps` 入力ピンへ自動結線。
  - ガイドNoteおよびドキュメントに **「動画パイプラインの鉄則: オーバーレイは一番最後に配置する（Overlay Belongs Last）」** を明記。フレーム補間（RIFE等）やAIアップスケールの前に配置することによる文字の滲み（smear）やタイムコードのズレを防止する注意喚起を追加。
- **自動テストの拡充**:
  - 外部 `fps` 入力上書きテスト、SMPTEフレーム繰り上がりテスト、秒付き日時進行テスト、キャッシュ上限テスト（計42テスト）を追加し全件パスを確認。

---

## [1.0.0] - 2026-11-02

### ワークフローの日英完全分離 (Official Workflows Bilingual Separation)
- **英語版 (`_en.json`) と 日本語版 (`_ja.json`) の完全分離**:
  - グローバルな ComfyUI ユーザーおよび国内ユーザーの利便性を極限まで高めるため、公式ワークフロー 3 種をそれぞれ英語版（`_en.json`）と日本語版（`_ja.json`）の計 6 ファイルに完全分離。
  - **Note ノードの言語特化**: ワークフロー左端の解説 Note ノードを各言語ネイティブに全面書き下ろし。機能概要・設定項目・リアルタイムプレビュー・出力スロットの意味を完璧に案内。
  - **Group タイトルの純化**: グループ枠のタイトルを各言語専用（EN: `1. Guide & Controls` 等、JA: `1. ガイド` 等）に整備し、余計な混在表記を排除。
  - **ComfyUI 本体同期**: `scripts/create_workflows.py` を更新し、リポジトリ内 `workflows/` および ComfyUI 側 `user/default/workflows/rec-frame/` への自動生成・配置を完備。
  - **自動テスト (`tests/test_workflows.py`)**: 6 ファイルすべての構文、リンク整合性、ウィジェット数を検証する自動テストに更新。

### ドキュメント & グローバル対応 (Documentation & Internationalization)
- **英語メインの公式ドキュメント (README.md) と完全日本語版 (README_JA.md) の併設**:
  - ComfyUI-Manager およびグローバルコミュニティ（利用者の80%以上が英語圏）に向け、README.md を洗練された英語メインに刷新。
  - 冒頭に [🇯🇵 日本語ドキュメント (README_JA.md)](./README_JA.md) 誘導リンクを配置し、日本人ユーザーも1クリックで完全な日本語解説を参照可能に。
  - 最新機能（6色カラープリセット、カスタムHEX指定、
etro_effect 0〜6スライダー、単体オーバーレイ生成、リアルタイムプレビュー、L字枠の錯視メカニズムと rm_len_ratio 調整Tips、自作素材追加FAQ）を両言語に完全反映。
- **公式ビジュアルデモアセットの一括生成 (ssets/demo/ & scripts/generate_demo_assets.py)**:
  - hero_showcase.png (1280x720): 4つの代表的なスタイル（クラシック白枠、2000sレトロY2K、ナイトビジョン、警報アクションHUD）の2x2比較ヒーローバナー。
  - ideo_playback.gif (640x360, 431KB): 実機の1秒周期点滅（0.5秒点灯/0.5秒消灯）と秒進行タイムコードを完全再現した軽量・高品位な動画ループGIF。
  - 
etro_effect_levels.png (1200x520): 
etro_effect スライダー（0: Clean 〜 2: 2000s 〜 6: Near Break）の7段階のUI劣化を横並び比較。
  - color_presets.png (1200x360): 6色プリセットおよび発光グロードット素材・自動輝度反転座布団ボックスの視認性比較。
  - scripts/generate_demo_assets.py を新設し、描画エンジンからワンコマンドで全ビジュアルを決定論的に再生成可能な自動化パイプラインを整備。

### 新機能 (Added) / カラーバリエーション拡張とカスタムHEX指定
- **ファインダーカラーの6色プリセット拡充**:
  - 従来の白・黒（`white` / `black`）の2択から、ミリタリー・SF・警報演出でニーズの高い6色プリセットへ拡張：
    - `white (白)`: 標準・現代ビデオカメラ・デジカメ
    - `black (黒)`: 明所・屋外・雪山向け
    - `green (暗視グリーン)`: 特殊部隊・PVS-14暗視スコープ風 (`#00FF50`)
    - `cyan (サイバーHUD)`: 近未来SF・戦闘機HUD・アニメ義眼カメラ風 (`#00DCFF`)
    - `red (警告レッド)`: 非常事態・ハッキング・警報演出風 (`#FF1E1E`)
    - `yellow (ハザードイエロー)`: 建設重機・ミリタリー測距・Cyberpunk 2077風 (`#FFE100`)
  - ドットマーク透過アセット（`assets/dots/` の `glow_*` / `flat_*`）と完全同期し、全身同色の高品位HUD画面が一発で構築可能に。
- **自由色指定ウィジェット (`custom_color`) の新設**:
  - オプションウィジェットに `custom_color: ""` を追加。
  - `#00FF50`, `#FF007F` (ネオンピンク), `#0F6` などのHEXコード（またはRGBタプル）を指定することで、世界観に合わせた自由な色で枠・文字・電池・十字を描画可能。
  - 不正な色文字列が渡された場合も例外クラッシュせず、安全にプリセットカラーへフォールバックする防御機構を整備。
- **半透明座布団（`bg_box_opacity`）の知覚輝度連動自動反転**:
  - 描画色の知覚輝度（`0.299R + 0.587G + 0.114B`）を計算し、極端に暗い色（黒など輝度 < 60）は白半透明、それ以外の明色・蛍光色は黒半透明を自動適用。
  - 白い壁や明るい背景の上でも文字やマークが一切埋もれずに高いコントラストと視認性を自動確保。
- **ブルーム発光エフェクトのカラー最適化**:
  - 暗色（黒等）以外の明色・ネオン系カラーにおいて、ブルーム適用時に周囲へ鮮烈な光彩オーラ（ネオングロー）が美しく広がるよう処理を協調。

### 新機能 (Added) / 単体透過オーバーレイジェネレーター化
- **入力画像なし時のカスタム解像度・フレーム数指定 (`empty_width`, `empty_height`, `empty_frames`)**:
  - `RecFrameImageOverlay`, `RecFrameVideoOverlay`, `RecFrameOverlay` のオプション引数に `empty_width`（既定 1280, 64〜8192）および `empty_height`（既定 720, 64〜8192）を追加。
  - `RecFrameVideoOverlay` にはさらに `empty_frames`（既定 24, 1〜1024）を追加。
  - **効果**: `image` を接続せずにノード単体で動作させた場合、空画像生成ノード（Empty Image等）を別途接続することなく、任意の解像度（9:16縦長ショート、1:1正方形、4K等）の透過オーバーレイ（`overlay_rgba`）およびマスク（`overlay_mask`）を直接生成可能に。
  - **動画用単体生成**: `RecFrameVideoOverlay` では指定フレーム数（既定24フレーム）の赤丸点滅・タイムコード進行アニメーション付き透過連番枠を一発生成可能。
  - **リアルタイムプレビュー連携**: プレビューAPIエンドポイント（`/rec_frame/preview`）が `empty_width` / `empty_height` に自動連動し、キャンバス上での解像度変更がプレビュー表示へ即座に反映。
  - **100%の後方互換性**: 入力画像が存在する場合は入力解像度が最優先され、既存ワークフローに一切の影響を与えない設計を徹底。

### セキュリティ・堅牢性 (Security & Hardening)
- **外部パス入力のホワイトリスト検証と縮退保護**:
  - `custom_font_path` に対し、許可拡張子（`.ttf`, `.otf`, `.ttc`, `.woff`, `.woff2`）および存在確認を行う `is_valid_custom_font_path` を導入。
  - `custom_dot_path` に対し、許可拡張子（`.png`, `.webp`, `.jpg`, `.jpeg`）および存在確認を行う `is_valid_dot_asset_path` を導入。
  - 非許可拡張子、存在しないファイルパス、ヌルバイトを含む不正パスが入力された場合でも、例外でクラッシュせず警告ログを出力した上で安全にデフォルト（`font_key` / `dot_style`）へフォールバックする防御機構を整備。
  - 破損したフォントや画像が指定された場合も例外で処理が中断しない Graceful Degradation を実装。
- **リアルタイムプレビュー API エンドポイント (`/rec_frame/preview`) の堅牢化**:
  - リクエスト JSON への型ガード（dict 型検証）を追加。
  - 描画および PNG エンコード処理全体を例外保護し、万が一の描画例外時も ComfyUI サーバープロセスを巻き込まず安全なエラーレスポンス（HTTP 500）を返却するよう改修。

### 配布規格・パッケージング (Packaging)
- **PEP 621 / Comfy Registry 規格対応 (`pyproject.toml`)**:
  - `[project]` および `[tool.comfy]` メタデータ（PublisherId, DisplayName, dependencies 等）を完備した `pyproject.toml` を新規作成。
  - `comfy-cli`（`comfy node pack` / `comfy node publish`）および ComfyUI-Manager v2 への登録要件に対応。
- **配布用除外設定 (`.comfyignore`) の追加**:
  - パッケージ配布時にテストコード（`tests/`）、開発スクリプト（`scripts/`）、中間ドキュメント（`doc/`）や開発用画像を除外する `.comfyignore` を配備。

### 変更 (Changed) / エフェクトパラメータの直感的スライダー一本化
- **エフェクト設定の完全一本化 (`retro_effect: 0〜6`)**:
  - 従来の「エフェクト種類ドロップダウン（ノーマル / 2000sデジカメ風）」と「3種の個別オーバーライド（`override_shift_level`, `override_bloom`, `override_pixel_scale`）」という2重構造を撤廃。
  - **`retro_effect` スライダー（0〜6）1本**に集約し、ノードUIを極限までシンプルに刷新。
  - **視認テストに基づく7段階の最適化**:
    - `0`: OFF (完全クリーン・現代ベクター)
    - `1`: 微弱 (Subtle / 現代デジカメ・初期液晶)
    - `2`: 標準 (Classic 2000s / 従来の2000sデジカメ風標準値)
    - `3`: 中 (Medium / ミニDV・トイカメラ)
    - `4`: 強 (Heavy / レトロVHS・ブラウン管)
    - `5`: 超強 (Extreme / 監視カメラ・SFホラー)
    - `6`: 極限Break (Near Break / 人間の視認から見て推測をもとに読める極限境界)
  - 白枠・黒枠の双方で詳細な視認限界テストを実施し、最大値「6」を「推測をもとに日時データが読めるギリギリの極限」として調整。
- **後方互換性の完全担保**:
  - 既存ワークフローから `effect` 文字列（`"normal"` → 0, `"2000s"` → 2）や旧 `override_*` が渡された場合も、内部で安全に自動マッピングしてそのまま動作。
- **公式ワークフローの同期更新**:
  - `rec_frame_basic_workflow.json`: `retro_effect = 0`
  - `rec_frame_2000s_digicam_workflow.json`: `retro_effect = 2`
  - `rec_frame_video_batch_workflow.json`: `retro_effect = 0`
  - `scripts/create_workflows.py` により ComfyUI 本体側のワークフローファイルへも自動反映。

---

## [0.2.0] - 2026-11-01

### 変更 (Changed) / エフェクト断捨離
- **エフェクト種類の断捨離・2種プリセット集約**:
  - UI劣化エフェクトの選択肢を **「`normal (ノーマル)`」** と **「`2000s (2000sデジカメ風)`」** の2種類にスッキリ整理。
  - 従来の「OLED(微発光)」を整理し、普段使いのクリーン表示「ノーマル」と、レトロ特化「2000sデジカメ風」で迷わず直感的に使い分けられるUIに改善。
  - **後方互換性の担保**:
    - 過去のワークフローや保存設定で `off` または `oled` が指定されていた場合も、自動的に安全に `normal` としてフォールバック処理。既存ワークフローが破損・停止することなくそのまま動作。
  - **高度な微調整パラメータ（オプション）の維持（方針A）**:
    - 劇的な効果を得られる詳細オプション（`override_shift_level`, `override_bloom`, `override_pixel_scale`）は高度な調整用としてそのまま維持。プリセットを選んだ上で自分好みの微調整が可能。
  - **公式ワークフローおよびデフォルト値の更新**:
    - `rec_frame_basic_workflow.json`: `normal (ノーマル)` をデフォルトに設定。
    - `rec_frame_2000s_digicam_workflow.json`: `2000s (2000sデジカメ風)` に更新。実機検証に基づく最適パラメータ（`font_key`: `Share Tech Mono(等幅)`, `override_shift_level`: 2, `override_bloom`: `strong (強)`, `override_pixel_scale`: 0.55 等）をプリセット初期値として反映。
    - `rec_frame_video_batch_workflow.json`: `normal (ノーマル)` をデフォルトに設定。
    - `scripts/create_workflows.py` により ComfyUI 本体側のワークフローファイルへも自動同期。
- **`dot_style` 選択肢の重複整理**:
  - ドロップダウン候補で `classic (幾何学・真円)` と `classic` が二重に表示されていた問題を解消し、`classic (幾何学・真円)` の1つに統一。内部処理では旧キー `classic` も引き続き完全互換。

### 追加 (Added)
- **静止画と動画の役割分離ノード (`RecFrameImageOverlayNode` / `RecFrameVideoOverlayNode`)**:
  - **背景・設計思想**: 従来の単一ノードでは静止画生成時にも動画専用パラメータ（点滅間隔、タイムコード進行FPS）が常に表示されUIが煩雑だったため、用途別にノードを分離して直感性と使いやすさを最大化。
  - **画像用ノード `REC Frame (Image)` (`RecFrameImageOverlayNode`)**:
    - 静止画パイプライン特化。動画専用の点滅間隔 (`blink_red_dot_interval`) や進行FPS (`advance_timecode_fps`) を完全に除外。
    - 枠の太さスライダー（0〜100）、フォント、色、電池、REC文字、日時、座布団、エフェクトなど「静止画1枚の設定」だけに集中できるスッキリしたUIを提供。
    - バッチ入力時も1回のみ描画したオーバーレイを全フレームに再利用し、`torch.lerp` による高速一括合成を実行。
  - **動画用ノード `REC Frame (Video)` (`RecFrameVideoOverlayNode`)**:
    - 動画・連続フレームパイプライン（AnimateDiff, MiniMax-H3, SVD, Wan, CogVideoX 等）特化。
    - 画像用の基本デザイン設定に加え、動画専用パラメータ（赤丸点滅周期 `blink_red_dot_interval`、タイムコード自動進行 `advance_timecode_fps`）をグループ化して分かりやすく配置。
    - `(赤丸点灯, タイムコード文字列)` の辞書キャッシュにより、最小限の描画負荷でフレームアニメーションを高速合成。
  - **既存互換性維持**:
    - 従来の統合ノード `RecFrameOverlayNode`（および `RecFrameCustomOverlayNode`）は後方互換ノードとしてそのまま維持。既存の保存済みワークフローもエラーなく継続利用可能。
  - **公式ワークフロー 3種の刷新**:
    - `workflows/rec_frame_basic_workflow.json`: 静止画基本合成ワークフローに画像専用ノード `RecFrameImageOverlay` ＋ 直下に `Preview REC Overlay` を配置。
    - `workflows/rec_frame_2000s_digicam_workflow.json`: 2000s レトロデジカメ風プリセットに `RecFrameImageOverlay` ＋ 直下に `Preview REC Overlay` を配置。
    - `workflows/rec_frame_video_batch_workflow.json`: 動画バッチアニメーションワークフローに動画専用ノード `RecFrameVideoOverlay` ＋ 直下に `Preview REC Overlay` を配置。
    - 各ノードのウィジェット変更を検知して Queue 不要でダイナミックに枠デザインを確認可能。ComfyUI 本体 (`user/default/workflows/rec-frame/`) にも自動同期インストール。
- **プレビュー専用ノード `Preview REC Overlay` (`RecFramePreviewNode`)**:
  - `RecFrameImageOverlay` / `RecFrameVideoOverlay` / `RecFrameOverlay` の `overlay_rgba` 端子と接続し、ノード内でフレームの仕上がりをリアルタイム画像プレビュー表示（`OUTPUT_NODE = True`）。
  - **背景色の切り替え**: `black (黒)`, `white (白)`, `gray (グレー)`, `checker (透過市松)` の4種から選択可能。白枠・黒枠のどちらでも見やすい背景を即座に選べる。
  - **解像度・アスペクト比選択**: `1280x720 (16:9 HD)`, `1920x1080 (16:9 FHD)`, `1024x1024 (1:1)`, `720x1280 (9:16 縦動画)`。
  - 後続ノードへの `IMAGE` パイプライン出力端子も保持。
- **Queue 不要のリアルタイム追従機能 (フロントエンド拡張 + API)**:
  - `web/js/rec_frame_preview.js`: 各種 REC オーバーレイノードと `RecFramePreview` 間の接続を検知し、ウィジェット変更（`show_frame` の ON/OFF、`thickness` スライダー、フォント、色、エフェクト等）を監視。
  - パラメータを変更した瞬間に、Queue Prompt ボタンを押さなくてもプレビュー画像がダイナミックに即時更新される（デバウンス付き）。
  - バックエンド側に高速プレビュー生成エンドポイント (`POST /rec_frame/preview`) を追加。
- **入力画像未接続（単体動作）対応**:
  - `image` / `images` 入力を `optional` に対応。画像生成前や画像ノード未接続の段階でも、デフォルト解像度（1280x720）の黒背景で単体実行・プレビューが可能に。

### 変更 (Changed) / 初期設定チューニング
- **基本ワークフロー (`rec_frame_basic_workflow.json`) のシンプル化・ショーケース最適化**:
  - セクション5（「5. 透過オーバーレイ & マスク」ノード群: RGBA保存・マスク変換・各プレビュー）を削除し、デジカメ風ワークフローや動画ワークフローと同様に「1. ガイド」「2. 入力画像」「3. 枠合成 & リアルタイムプレビュー」「4. 完成画像出力」の4セクション完結に統一。
  - ショーケースとして直感的に理解しやすく、実行時に余計な透過PNGファイルが output ディレクトリに保存されないクリーンな設計に改善。
  - Note（ガイド）の記述を更新し、通常は一番上の `image` 出力を使いつつ、外部ソフト連携等で必要な場合は `overlay_rgba` や `overlay_mask` も取り出せる旨の案内文に整理。
- **動画用ノード (`RecFrameVideoOverlay`) のUIウィジェット順序改善**:
  - `blink_red_dot_interval`（赤丸点滅周期）と `advance_timecode_fps`（タイムコード進行FPS）の配置位置を、`custom_dot_path` の直下に移動。UIのグルーピングが整理され、画像・デザイン系ウィジェットと動画専用パラメータが視覚的に自然な並び順に改善。
- **動画用ノード (`RecFrameVideoOverlay`) および公式動画ワークフローのデフォルト値刷新**:
  - 実機検証に基づく最適なデフォルト設定を標準化：
    - `color`: `white (白)`
    - `font_key`: `Share Tech Mono(等幅)`（計器・ファインダー調のスタイリッシュな等幅フォント）
    - `battery_bars`: `3`（リアルな残量演出）
    - `show_timecode`: `True` / `timecode_mode`: `now (現在時刻を自動取得)`
    - `blink_red_dot_interval`: `24`（24fps設定時、ちょうど1秒ごとに点滅する自然なテンポ）
    - `advance_timecode_fps`: `24.0`
    - `margin_ratio`: `0.020` / `arm_len_ratio`: `0.15`
    - `bg_box_opacity`: `0.0`（座布団なしでスッキリとしたクリーン表示）
- **ユーザー体験に最適化したゴールデン初期設定への刷新**:
  - `dot_style`: `flat_red`（高品位フラット赤丸素材を標準採用）
  - `margin_ratio`: `0.020`（端距離を画面短辺の2%に引き締め、より引き締まった現代的ファインダー枠レイアウトへ）
  - `arm_len_ratio`: `0.15`（L字枠の一辺比率を短辺の15%に設定し、UI要素とのバランスを最適化）
  - `thickness`: `40`（四隅L字枠の太さを従来の中太50からシャープで洗練された40へ調整）
  - `bg_box_opacity`: `0.10`（文字・マーク背後に自然な薄い座布団を初期適用し、どんな背景でも文字が埋もれず視認性を確保）
- **`dot_style` の後方互換性拡張**: `classic (幾何学・真円)` に加えて `"classic"` キーも選択肢リストに含め、旧ワークフロー読み込み時やAPI呼び出し時のバリデーションエラーを防止。

### 修正 (Fixed)
- **リアルタイムプレビュー API (`render_overlay_preview_pil`) の合成精度改善**:
  - `bg_img.paste(overlay_pil, (0, 0), overlay_pil)` では RGBA オーバーレイの半透明ピクセル（半透明座布団・ブルーム発光・光球外周グロー）に対してアルファが二重に掛かって薄くなっていた問題を解消し、`Image.alpha_composite` による正確な over 合成へ統一。これによりQueue不要のリアルタイムプレビューと実行時の Tensor 合成結果が完全に一致。
- **パラメータ型変換の堅牢化と Tensor 一括ブロードキャスト最適化**:
  - フロントエンド JS や API 経由で数値ウィジェットに float（例: `2.0`）、数値文字列、または `None` が渡された場合でも例外やフォールバックを起こさず安全に正規化（`battery_bars`, `margin_ratio`, `arm_len_ratio`, `bg_box_opacity`, `blink_red_dot_interval`, `advance_timecode_fps`）。
  - 静止画ノードおよび `RecFramePreviewNode` でのバッチ合成を Python ループから PyTorch ブロードキャスト（`torch.lerp` 4次元一括計算）に最適化。
  - フロントエンド拡張（`web/js/rec_frame_preview.js`）において、ComfyUI 新旧フロントエンドの `app.graph.links`（Array / Map 両対応）、ワークフロー読込時（`onConfigure`）の自動プレビュー復元、および `URL.createObjectURL` のメモリリーク解放（`revokeObjectURL`）を追加。
- **動画バッチ実行時の `Preview REC Overlay` モザイク・タイルグリッド化の修正**:
  - 動画生成パイプライン実行時、数百フレームの全画像がプレビューUIに返されていたため、ComfyUI標準の画像タイル表示機能により大量のサムネイルがモザイク状に敷き詰められていた現象を解消。
  - 枠デザイン確認用プレビューとしては先頭1フレームのみを画像化して返すよう最適化（余分なディスクI/Oとメモリ消費も大幅削減）。後続ノードへの全フレームTensorパイプライン出力はそのまま維持。
- **動画ワークフロー (`rec_frame_video_batch_workflow.json`) の動画入出力対応**:
  - 従来の動画ワークフローが静止画用の `LoadImage` / `SaveImage` になっていたため、動画ファイル（MP4/WEBM等）を直接指定できない状態だった問題を解消。
  - ComfyUI 公式の動画パイプライン（`Load Video` → `Get Video Components` → `RecFrameVideoOverlay` → `Create Video` → `Save Video`）に刷新。動画ファイルをドラッグ＆ドロップまたはファイル選択して実行するだけで、音声やフレームレートを維持したままREC枠合成動画を書き出し可能に改修。
- **`custom_dot_path` が機能していなかった不具合**: パスを指定しても素材キー検索 (`assets/dots/` の stem) にしか照合されず、常に赤い幾何円へフォールバックしていた。`rec_overlay._resolve_dot_asset_path()` で素材キー → 画像ファイル直接パスの順に解決するよう修正。存在しないパスは警告ログを出して `dot_style` の選択にフォールバック。
- **短辺 約94〜133px の画像でノードがクラッシュする不具合**: 電池残量バーの内高不足で `ImageDraw.rectangle` が `ValueError (y1 must be greater than or equal to y0)` を送出していた。内高チェックを追加。
- **手入力日付の 29〜31 日が 28 日に丸められる不具合** (`advance_timecode_fps` 使用時): 月末日は `calendar.monthrange` で判定し、実在しない日付 (例: 2/31) のみ月末に丸める。
- **日時として解釈できない手入力テキストが現在時刻に置き換わる不具合** (`advance_timecode_fps` 使用時): 自由文字列は進行対象外とし入力どおり固定表示。
- **エフェクト個別オーバーライドの関数内相対 import**: パッケージ外読込 (テスト等) で `ImportError` になっていたため、`EFFECT_PRESETS` をモジュール先頭で import。
- **赤丸点滅時の REC 文字・座布団のガタつき**: 消灯フレームで赤丸分の幅/高さが消えレイアウトが再計算されていた。`OverlayConfig.red_dot_visible` を追加し、消灯時もレイアウトを維持して描画のみ省略。
- **マーク素材の合成方法**: `paste(mask)` では座布団ボックス上でαが補間され薄くなるため、`alpha_composite` による正しい over 合成へ変更。
- 数値文字列の `thickness` (例: `"50"`) で `ValueError` になっていた問題を修正。存在しない `custom_font_path` は警告ログを出して `font_key` にフォールバック。

### 変更 (Changed) / 最適化
- **合成処理を PyTorch Tensor 上で実行**: フレーム毎の Tensor → PIL → Tensor 往復を廃止し、`torch.lerp` によるストレートα over 合成に変更。入力画像の 8bit 量子化による精度劣化も解消 (PIL 合成との差は ±1/255 以内)。入力のデバイス (CPU/GPU) をそのまま使用。1280x720・56 フレームで 約1.55s → 約0.28s。
- **オーバーレイのキャッシュを辞書化**: 直前フレームとの比較のみだったキャッシュを `(赤丸点灯, タイムコード文字列)` キーの辞書に変更。点滅時も描画は 2 回のみ。
- グレースケール (1ch) 入力に対応。
- `tests/test_comfy_nodes.py` に回帰テスト `TestRefactorRegressions` (11 件) を追加。

### 追加 (Added)
- **ComfyUI Desktop 向け公式ワークフロー 3種を同梱**:
  - `workflows/rec_frame_basic_workflow.json` — 静止画向け基本合成ワークフロー。合成結果プレビュー、背景透明なUI単体出力 (`overlay_rgba`)、不透明度マスク (`overlay_mask`) の確認ノードおよび詳細な日本語ガイド Note を完備。
  - `workflows/rec_frame_2000s_digicam_workflow.json` — 2000年代コンデジ・液晶ファインダー再現プリセット（VT323レトロドット、2000sエフェクト、中央AF十字、バッテリー2本、ノスタルジック日時手入力）。
  - `workflows/rec_frame_video_batch_workflow.json` — MiniMax-H3 / Wan などの動画パイプライン向けアニメーションワークフロー（24fps・0.5秒おきの赤丸REC点滅、1秒刻みのリアルタイムコード進行カウントアップ）。
  - `scripts/create_workflows.py` — ワークフロー JSON の自動生成スクリプト。ComfyUI 本体 (`user/default/workflows/rec-frame/`) へも直接同期インストール。
  - `tests/test_workflows.py` — 生成されたワークフロー JSON の構文・リンク整合性・ウィジェット適合性を検証する自動テスト。
- **文字・マーク背後の半透明座布団ボックス (`bg_box_opacity`)**:
  - 白飛び背景や暗い背景、複雑なディテールの映像上でも抜群の視認性を確保する「シャープ長方形（Rect）座布団」機能を追加。
  - 左上（電池マーク）、右上（赤丸＋REC文字）、右下（日時タイムコード）の全3要素に統一ルールで座布団ボックスを適用。
  - **自動反転色**: 白枠（`color="white"`）時は黒半透明 `rgba(0, 0, 0, alpha)`、黒枠（`color="black"`）時は白半透明 `rgba(255, 255, 255, alpha)` を敷くことで、あらゆる明暗のシーンで文字が埋もれない。
  - **L字枠クリアランス自動確保**: 枠の太さ（`thickness: 0〜100`）にかかわらず、L字枠の縦線・横線の内側から一定の余白比率（`BOX_CLEARANCE_X_RATIO = 0.012`, `BOX_CLEARANCE_Y_RATIO = 0.010`）を自動維持し、枠との接触・干渉を完全に防止。
  - **フォント実描画インクの厳密センタリング (`_tight_ink_metrics`)**:
    - `font.getmask2(..., anchor="lt")` を利用し、フォント固有のアセンダ・ディセンダ余白やサイドベアリングに影響されず、実描画インクの幾何中心をボックスおよび赤丸の中心線 `cy` にピクセル単位で完全一致させる描画パイプラインへ改善。
  - **完全な後方互換性**: `bg_box_opacity: float = 0.0`（0.0〜1.0、step 0.05、デフォルト 0.0 で完全OFF）として `OverlayConfig`（スキーマバージョン 9）およびノードの optional 入力に追加。既存ワークフローの出力には影響ゼロ。
  - `tests/test_comfy_nodes.py` に `test_bg_box_opacity`（座布団描画、白枠・黒枠の反転色検証、ノード実行検証）を追加。
- **フォント自己完結化・オープンソースフォント（SIL OFL 1.1）同梱**:
  - すべて `rec-frame-ComfyUI/fonts/` 内で自己完結し、OSのシステムフォルダに一切依存しない設計へ刷新。
  - ファインダー・タイムコード用途に最適化したオープンソースフォント（商用・再配布フリー）6種を標準同梱：
    1. `Roboto Condensed Bold(細長)` (`RobotoCondensed-Bold.ttf`) - デフォルト・標準ファインダー
    2. `Bebas Neue(縦長大文字)` (`BebasNeue-Regular.ttf`) - 映画・タイトル調
    3. `DSEG7 Classic(7セグLED)` (`DSEG7Classic-Bold.ttf`) - 液晶デジタルタイムコード
    4. `Share Tech Mono(等幅)` (`ShareTechMono-Regular.ttf`) - 計測機器・サイバー等幅
    5. `VT323(レトロドット)` (`VT323-Regular.ttf`) - 2000s レトロビットマップ
    6. `Zen Kaku Gothic(日本語)` (`ZenKakuGothicNew-Bold.ttf`) - 日本語対応ゴシック
  - 各フォントのライセンス案内（[`fonts/README.md`](./fonts/README.md)・[`fonts/LICENSE-OFL.txt`](./fonts/LICENSE-OFL.txt)・[`fonts/LICENSE-DSEG.txt`](./fonts/LICENSE-DSEG.txt)）を同梱。
  - 同梱フォント一括再取得スクリプト [`scripts/download_builtin_fonts.py`](./scripts/download_builtin_fonts.py) を追加。
  - 過去の旧キー（`Arial Narrow Bold(細長)` など）が入力された場合も、対応する同梱フォントへ安全に自動マッピングする後方互換層を実装。
  - ユーザー自作フォントは `fonts/` に配置するだけでドロップダウンに自動登録される機能を維持。
  - 日本語文字列（「録画中」や年月日表記等）が正しく描画できる自動テストを追加。
- **RECマークのスタイル切り替え・透過素材アセット対応 (`dot_style`)**:
  - **表示優先順**: `flat_*`（発光なし真円素材、デフォルト `flat_red`）→ `glow_*`（セルアニメ調発光光球）→ `classic (幾何学・真円)`（コード描画）→ その他カスタム自作アセット。
  - `flat_*`（発光ゼロの純色フラット真円アセット）: `flat_red` (純色 #FF0000), `flat_green`, `flat_amber`, `flat_cyan`, `flat_white`。
  - `glow_*`（セルアニメ調発光光球アセット）: `glow_red`, `glow_green`, `glow_amber`, `glow_cyan`, `glow_white`。
  - **自動探索＆自作マーク対応**: `assets/dots/` フォルダに置いた透過PNG/WebPが自動でドロップダウン一覧に登録。
  - **直接ファイル指定 (`custom_dot_path`)**: optional 引数で任意の画像ファイルを直接指定可能。
  - **中心アライメントの維持**: どんな素材画像でも、文字のインク中央 `cy` にピタリと中心が揃うよう自動計算してリサイズ・アルファ合成。
  - 高精度リサイズ結果の LRU キャッシュ（`_load_and_resize_dot_asset`）によるバッチ処理時の高速化。
  - `tests/test_comfy_nodes.py` に `test_dot_style_assets` を追加。
  - 多様な実画像で瞬時比較できるインタラクティブA/BテストHTMLビューア（`tests/preview_gallery/index.html`）を生成。

### 変更 (Changed)
- **フォント探索仕様の脱システム依存化**:
  - `rec_overlay.py` および `rec_config.py` から `C:/Windows/Fonts/` への固定アクセスコードを完全に除去。
  - デフォルトフォントを従来の `Arial Narrow Bold(細長)` から、自己完結同梱の `Roboto Condensed Bold(細長)` に変更。
  - ドロップダウン選択肢（`get_all_font_names`）の表示順を整理し、同梱フォント6種を最優先で表示。
- **ノードの一本化・UIパラメータ整流化**:
  - 初心者用・拡張用に分かれていたノード構成を見直し、**`RecFrameOverlay`（`REC Frame Overlay (ファインダー枠合成)`）** 1本に統合。
  - **論理的なパーツ別グルーピング**:
    1. 入力画像 (`image`)
    2. 全体共通テーマ (`color`, `font_key`, `effect`)
    3. 四隅枠 (`show_frame`, `thickness`)
    4. 録画インジケーター (`show_rec`, `dot_style`, `rec_label`)
    5. 電池マーク (`show_battery`, `battery_bars`)
    6. 中央十字 (`show_cross`)
    7. タイムコード (`show_timecode`, `timecode_mode`, `timecode_text`)
    8. 詳細・動画向け調整 (`optional`: 各種マージン比率、点滅・進行FPS、エフェクト上書き等)
  - 「パーツの表示/非表示 (true/false) を先頭にし、直下に関連パラメータを配置する」直感的なUI順序に統一。
  - 既存ワークフロー互換のため、`RecFrameCustomOverlay` は `RecFrameOverlay` へのエイリアスとして維持。
- **枠太さの無段階スライダー化 (`thickness`)**:
  - 従来の3択（小/中/大）から、**0〜100 の無段階スライダー（INT, default 50）** に変更。
  - 入力画像の解像度差（SD1.5, SDXL/Flux, 2K/4Kアップスケール等）に完全追従する **「短辺比例スケール（区分線形補間）」** を採用。
    - `0`: 比率 `0.0010`（短辺1000pxで約1pxの極細線）
    - `50`: 比率 `0.0080`（従来の「中」と完全同一）
    - `100`: 比率 `0.0200`（短辺1000pxで約20pxの極太インパクト枠）
    - 最低保証: `max(1, ...)` により極小画像でも線が消えないよう1pxを保証。
- **ドキュメント運用方針の整備**:
  - 更新履歴は本ファイル（`CHANGELOG.md`）、現在のアーキテクチャ・設計仕様は `AGENTS.md` に集約する棲み分けルールを確立。

---

## [1.0.0] - 2026-10-31

### 追加 (Added)
- 単体アプリ `rec-frame-app` の描画エンジンを移植した ComfyUI 向けカスタムノードパッケージの初回リリース。
- PyTorch Tensor (`[B, H, W, C]`, float32 0..1) と PIL の高速相互変換層。
- 透過オーバーレイ単体出力 (`overlay_rgba`) およびアルファマスク出力 (`overlay_mask`)。
- 動画フレーム列（MiniMax-H3等）向けギミック:
  - 赤丸REC点滅 (`blink_red_dot_interval`)
  - フレーム経過に伴うタイムコード進行 (`advance_timecode_fps`)
  - 同一描画フレームのキャッシュ最適化（GaussianBlur / RGBシフト負荷の最小化）
- ファインダーUI劣化エフェクト（OLED微発光、2000sデジカメ）の非破壊適用および個別パラメータ上書き機能。
- 日時自動取得モード (`timecode_mode="now"`)。
- ComfyUI Python環境での単体自動テストスイート (`tests/test_comfy_nodes.py`)。
