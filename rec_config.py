"""オーバーレイ設定の定義。SPEC.md §3・§10.2 が正本。

ComfyUI カスタムノードおよび設定互換のために共有する薄い設定層。
単体アプリ `%APPDATA%/rec-frame-app/config.json` との互換・カスタムフォント参照も維持する。
"""
from __future__ import annotations

import dataclasses
import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

try:
    from .rec_i18n import DEFAULT_LANGUAGE, LanguageKey, normalize_language, tr
except ImportError:
    from rec_i18n import DEFAULT_LANGUAGE, LanguageKey, normalize_language, tr

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".png", ".jpg", ".jpeg", ".webp", ".bmp"})

OverlayColor = Literal["white", "black", "green", "cyan", "red", "yellow"] | str
ThicknessKey = Literal["small", "medium", "large"]
EffectKey = Literal["normal", "2000s", "off", "oled"]

# カラープリセット定義 (表示名/内部キー: (R, G, B, A))
COLOR_PRESETS: dict[str, tuple[int, int, int, int]] = {
    "white": (255, 255, 255, 255),
    "black": (0, 0, 0, 255),
    "green": (0, 255, 80, 255),    # #00FF50 暗視スコープ・ナイトビジョン
    "cyan": (0, 220, 255, 255),     # #00DCFF 近未来SF・サイバーHUD
    "red": (255, 30, 30, 255),      # #FF1E1E 警報・エマージェンシー
    "yellow": (255, 225, 0, 255),   # #FFE100 ハザード・注意喚起・ミリタリー測距
}

_HEX_COLOR_RE = re.compile(r"^#?([0-9a-fA-F]{3,8})$")


def parse_color_to_rgba(val: Any) -> tuple[int, int, int, int] | None:
    """色指定 (プリセット名 / HEXコード / RGBタプル) を RGBA タプル (0..255) に変換する。"""
    if not val:
        return None
    if isinstance(val, (tuple, list)) and len(val) in (3, 4):
        try:
            r, g, b = [max(0, min(255, int(round(c)))) for c in val[:3]]
            a = max(0, min(255, int(round(val[3])))) if len(val) == 4 else 255
            return (r, g, b, a)
        except (ValueError, TypeError):
            return None
    if not isinstance(val, str):
        return None

    cleaned = val.strip().lower()
    # 1. プリセット名完全一致
    if cleaned in COLOR_PRESETS:
        return COLOR_PRESETS[cleaned]

    # 2. プレフィックス一致 (例: "green (暗視グリーン)" -> "green")
    first_token = cleaned.split()[0].rstrip(",;:")
    if first_token in COLOR_PRESETS:
        return COLOR_PRESETS[first_token]

    # 3. HEXコード (#RGB, #RGBA, #RRGGBB, #RRGGBBAA)
    m = _HEX_COLOR_RE.match(cleaned)
    if m:
        hex_str = m.group(1)
        try:
            if len(hex_str) == 3:  # #RGB
                r = int(hex_str[0] * 2, 16)
                g = int(hex_str[1] * 2, 16)
                b = int(hex_str[2] * 2, 16)
                return (r, g, b, 255)
            elif len(hex_str) == 4:  # #RGBA
                r = int(hex_str[0] * 2, 16)
                g = int(hex_str[1] * 2, 16)
                b = int(hex_str[2] * 2, 16)
                a = int(hex_str[3] * 2, 16)
                return (r, g, b, a)
            elif len(hex_str) == 6:  # #RRGGBB
                r = int(hex_str[0:2], 16)
                g = int(hex_str[2:4], 16)
                b = int(hex_str[4:6], 16)
                return (r, g, b, 255)
            elif len(hex_str) == 8:  # #RRGGBBAA
                r = int(hex_str[0:2], 16)
                g = int(hex_str[2:4], 16)
                b = int(hex_str[4:6], 16)
                a = int(hex_str[6:8], 16)
                return (r, g, b, a)
        except ValueError:
            pass

    return None


