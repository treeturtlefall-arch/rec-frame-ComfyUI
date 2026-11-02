"""GUI・ダイアログ・CLI・ComfyUIノードで共有する日英翻訳層。"""
from __future__ import annotations

from typing import Literal

LanguageKey = Literal["ja", "en"]
SUPPORTED_LANGUAGES: tuple[LanguageKey, ...] = ("ja", "en")
DEFAULT_LANGUAGE: LanguageKey = "ja"
LANGUAGE_NAMES: dict[LanguageKey, str] = {"ja": "日本語", "en": "English"}


MESSAGES: dict[str, dict[str, str]] = {
    "ja": {
        "language.label": "Language",
        "thickness.small": "小",
        "thickness.medium": "中",
        "thickness.large": "大",
        "effect.normal": "ノーマル",
        "effect.2000s": "2000sデジカメ風",
        "effect.off": "ノーマル",
        "effect.oled": "ノーマル",
        "color.white": "白",
        "color.black": "黒",
        "color.green": "暗視グリーン",
        "color.cyan": "サイバーHUD",
        "color.red": "警告レッド",
        "color.yellow": "ハザードイエロー",
        "font.validation.missing": "ファイルが見つかりません",
        "font.validation.extension": "対応形式は {extensions} のみです",
        "font.custom_default": "カスタムフォント",
        "font.custom_marker": "カスタム",
    },
    "en": {
        "language.label": "Language",
        "thickness.small": "Small",
        "thickness.medium": "Medium",
        "thickness.large": "Large",
        "effect.normal": "Normal",
        "effect.2000s": "2000s digital camera",
        "effect.off": "Normal",
        "effect.oled": "Normal",
        "color.white": "White",
        "color.black": "Black",
        "color.green": "Night Vision Green",
        "color.cyan": "Cyber HUD Cyan",
        "color.red": "Alert Red",
        "color.yellow": "Hazard Yellow",
        "font.validation.missing": "The file was not found",
        "font.validation.extension": "Supported formats: {extensions}",
        "font.custom_default": "Custom font",
        "font.custom_marker": "Custom",
    },
}


BUILTIN_FONT_LABELS_EN: dict[str, str] = {
    "Arial(標準)": "Arial (Standard)",
    "Arial Narrow Bold(細長)": "Arial Narrow Bold (Condensed)",
    "Arial Black(極太)": "Arial Black (Extra bold)",
    "Impact(凝縮テロップ風)": "Impact (Condensed display)",
    "Bahnschrift(工業的)": "Bahnschrift (Industrial)",
    "Consolas(等幅)": "Consolas (Monospace)",
    "Roboto Condensed": "Roboto Condensed",
    "Montserrat Medium": "Montserrat Medium",
    "Bebas Neue(縦長)": "Bebas Neue (Tall)",
    "OCRB(計測機器風)": "OCRB (Instrument style)",
}


def normalize_language(value: object) -> LanguageKey:
    return value if value in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def tr(language: object, key: str, **values: object) -> str:
    lang = normalize_language(language)
    template = MESSAGES.get(lang, {}).get(key, MESSAGES[DEFAULT_LANGUAGE].get(key, key))
    return template.format(**values) if values else template


def thickness_label(key: str, language: object) -> str:
    return tr(language, f"thickness.{key}")


def effect_label(key: str, language: object) -> str:
    return tr(language, f"effect.{key}")


def color_label(key: str, language: object) -> str:
    return tr(language, f"color.{key}")


def builtin_font_label(key: str, language: object) -> str:
    if normalize_language(language) == "en":
        return BUILTIN_FONT_LABELS_EN.get(key, key)
    return key
