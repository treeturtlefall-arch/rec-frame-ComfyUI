<div align="center">

# 🔴 rec-frame-ComfyUI

### Professional Pure-Vector, Illusion-Compensated & Non-Destructive Retro Degradation Camera Viewfinder HUD for ComfyUI

[![Version](https://img.shields.io/badge/version-v1.0.0-ff3333?style=flat-square)](https://github.com/treeturtlefall-arch/rec-frame-ComfyUI/releases)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-Custom_Node-2ea44f?style=flat-square)](https://github.com/comfyanonymous/ComfyUI)
[![Python](https://img.shields.io/badge/python-3.9%2B-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Render Engine](https://img.shields.io/badge/engine-Pure_Vector_%26_Optics-e04000?style=flat-square)](#-3-stage-non-destructive-retro-ui-degradation-pipeline-retro_effect-0-to-6)
[![License: MIT](https://img.shields.io/badge/code-MIT-blue?style=flat-square)](LICENSE)
[![Fonts: OFL 1.1](https://img.shields.io/badge/fonts-SIL_OFL_1.1-8a2be2?style=flat-square)](fonts/LICENSE-OFL.txt)

**[🇺🇸 English](README.md)** | **[🇯🇵 日本語 (Japanese)](README_JA.md)**

[Why Pure-Vector?](#-why-pure-vector--optical-illusion-compensation) •
[Image & Video Architecture](#-dedicated-image--video-separation-architecture) •
[Live Preview](#-no-queue-instant-live-preview-recframepreview) •
[Retro Degradation](#-3-stage-non-destructive-retro-ui-degradation-pipeline-retro_effect-0-to-6) •
[6 Curated Fonts](#-6-curated-open-source-fonts--mark-assets-self-contained) •
[Official Workflows](#-official-workflows-comfyui-desktop-ready) •
[Parameter Specs](#%EF%B8%8F-parameter-specifications)

<br>

![Hero Showcase](./assets/demo/hero_showcase.png)

*Complete liberation from stretched, distorted PNG assets. Pixel-perfect camera viewfinder HUDs powered by short-edge vector math and strict ink-centering geometry.*

</div>

---

## 🔬 Why Pure-Vector & Optical Illusion Compensation?

A camera viewfinder or cinema HUD overlay is **fundamentally broken when implemented as a stretched static PNG graphic**. When changing aspect ratios to vertical video (9:16) or square formats (1:1), corner brackets stretch into uneven thicknesses. Furthermore, varying typographic ascenders and descenders cause text to float off-center, while human contrast illusions make upper L-brackets appear crammed and shortened.

Inherited and evolved from [treeturtlefall-arch/rec-frame-app](https://github.com/treeturtlefall-arch/rec-frame-app), **rec-frame-ComfyUI** combines pure vector geometry scaled to the canvas short edge with cognitive optical illusion engineering to render flawless HUDs across any resolution or aspect ratio:

| Feature & Philosophy | Static PNG Asset Overlay | Standard HUD / Text Nodes | **rec-frame-ComfyUI** |
| :--- | :---: | :---: | :---: |
| **Dynamic Aspect Ratios** | ❌ Distorts line thickness in 9:16 / 1:1 | ⚠️ Requires manual coordinate re-tuning | ✅ **Short-edge relative math (`s = min(w, h)`)** (Zero distortion on any ratio) |
| **Corner Precision** | ❌ Blurs and stretches on non-native resolutions | ⚠️ PIL coordinate bounds cause 1px asymmetry | ✅ **`-1` boundary correction for pixel-perfect equal-length corners** |
| **Glyph & Mark Alignment** | ❌ Text floats vertically due to font metrics | ⚠️ Visual approximation with baseline drift | ✅ **Strict ink-bounds measurement (`_tight_ink_metrics`) & optical clearance** |
| **Video & Frame Timing** | ❌ Text jumps around during blinking | ⚠️ Desynced frame rates and blink intervals | ✅ **External FPS auto-sync + skeleton-locked blinking + SMPTE timecodes** |
| **Preview Workflow** | ❌ Full queue cycle required per tweak (slow) | ❌ Full queue cycle required per tweak | ✅ **Frontend extension for queue-free, real-time dynamic preview** |
| **Retro Texture & Degradation**| ❌ Destructively degrades background imagery | ❌ Naive whole-canvas gaussian blur | ✅ **Non-destructive 3-stage pipeline applied exclusively to the UI layer (0–6)** |
| **Legibility Guarantee** | ❌ Blends and disappears against matching backdrops | ⚠️ Rigid single-color outlines | ✅ **Perceptual luminance auto-inverting backdrop boxes (White/Black)** |

---

### 📐 3 Principles of Uncompromising Pixel Accuracy & Illusion Engineering

1. **Short-Edge Relative Vector Math (`s = min(w, h)`)**:
   - Every single dimension (outer margins, bracket thickness, typography size, indicator dot radii) scales dynamically relative to the canvas short edge $s$. Whether rendering 16:9 cinematic widescreen, 4:3 vintage footage, 1:1 square, or 9:16 vertical TikTok/Reels, proportions and stroke weights remain mathematically consistent.
2. **Pixel-Perfect Equal-Length Corner Brackets (PIL `-1` Inclusive Offset Correction)**:
   - Python Pillow's `ImageDraw.rectangle` treats boundary coordinates as inclusive. Naive implementations result in bottom and right corner brackets that are 1 pixel longer or shorter than the top and left. rec-frame-ComfyUI applies exact `-1` coordinate corrections to guarantee that **all four corner brackets share identical horizontal and vertical pixel lengths down to the sub-pixel boundary**.
3. **Strict Ink-Centering Geometry (`_tight_ink_metrics`)**:
   - Standard text anchors (`anchor="lm"`) introduce vertical baseline floating because fonts include uneven ascenders, descenders, and line-gap metrics. This engine uses `font.getmask2(..., anchor="lt")` to sample the **exact physical ink bounding box**, aligning the optical geometric centerline of the REC text precisely with the center of the recording dot.

---

## 🎬 Dedicated Image & Video Separation Architecture

Static image generation and video generation (AnimateDiff, Wan, MiniMax, CogVideoX, etc.) have radically different performance and architectural requirements. rec-frame-ComfyUI separates them into dedicated, purpose-built nodes for maximum workflow ergonomics and rendering speed.

![Video Playback Demo](./assets/demo/video_playback.gif)

### 1. `RecFrameImageOverlay` (Dedicated Still Image Node)
A streamlined, clean node interface stripped of video-specific parameters (blinking intervals and frame rates).
- Generates the RGBA overlay once and composites across all batch frames simultaneously via `torch.lerp` with zero redundant re-draw overhead.
- When no input image is connected, operates as a **standalone overlay generator** using `empty_width` and `empty_height` (default 1280x720) to output transparent alpha HUDs.

### 2. `RecFrameVideoOverlay` (Dedicated Video & Batch Frame Node)
A high-performance video node fully synchronized with generative model frame rates.
- **External FPS Auto-Sync (`fps` Input Pin)**: Connect the `fps` output from `GetVideoComponents` or video loaders to automatically lock timecode progression and blinking intervals to the true video playback speed (e.g. Wan 16fps, MiniMax 24fps).
- **Skeleton-Locked Blinking (`red_dot_visible`)**: During off-phase frames, the recording dot is hidden while maintaining layout bounds—eliminating visual jitter and locking the REC text and backdrop box securely in place.
- **SMPTE Broadcast Frame Counters (`smpte`)**: Counts frames with broadcast-standard `HH:MM:SS:FF` precision.
- **LRU/FIFO Cache Optimization (`MAX_CACHE_SIZE = 32`)**: Avoids redundant frame redraws while maintaining a strict 32-entry cache ceiling, ensuring near-instant compositing on long clips without memory leaks.

> [!IMPORTANT]
> **Video Pipeline Best Practice: "Overlay Belongs Last"**  
> If your pipeline incorporates **Frame Interpolation (e.g. RIFE, FILM)** or **AI Upscaling (e.g. RealESRGAN, NNLatentUpscale)**, ALWAYS position `RecFrameVideoOverlay` **AFTER** them, immediately before video combining or saving (`CreateVideo` / `SaveVideo`).  
> * **Why?** Frame interpolation algorithms attempt to morph sharp text strokes and blinking lights between frames, creating unsightly visual smearing and altering frame counts that desync timecode timing. Keep HUD overlay compositing as the absolute final step in the pipeline.

---

## ⚡ No-Queue Instant Live Preview (`RecFramePreview`)

Eliminates the frustrating workflow of **pressing "Queue Prompt" and waiting after every single slider adjustment**.

A bundled frontend JavaScript extension (`web/js/rec_frame_preview.js`) monitors connections between overlay nodes and `RecFramePreview`. Whenever you adjust a slider (bracket thickness, typography, colors, indicator toggles, or box opacities), the preview node **updates dynamically and instantaneously inside the ComfyUI canvas** via a lightweight internal preview endpoint.

- **4 Background Modes**: Toggle between Black, White, Neutral Gray, or Transparent Checkerboard.
- **Resolution Scaling**: Switch preview rendering between Full, 1/2, or 1/4 resolution for low-spec hardware.
- **Pipeline Passthrough**: Functions both as an interactive visual inspector and passes the composite `IMAGE` tensor to downstream save nodes.

---

## 📺 3-Stage Non-Destructive Retro UI Degradation Pipeline (`retro_effect: 0 to 6`)

A single intuitive slider **`retro_effect` (0 to 6)** spans the entire spectrum from razor-sharp modern vector displays to nostalgic 2000s consumer digicams and gritty security camera footage.

![Retro Effect Levels](./assets/demo/retro_effect_levels.png)

> [!NOTE]
> **Non-Destructive UI-Only Isolation**:  
> The degradation pipeline is applied **exclusively to the rendered HUD overlay layer (RGBA)** before it is blended onto the background. Your underlying AI generation, character details, and background textures remain 100% untouched and pristine.

### Degradation Intensity Reference

| Level | Style Preset | Visual Texture & Optical Profile | Recommended Context & Aesthetics |
| :---: | :--- | :--- | :--- |
| **`0`** | **OFF (Clean Vector)** | Modern high-precision vector HUD. Zero noise, zero aberration | Modern mirrorless cameras, drone telemetry, sci-fi cyber interfaces |
| **`1`** | **Subtle (Digicam)** | Delicate optical blur mimicking early 2000s LCD viewfinders | Seamlessly embeds into modern AI photographic outputs |
| **`2`** | **Classic (Y2K)** | **Default Preset**. Balanced chromatic aberration and CRT bloom | Authentic 2000s CCD digicam snaps, Y2K retro, lifestyle vlogs |
| **`3`** | **Medium (MiniDV)** | Noticeable optical dispersion and handycam display softening | Late 90s–early 2000s home camcorders, indie found-footage |
| **`4`** | **Heavy (VHS)** | Heavy phosphor bloom and CRT monitor horizontal color drift | Analog horror, retro VHS tapes, broadcast television rips |
| **`5`** | **Extreme (CCTV)** | Gritty, degraded surveillance camera and low-bitrate security feeds | Backrooms, abandoned facility security feeds, post-apocalyptic HUDs |
| **`6`** | **Near Break** | Optical breakdown at the absolute edge of human decipherability | Corrupted black box data, SCP anomalous records, deep space telemetry |

<details>
<summary><b>🧬 Click to expand 3-Stage Non-Destructive Pipeline Architecture</b></summary>

<br>

```text
       [ Pure Vector UI Render Layer (RGBA) ]
                         │
                         ▼
 ┌─────────────────────────────────────────────────┐
 │ Stage 1 — Chromatic Aberration (RGB Shift)      │  Horizontal displacement of Red & Blue
 │          Optical Dispersion Simulation          │  channels emulating budget camera lenses
 └───────────────────────┬─────────────────────────┘
                         │
                         ▼
 ┌─────────────────────────────────────────────────┐
 │ Stage 2 — CRT Phosphor Bloom Glow               │  Luminance-aware surface blur & halo
 │          Surface Halation & Flare               │  (Optimized radii for white and dark themes)
 └───────────────────────┬─────────────────────────┘
                         │
                         ▼
 ┌─────────────────────────────────────────────────┐
 │ Stage 3 — LCD Sub-Sampling (Downsampling)       │  Short-edge nearest-neighbor decimation
 │          Pixel Grid Decimation                  │  reproducing low-res CCD & LCD pixel structures
 └───────────────────────┬─────────────────────────┘
                         │
                         ▼
    [ Fully Degraded Retro UI Overlay Layer (RGBA) ]
                         │
                         ▼  (torch.lerp / alpha_composite)
    [ Pristine, High-Resolution Base Image / Video ]
```

The execution order is strictly locked to **"RGB Shift → Bloom → Downsampling"**. Applying bloom *before* pixel decimation reproduces the characteristic blocky glow bleed seen on vintage low-resolution CCD sensors and analog display panels.

</details>

---

## 🎨 Intelligent Legibility: Color Presets & Perceptual Luminance Backdrop Boxes

Engineered to remain crisp and readable regardless of whether your footage is shot against bright snow or pitch-black darkness.

![Color Presets](./assets/demo/color_presets.png)

### 1. 6 Built-in Color Presets + Arbitrary HEX Support
- Presets: `white` (Studio White), `green` (Night Vision), `cyan` (Cyber Blue), `red` (Alert Red), `yellow` (Caution Amber), `black` (Monochrome Black).
- Enter any standard HEX string (e.g. `#00FF88`) into `custom_color` to override the dropdown with bespoke color palettes.

### 2. Perceptual Luminance Auto-Inverting Backdrop Boxes (`bg_box_opacity`)
Semi-transparent sharp rectangular backdrop boxes behind the battery indicator, REC text, and timecodes dynamically sample the perceived luminance of the chosen UI color:

$$\text{Luminance} = 0.299\,R + 0.587\,G + 0.114\,B$$

- **Light & Neon Themes (White, Green, Cyan, Yellow / Luminance $\ge 60$)**: Automatically renders a **soft black backdrop box** `rgba(0, 0, 0, opacity)`, maintaining contrast over bright skies or white walls.
- **Dark & Monochrome Themes (Black / Luminance $< 60$)**: Automatically renders a **soft white backdrop box** `rgba(255, 255, 255, opacity)`, preventing elements from sinking into dark shadows or night scenes.

---

## 🔤 6 Curated Open-Source Fonts & Mark Assets (Self-Contained)

### Privacy Protection & Deterministic Cross-Platform Rendering
To protect user privacy and ensure 100% deterministic, reproducible outputs across Linux, macOS, and Windows environments, **rec-frame-ComfyUI never scans or accesses OS system font directories (`C:/Windows/Fonts`, etc.)**. All typography is completely self-contained within `fonts/`.

| Font Option (`font_key`) | License | Typographic & Geometric Characteristics | Iconic Application & Aesthetics |
| :--- | :---: | :--- | :--- |
| **`Roboto Condensed Bold(細長)`** | SIL OFL 1.1 | ★ **Default Font**. Clean, modern condensed sans-serif | Modern DSLR/mirrorless viewfinders, clean video HUDs |
| **`Bebas Neue(縦長大文字)`** | SIL OFL 1.1 | Powerful, tall, tightly spaced all-caps display font | Cinematic trailers, movie title cards, promotional video |
| **`DSEG7 Classic(7セグLED)`** | SIL OFL 1.1 | Authentic 7-segment digital display module geometry | Digital LCD chronometers, industrial instruments, lab clocks |
| **`Share Tech Mono(等幅)`** | SIL OFL 1.1 | Technical, clean cyberpunk monospace geometry | Night vision goggles, drone telemetry, space exploration HUDs |
| **`VT323(レトロドット)`** | SIL OFL 1.1 | Authentic 90s/2000s pixel dot-matrix typography | Y2K early digicams, retro handhelds, arcade interfaces |
| **`Zen Kaku Gothic(日本語)`** | SIL OFL 1.1 | High-legibility Japanese Gothic typography | Japanese viewfinder telemetry, warnings (e.g. 録画中, 警告) |

### High-Resolution Indicator Dots (`dot_style`)
Select between mathematical circular geometry (`classic`) or curated 512x512 transparent assets in `assets/dots/`:
- **`flat_*` Series** (`flat_red`, `flat_amber`, `flat_cyan`, `flat_green`, `flat_white`): Sharp, crisp solid indicators.
- **`glow_*` Series** (`glow_red`, `glow_amber`, `glow_cyan`, `glow_green`, `glow_white`): Vibrant anime-style glowing orbs with soft halos.

> [!TIP]
> **Using Custom Fonts & Dot Assets**:
> - **Instant Custom Paths (No Restart Required)**: Point `custom_font_path` to any `.ttf`/`.otf`/`.ttc` font or `custom_dot_path` to any transparent `.png`/`.webp` image to test custom graphics immediately.
> - **Permanent Library Registration**: Drop font files into `fonts/` or images into `assets/dots/` to have them automatically appear in ComfyUI dropdown menus upon server restart.

---

## 📦 Installation

### Method 1: ComfyUI-Manager (Recommended)
1. Open the **Manager** menu inside ComfyUI.
2. Select **Custom Nodes Manager**.
3. Search for `rec-frame` or `REC Frame`.
4. Click **Install** and restart ComfyUI.

### Method 2: Comfy-CLI
```bash
comfy node install rec-frame-comfyui
```

### Method 3: Manual Git Clone
Clone this repository directly into your ComfyUI `custom_nodes/` directory:
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/treeturtlefall-arch/rec-frame-ComfyUI.git
```
*(No additional `pip install` commands are required. Runs natively on ComfyUI's standard PyTorch, Pillow, and torchvision stack.)*

---

## 🚀 Official Workflows (ComfyUI Desktop Ready)

The [`workflows/`](./workflows/) directory includes complete, production-ready workflows in both **English (`_en.json`)** and **Japanese (`_ja.json`)**. They can be opened directly from the ComfyUI Desktop "Workflows" sidebar under the `rec-frame/` folder.

| Workflow Name | File Name | Core Nodes | Key Features & Purpose |
| :--- | :--- | :--- | :--- |
| **① Basic Still Image Workflow** | [`rec_frame_basic_workflow_en.json`](./workflows/rec_frame_basic_workflow_en.json) | `RecFrameImageOverlay`<br>`RecFramePreview` | Standard image loading, HUD customization, live preview, and image saving |
| **② 2000s Digicam Preset** | [`rec_frame_2000s_digicam_workflow_en.json`](./workflows/rec_frame_2000s_digicam_workflow_en.json) | `RecFrameImageOverlay`<br>`RecFramePreview` | `Share Tech Mono` font, `retro_effect: 2`, `STBY` text, 3-bar battery preset |
| **③ Video Animation Batch** | [`rec_frame_video_batch_workflow_en.json`](./workflows/rec_frame_video_batch_workflow_en.json) | `RecFrameVideoOverlay`<br>`RecFramePreview` | Video loading, `fps` auto-sync via `GetVideoComponents`, blinking REC dot, timecode |

### 🔌 Output Slot Capabilities
- **`IMAGE`**: The fully composited image tensor `[B, H, W, C]` with the viewfinder HUD burned in.
- **`overlay_rgba`**: Standalone transparent alpha HUD tensor `[B, H, W, 4]`. Pipe directly into `RecFramePreview` for live inspection or into custom compositing nodes.

---

## ⚙️ Parameter Specifications

### Required Parameters

| Parameter | Type / Options | Default | Description |
| :--- | :--- | :---: | :--- |
| **`color`** | `white`, `black`, `green`, `cyan`, `red`, `yellow` | `white` | Viewfinder theme color preset (frames, battery, text, center cross) |
| **`font_key`** | Dropdown (6 bundled + custom) | `Roboto Condensed Bold(細長)` | Bundled open-source typography or user fonts registered in `fonts/` |
| **`retro_effect`** | `INT` (Slider 0 to 6) | `0` | UI degradation intensity (0: Clean Vector to 6: Near Break) |
| **`show_frame`** | `BOOLEAN` | `True` | Toggle corner L-shaped viewfinder brackets |
| **`thickness`** | `INT` (Slider 0 to 100) | `50` | Bracket stroke thickness (0: hairline ~1px, 50: standard, 100: bold impact) |
| **`show_rec`** | `BOOLEAN` | `True` | Toggle recording indicator block (dot + text) |
| **`dot_style`** | Dropdown (Assets list) | `flat_red` | Mark asset style (`flat_*` solid circle, `glow_*` anime orb, `classic` geometric circle) |
| **`rec_label`** | `STRING` | `"REC"` | Text string next to dot (e.g. `"LIVE"`, `"PLAY"`, `"STBY"`, `"ALERT"`) |
| **`show_battery`** | `BOOLEAN` | `True` | Toggle battery gauge |
| **`battery_bars`** | `INT` (0 to 4) | `4` | Number of battery level bars (0 expresses depleted battery) |
| **`show_cross`** | `BOOLEAN` | `False` | Toggle center crosshairs focus mark |
| **`show_timecode`** | `BOOLEAN` | `False` | Toggle timestamp/timecode display |
| **`timecode_mode`** | `manual`, `now`, `now_sec`, `smpte` | `manual` | Manual text / Current time (min) / Current time (sec `:SS`) / Frame SMPTE (`HH:MM:SS:FF`) |
| **`timecode_text`** | `STRING` | `""` | Timestamp text (`YYYY/MM/DD AM/PM HH:MM[:SS]`, SMPTE `00:00:00:00`, or custom text) |

### Optional & Video Parameters

| Parameter | Type / Range | Default | Description |
| :--- | :--- | :---: | :--- |
| **`images` / `image`** | `IMAGE` | Optional | Input image or video batch. Generates standalone overlay if unconnected |
| **`fps`** | `FLOAT` (Input Pin) | Optional | External frame rate input. Automatically overrides `advance_timecode_fps` and locks to video speed |
| **`custom_color`** | `STRING` | `""` | Direct HEX color override (e.g. `#00FF50`). Highest priority over `color` |
| **`custom_font_path`** | `STRING` | `""` | Direct path to external `.ttf`/`.otf`/`.ttc` font file (works immediately without restart) |
| **`custom_dot_path`** | `STRING` | `""` | Direct path to custom dot/logo `.png`/`.webp` image (works immediately without restart) |
| **`bg_box_opacity`** | `FLOAT` (0.0 to 1.0) | `0.10` | Opacity of semi-transparent backdrop boxes (auto-inverts white/black based on luminance) |
| **`margin_ratio`** | `FLOAT` (0.0 to 0.2) | `0.020` | Outer margin ratio of corner brackets relative to short edge |
| **`arm_len_ratio`** | `FLOAT` (0.01 to 0.5) | `0.15` | Bracket arm length ratio (increase to `0.18`–`0.20` for wider, cinematic brackets) |
| **`blink_red_dot_interval`** | `INT` (Video) | `0` | Blinking frame interval (0: always on; e.g. `12` blinks every 0.5s at 24fps) |
| **`advance_timecode_fps`** | `FLOAT` (Video) | `0.0` | Frame rate for advancing timecode seconds (0.0: static) |
| **`empty_width` / `empty_height`** | `INT` | 1280x720 | Canvas resolution when generating standalone transparent overlays |
| **`empty_frames`** | `INT` (Video) | `24` | Number of frames to generate when running standalone video node |

---

## 💡 Frequently Asked Questions & Tips (FAQ)

### Q. The top corner brackets appear slightly shorter than the bottom ones. Is this a bug?
**A. All four corner brackets are rendered with mathematically identical, pixel-perfect lengths.**  
Because the upper region contains horizontal UI elements (the battery gauge and REC indicator), the human brain experiences a combination of the **contrast illusion** and the **horizontal-vertical illusion** (where vertical lines are perceived as longer than horizontal lines of equal physical length).  
If you prefer a wider, more expansive horizontal look, simply adjust **`arm_len_ratio` (default `0.15`) up to `0.18`–`0.20`**.

### Q. The timecode advances too quickly or slowly in my video.
**A. Check your `fps` connection and pipeline execution order.**
1. **Connect External FPS**: Wire the `fps` output from `GetVideoComponents` or your video loader into the `fps` pin of `RecFrameVideoOverlay`. The node will automatically lock its timecode advance to the exact playback rate of your generative model (e.g. Wan 16fps, MiniMax 24fps).
2. **Check for Frame Interpolation**: If using RIFE or FILM, frame counts increase 2x to 4x. Placing the overlay *before* interpolation will cause timecodes to advance too slowly. Always place the overlay node *after* interpolation, directly before video saving.

### Q. How can I export just the transparent HUD as an image sequence or video?
**A. Leave the `images` (or `image`) input unconnected.**  
When no input is wired, the node automatically switches to standalone overlay generator mode, outputting transparent alpha HUD tensors sized to `empty_width` and `empty_height` (for still images) or `empty_frames` (for video sequences).

---

## 📄 License & Credits

- **rec-frame-ComfyUI**: [MIT License](./LICENSE)
- Original Repository: [treeturtlefall-arch/rec-frame-app](https://github.com/treeturtlefall-arch/rec-frame-app)
- **Bundled Fonts (`fonts/*.ttf`)**:
  - Roboto Condensed, Bebas Neue, DSEG7 Classic, Share Tech Mono, VT323, Zen Kaku Gothic: [SIL Open Font License 1.1](./fonts/LICENSE-OFL.txt)