# 枠太さの表示名と内部キーの対応 (後方互換用)
THICKNESS_CHOICES: dict[str, ThicknessKey] = {
    "小": "small",
    "中": "medium",
    "大": "large",
}
DEFAULT_THICKNESS: int = 40

# 同梱フォント候補 (表示名: ファイル名)
# rec-frame-ComfyUI/fonts/ ディレクトリ内で自己完結し、OSシステムフォルダには一切依存しない。
BUNDLED_FONT_CHOICES: dict[str, str] = {
    "Roboto Condensed Bold(細長)": "RobotoCondensed-Bold.ttf",
    "Bebas Neue(縦長大文字)": "BebasNeue-Regular.ttf",
    "DSEG7 Classic(7セグLED)": "DSEG7Classic-Bold.ttf",
    "Share Tech Mono(等幅)": "ShareTechMono-Regular.ttf",
    "VT323(レトロドット)": "VT323-Regular.ttf",
    "Zen Kaku Gothic(日本語)": "ZenKakuGothicNew-Bold.ttf",
}
DEFAULT_FONT = "Roboto Condensed Bold(細長)"

# 旧バージョンおよび単体アプリ互換用のレガシーフォントマッピング
# 過去のワークフローで指定されたキーが渡された場合、対応する同梱フォントへ安全にマッピングする。
LEGACY_FONT_CHOICES: dict[str, str] = {
    "Arial(標準)": "RobotoCondensed-Bold.ttf",
    "Arial Narrow Bold(細長)": "RobotoCondensed-Bold.ttf",
    "Arial Black(極太)": "RobotoCondensed-Bold.ttf",
    "Impact(凝縮テロップ風)": "BebasNeue-Regular.ttf",
    "Bahnschrift(工業的)": "ShareTechMono-Regular.ttf",
    "Consolas(等幅)": "ShareTechMono-Regular.ttf",
    "Roboto Condensed": "RobotoCondensed-Bold.ttf",
    "Montserrat Medium": "RobotoCondensed-Bold.ttf",
    "Bebas Neue(縦長)": "BebasNeue-Regular.ttf",
    "OCRB(計測機器風)": "ShareTechMono-Regular.ttf",
}

# 全許容キー辞書 (バリデーション・後方互換用)
FONT_CHOICES: dict[str, str] = {**BUNDLED_FONT_CHOICES, **LEGACY_FONT_CHOICES}

# ファインダーUI劣化エフェクトの選択肢 (表示名: 内部キー、SPEC §3.6)
EFFECT_CHOICES: dict[str, EffectKey] = {
    "ノーマル": "normal",
    "2000sデジカメ風": "2000s",
}
DEFAULT_EFFECT: EffectKey = "normal"
DEFAULT_RETRO_EFFECT: int = 0  # 0(OFF)〜6(極限Break)

CLASSIC_DOT_STYLE: str = "classic (幾何学・真円)"
DEFAULT_DOT_STYLE: str = "flat_red"

CONFIG_SCHEMA_VERSION = 10

# ユーザーが追加できるフォントの拡張子 (SPEC §5)。ttcは先頭フェイス(index=0)を使用。
CUSTOM_FONT_EXTENSIONS: frozenset[str] = frozenset({".ttf", ".otf", ".ttc", ".woff", ".woff2"})
DOT_ASSET_EXTENSIONS: frozenset[str] = frozenset({".png", ".webp", ".jpg", ".jpeg"})


def is_valid_custom_font_path(path_str: str | None) -> bool:
    """カスタムフォントの直接パスが安全かつ有効なフォントファイルか検査する。"""
    if not path_str or not isinstance(path_str, str):
        return False
    try:
        p = Path(path_str.strip().strip('"').strip("'"))
        return p.suffix.lower() in CUSTOM_FONT_EXTENSIONS and p.is_file()
    except (OSError, ValueError):
        return False


def is_valid_dot_asset_path(path_str: str | None) -> bool:
    """マーク素材の直接パスが安全かつ有効な画像ファイルか検査する。"""
    if not path_str or not isinstance(path_str, str):
        return False
    try:
        p = Path(path_str.strip().strip('"').strip("'"))
        return p.suffix.lower() in DOT_ASSET_EXTENSIONS and p.is_file()
    except (OSError, ValueError):
        return False

APP_CONFIG_DIRNAME = "rec-frame-app"
APP_CONFIG_FILENAME = "config.json"


def get_user_config_path() -> Path:
    """単体アプリの自動記憶用JSONの保存先。カスタムフォント設定等の連携に使用。

    - Windows: %APPDATA%/rec-frame-app/config.json
    - その他: $XDG_CONFIG_HOME/rec-frame-app/config.json (既定 ~/.config)
    """
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / APP_CONFIG_DIRNAME / APP_CONFIG_FILENAME
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / APP_CONFIG_DIRNAME / APP_CONFIG_FILENAME


def load_user_config(path: Path | str | None = None) -> "OverlayConfig":
    """保存済み設定を読む。欠落・破損・旧形式は既定値で吸収し例外を出さない。"""
    target = Path(path) if path is not None else get_user_config_path()
    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, NotADirectoryError, OSError, ValueError):
        return OverlayConfig()
    if not isinstance(data, dict):
        return OverlayConfig()
    try:
        return OverlayConfig.from_dict(data)
    except (ValueError, TypeError):
        return OverlayConfig()


def save_user_config(config: "OverlayConfig", path: Path | str | None = None) -> Path | None:
    """設定を自動保存する。書けない環境では None を返し例外を出さない。"""
    target = Path(path) if path is not None else get_user_config_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
        return target
    except OSError:
        return None


def get_user_fonts_dir() -> Path:
    """カスタムフォントのコピー先。設定JSONと同じルート直下の `fonts/`。"""
    return get_user_config_path().parent / "fonts"


def get_local_fonts_dir() -> Path:
    """本カスタムノードリポジトリ直下の `fonts/` フォルダ。"""
    return Path(__file__).resolve().parent / "fonts"


def resolve_bundled_font_path(font_key: str) -> Path | None:
    """同梱フォントの実ファイルパスを解決する。rec-frame-ComfyUI/fonts/ 内のみ探索。"""
    local_dir = get_local_fonts_dir()
    if not local_dir.is_dir():
        return None

    # 1. BUNDLED_FONT_CHOICES の表示名
    filename = BUNDLED_FONT_CHOICES.get(font_key)
    if filename:
        p = local_dir / filename
        if p.is_file():
            return p

    # 2. LEGACY_FONT_CHOICES の旧表示名 (後方互換)
    legacy_file = LEGACY_FONT_CHOICES.get(font_key)
    if legacy_file:
        p = local_dir / legacy_file
        if p.is_file():
            return p

    # 3. fonts/ 直下のファイル名直接指定 (例: "RobotoCondensed-Bold.ttf")
    direct = local_dir / font_key
    if direct.is_file():
        return direct

    # 4. stem 一致
    for ext in CUSTOM_FONT_EXTENSIONS:
        p = local_dir / f"{font_key}{ext}"
        if p.is_file():
            return p

    return None


def discover_custom_fonts(config: "OverlayConfig | None" = None) -> dict[str, str]:
    """利用可能なカスタムフォント辞書 `{表示名: ファイルパス}` を収集する。

    1. 本リポジトリ直下の `fonts/` フォルダ内のユーザー追加フォント (.ttf/.otf/.ttc)
    2. 単体アプリの設定 (`%APPDATA%/rec-frame-app/config.json`) の `custom_fonts`
    3. 引数 `config.custom_fonts` (最優先)
    ※ 同梱フォント (BUNDLED_FONT_CHOICES) は除外される。
    """
    merged: dict[str, str] = {}
    bundled_files = set(BUNDLED_FONT_CHOICES.values())

    local_dir = get_local_fonts_dir()
    if local_dir.is_dir():
        for p in sorted(local_dir.iterdir()):
            if p.is_file() and p.suffix.lower() in CUSTOM_FONT_EXTENSIONS:
                if p.name not in bundled_files:
                    display_name = sanitize_custom_font_name(p.stem, merged)
                    merged[display_name] = str(p)

    user_cfg = load_user_config()
    for name, path_str in user_cfg.custom_fonts.items():
        if name not in FONT_CHOICES and Path(path_str).is_file():
            merged[name] = path_str

    if config is not None and config.custom_fonts:
        for name, path_str in config.custom_fonts.items():
            if name not in FONT_CHOICES:
                merged[name] = path_str

    return merged


def get_dot_assets_dir() -> Path:
    """同梱および自作の丸マーク素材フォルダ (`assets/dots`)。"""
    return Path(__file__).resolve().parent / "assets" / "dots"


def discover_dot_assets() -> dict[str, str]:
    """利用可能なマーク素材 `{表示名/キー: ファイルパス}` を収集する。"""
    assets: dict[str, str] = {}
    dot_dir = get_dot_assets_dir()
    if dot_dir.is_dir():
        for p in sorted(dot_dir.iterdir()):
            if p.is_file() and p.suffix.lower() in (".png", ".webp"):
                assets[p.stem] = str(p)
    return assets


def get_all_dot_styles() -> list[str]:
    """選択肢用リストを返す (flat -> glow -> classic -> その他カスタム の優先順)。"""
    assets = discover_dot_assets()

    flats = [k for k in assets if k.startswith("flat_")]
    if "flat_red" in flats:
        flats.remove("flat_red")
        flats = ["flat_red"] + flats

    glows = [k for k in assets if k.startswith("glow_")]
    if "glow_red" in glows:
        glows.remove("glow_red")
        glows = ["glow_red"] + glows

    others = [k for k in assets if not k.startswith("flat_") and not k.startswith("glow_")]

    return flats + glows + [CLASSIC_DOT_STYLE] + others


def get_system_font_dirs() -> list[Path]:
    """フォント格納先。外部システムフォルダにはアクセスせず fonts/ のみを返す。"""
    local = get_local_fonts_dir()
    return [local] if local.is_dir() else []


def get_font_browse_start_dir() -> Path | None:
    """フォント選択ダイアログの初期フォルダ。"""
    local = get_local_fonts_dir()
    return local if local.is_dir() else None


def is_builtin_font(font_key: str) -> bool:
    """同梱またはレガシーフォントの表示名か。"""
    return font_key in FONT_CHOICES


def get_all_font_names(config: "OverlayConfig | None" = None) -> list[str]:
    """選択肢用。同梱フォント6種を最優先し、次にユーザー追加フォントを並べる。"""
    names = list(BUNDLED_FONT_CHOICES)
    customs = discover_custom_fonts(config)
    for name in customs:
        if name not in names:
            names.append(name)
    if config is not None:
        for name in config.custom_fonts:
            if name not in names:
                names.append(name)
    return names


def resolve_custom_font_path(
    font_key: str, custom_fonts: dict[str, str] | None
) -> Path | None:
    """カスタム名に対応する実ファイル。存在しない・組込名なら None。"""
    if not custom_fonts or font_key in FONT_CHOICES:
        return None
    raw = custom_fonts.get(font_key)
    if not raw:
        return None
    return Path(raw)


def sanitize_custom_font_name(proposed: str, custom_fonts: dict[str, str] | None) -> str:
    """表示名の衝突回避。組込・登録済みと重なったら `名 2` / `名 3` …を付ける。"""
    base = (proposed or "").strip() or "カスタムフォント"
    if base not in FONT_CHOICES and not (custom_fonts and base in custom_fonts):
        return base
    i = 2
    while True:
        candidate = f"{base} {i}"
        if candidate not in FONT_CHOICES and not (custom_fonts and candidate in custom_fonts):
            return candidate
        i += 1


def validate_custom_font_file(
    path: Path | str, language: LanguageKey = DEFAULT_LANGUAGE
) -> str | None:
    """追加前の軽量検査。問題なければ None、あれば理由文を返す。"""
    p = Path(path)
    if not p.exists() or not p.is_file():
        return tr(language, "font.validation.missing")
    if p.suffix.lower() not in CUSTOM_FONT_EXTENSIONS:
        return tr(
            language, "font.validation.extension",
            extensions=sorted(CUSTOM_FONT_EXTENSIONS))
    return None


def is_simple_equivalent(config: "OverlayConfig") -> bool:
    """簡易モードの描画と等価か。mode自体は保存対象外のため起動時推定に使う。"""
    return (
        config.show_frame
        and config.show_battery
        and config.show_rec
        and not config.show_cross
        and not config.show_timecode
        and not config.timecode_from_exif
    )


_TIMECODE_RE = re.compile(
    r"^\s*(\d{1,4})/(\d{1,2})/(\d{1,2})\s+(AM|PM)\s+(\d{1,2}):(\d{1,2})\s*$"
)

_TIMECODE_SEC_RE = re.compile(
    r"^\s*(\d{1,4})/(\d{1,2})/(\d{1,2})\s+(AM|PM)\s+(\d{1,2}):(\d{1,2}):(\d{1,2})\s*$"
)

_SMPTE_RE = re.compile(
    r"^\s*(\d{1,2}):(\d{1,2}):(\d{1,2})[:;](\d{1,2})\s*$"
)

_CLOCK_SEC_RE = re.compile(
    r"^\s*(\d{1,2}):(\d{1,2}):(\d{1,2})\s*$"
)


def compose_timecode_text(year, month, day, ampm, hour, minute) -> str:
    """日時セレクタ値を `YYYY/MM/DD AM/PM HH:MM` に整形する (SPEC §10.3)。"""
    return (f"{int(year):04d}/{int(month):02d}/{int(day):02d} "
            f"{ampm} {int(hour):02d}:{int(minute):02d}")


def parse_timecode_text(text: str) -> tuple[int, int, int, str, int, int] | None:
    """日時文字列をパースする。不正形式は None を返す。compose_timecode_text の逆操作。"""
    m = _TIMECODE_RE.match(text or "")
    if not m:
        return None
    year, month, day, ampm, hour, minute = m.groups()
    try:
        return int(year), int(month), int(day), ampm, int(hour), int(minute)
    except ValueError:
        return None


def parse_timecode_sec_text(text: str) -> tuple[int, int, int, str, int, int, int] | None:
    """秒付き日時文字列 `YYYY/MM/DD AM/PM HH:MM:SS` をパースする。"""
    m = _TIMECODE_SEC_RE.match(text or "")
    if not m:
        return None
    year, month, day, ampm, hour, minute, second = m.groups()
    try:
        return int(year), int(month), int(day), ampm, int(hour), int(minute), int(second)
    except ValueError:
        return None


def parse_smpte_text(text: str) -> tuple[int, int, int, int] | None:
    """SMPTE タイムコード `HH:MM:SS:FF` (またはセミコロン区切り) をパースする。"""
    m = _SMPTE_RE.match(text or "")
    if not m:
        return None
    h, m_val, s, f = m.groups()
    try:
        return int(h), int(m_val), int(s), int(f)
    except ValueError:
        return None


def parse_clock_sec_text(text: str) -> tuple[int, int, int] | None:
    """時刻文字列 `HH:MM:SS` をパースする。"""
    m = _CLOCK_SEC_RE.match(text or "")
    if not m:
        return None
    h, m_val, s = m.groups()
    try:
        return int(h), int(m_val), int(s)
    except ValueError:
        return None


def advance_smpte_timecode(
    start_h: int,
    start_m: int,
    start_s: int,
    start_f: int,
    frame_offset: int,
    fps: float,
) -> str:
    """SMPTE タイムコードを指定フレーム数分進めた文字列 `HH:MM:SS:FF` を生成する。"""
    fps_int = max(1, int(round(fps))) if fps > 0.0 else 24
    total_f = ((start_h * 3600 + start_m * 60 + start_s) * fps_int) + start_f + frame_offset
    total_f = max(0, total_f)
    f = total_f % fps_int
    total_s = total_f // fps_int
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = (total_m // 60) % 100
    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"



@dataclass(frozen=True)
class OverlayConfig:
    """オーバーレイ生成設定。将来の拡張用にスキーマバージョン付き。"""

    color: OverlayColor = "black"
    custom_color: str = ""  # 空文字以外なら最優先で適用される直接HEX/RGB色指定 (#00FF50 等)
    font_key: str = DEFAULT_FONT
    thickness: int | str = DEFAULT_THICKNESS
    show_frame: bool = True
    show_battery: bool = True
    show_rec: bool = True
    show_cross: bool = False
    show_timecode: bool = False
    timecode_text: str = ""
    effect: EffectKey = "normal"
    retro_effect: int = DEFAULT_RETRO_EFFECT  # 0:OFF(クリーン) 〜 6:極限Break
    custom_fonts: dict[str, str] = field(default_factory=dict)
    timecode_from_exif: bool = False
    ui_language: LanguageKey = DEFAULT_LANGUAGE
    # --- ComfyUI カスタム拡張用フィールド (既定値は単体アプリと完全互換) ---
    rec_label: str = "REC"
    show_red_dot: bool = True
    # 点滅の消灯フレーム用。False でも赤丸分のレイアウト (座布団幅・文字位置) は維持し描画のみ省く。
    red_dot_visible: bool = True
    dot_style: str = DEFAULT_DOT_STYLE
    battery_bars: int = 4  # 0〜4
    margin_ratio: float | None = None  # None の場合は MARGIN_RATIO (0.020)
    arm_len_ratio: float | None = None  # None の場合は ARM_LEN_RATIO (0.15)
    bg_box_opacity: float = 0.10  # 0.0〜1.0 (文字・マーク背後の半透明シャープ長方形ボックス)

    def __post_init__(self) -> None:
        if not isinstance(self.custom_color, str):
            raise ValueError(f"custom_color must be str, got {self.custom_color!r}")
        target_color = self.custom_color.strip() if self.custom_color.strip() else self.color
        if parse_color_to_rgba(target_color) is None:
            raise ValueError(
                f"color must be valid preset {list(COLOR_PRESETS.keys())} or HEX string, "
                f"got color={self.color!r}, custom_color={self.custom_color!r}"
            )
        if not isinstance(self.custom_fonts, dict):
            raise ValueError(f"custom_fonts must be dict, got {self.custom_fonts!r}")
        for k, v in self.custom_fonts.items():
            if not isinstance(k, str) or not k.strip():
                raise ValueError(f"custom_fonts keys must be non-empty str, got {k!r}")
            if k in FONT_CHOICES:
                raise ValueError(f"custom_fonts key collides with builtin: {k!r}")
            if not isinstance(v, str) or not v.strip():
                raise ValueError(f"custom_fonts values must be non-empty str, got {v!r}")
        if self.font_key not in FONT_CHOICES and self.font_key not in self.custom_fonts:
            raise ValueError(f"unknown font_key: {self.font_key!r}")
        if isinstance(self.thickness, int):
            if not (0 <= self.thickness <= 100):
                raise ValueError(f"thickness must be int 0..100, got {self.thickness!r}")
        elif self.thickness in ("small", "medium", "large"):
            pass
        else:
            raise ValueError(
                f"thickness must be int 0..100 or 'small'|'medium'|'large', got {self.thickness!r}"
            )
        for key in ("show_frame", "show_battery", "show_rec", "show_cross",
                      "show_timecode", "timecode_from_exif", "show_red_dot",
                      "red_dot_visible"):
            if not isinstance(getattr(self, key), bool):
                raise ValueError(f"{key} must be bool, got {getattr(self, key)!r}")
        if not isinstance(self.timecode_text, str):
            raise ValueError(f"timecode_text must be str, got {self.timecode_text!r}")
        if not isinstance(self.rec_label, str):
            raise ValueError(f"rec_label must be str, got {self.rec_label!r}")
        if not isinstance(self.dot_style, str):
            raise ValueError(f"dot_style must be str, got {self.dot_style!r}")
        if not isinstance(self.battery_bars, int) or not (0 <= self.battery_bars <= 4):
            raise ValueError(f"battery_bars must be int 0..4, got {self.battery_bars!r}")
        if not isinstance(self.bg_box_opacity, (int, float)) or not (0.0 <= float(self.bg_box_opacity) <= 1.0):
            raise ValueError(f"bg_box_opacity must be float 0.0..1.0, got {self.bg_box_opacity!r}")
        if not isinstance(self.retro_effect, int) or not (0 <= self.retro_effect <= 6):
            raise ValueError(f"retro_effect must be int 0..6, got {self.retro_effect!r}")
        if self.effect not in ("normal", "2000s", "off", "oled"):
            raise ValueError(
                f"effect must be 'normal'|'2000s', got {self.effect!r}"
            )
        if self.ui_language not in ("ja", "en"):
            raise ValueError(
                f"ui_language must be 'ja'|'en', got {self.ui_language!r}"
            )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["schema_version"] = CONFIG_SCHEMA_VERSION
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "OverlayConfig":
        kwargs: dict = {}
        for f in dataclasses.fields(cls):
            if f.name in d:
                value = d[f.name]
                if f.name == "custom_fonts":
                    if isinstance(value, dict):
                        cleaned = {
                            k: v for k, v in value.items()
                            if isinstance(k, str) and k.strip()
                            and isinstance(v, str) and v.strip()
                            and k not in FONT_CHOICES
                        }
                        kwargs[f.name] = cleaned
                elif f.name == "ui_language":
                    kwargs[f.name] = normalize_language(value)
                elif f.name == "effect":
                    val = str(value)
                    if val in ("off", "oled"):
                        val = "normal"
                    kwargs[f.name] = val
                else:
                    kwargs[f.name] = value

        # 旧設定辞書の後方互換: retro_effect が無く effect のみ存在する場合の安全変換
        if "retro_effect" not in kwargs:
            legacy_eff = kwargs.get("effect", "normal")
            kwargs["retro_effect"] = 2 if legacy_eff == "2000s" else 0

        return cls(**kwargs)

    def with_custom_font(self, display_name: str, file_path: Path | str) -> "OverlayConfig":
        """カスタムフォントを1件登録し、使用フォントも切替えた新設定を返す。"""
        name = sanitize_custom_font_name(display_name, self.custom_fonts)
        err = validate_custom_font_file(file_path)
        if err is not None:
            raise ValueError(err)
        if name in FONT_CHOICES:
            raise ValueError(f"collides with builtin: {name!r}")
        merged = dict(self.custom_fonts)
        merged[name] = str(Path(file_path))
        return dataclasses.replace(self, custom_fonts=merged, font_key=name)

    def without_custom_font(self, display_name: str) -> "OverlayConfig":
        """カスタム1件を解除する。使っていた場合は既定フォントに戻す。"""
        if display_name in FONT_CHOICES:
            raise ValueError(f"builtin font cannot be removed: {display_name!r}")
        if display_name not in self.custom_fonts:
            raise ValueError(f"unknown custom font: {display_name!r}")
        merged = {k: v for k, v in self.custom_fonts.items() if k != display_name}
        next_key = self.font_key if self.font_key != display_name else DEFAULT_FONT
        return dataclasses.replace(self, custom_fonts=merged, font_key=next_key)
