"""同梱オープンソースフォント（SIL OFL / Apache 2.0）の一括ダウンロード・配置スクリプト。

fonts/ ディレクトリに以下のフォントおよびライセンスを配置し、
外部（C:/Windows/Fonts等）に一切依存しない自己完結環境を構築する。
"""
from __future__ import annotations

import io
import urllib.request
import zipfile
from pathlib import Path

FONTS_DIR = Path(__file__).resolve().parent.parent / "fonts"

GOOGLE_FONTS_BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl"

FONT_DOWNLOADS = {
    "RobotoCondensed-Bold.ttf": f"{GOOGLE_FONTS_BASE}/robotocondensed/RobotoCondensed%5Bwght%5D.ttf",
    "BebasNeue-Regular.ttf": f"{GOOGLE_FONTS_BASE}/bebasneue/BebasNeue-Regular.ttf",
    "ShareTechMono-Regular.ttf": f"{GOOGLE_FONTS_BASE}/sharetechmono/ShareTechMono-Regular.ttf",
    "VT323-Regular.ttf": f"{GOOGLE_FONTS_BASE}/vt323/VT323-Regular.ttf",
    "ZenKakuGothicNew-Bold.ttf": f"{GOOGLE_FONTS_BASE}/zenkakugothicnew/ZenKakuGothicNew-Bold.ttf",
}

DSEG_RELEASE_ZIP = "https://github.com/keshikan/DSEG/releases/download/v0.46/fonts-DSEG_v046.zip"


def download_fonts() -> None:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0"}

    # 1. Google Fonts のダウンロード
    for filename, url in FONT_DOWNLOADS.items():
        dest = FONTS_DIR / filename
        if dest.is_file() and dest.stat().st_size > 0:
            print(f"[Skip] Already exists: {filename}")
            continue
        print(f"[Download] Fetching {filename} ...")
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            dest.write_bytes(data)
            print(f"[OK] Saved {filename} ({len(data):,} bytes)")

    # 2. DSEG7 (7セグLEDフォント) の展開
    dseg_dest = FONTS_DIR / "DSEG7Classic-Bold.ttf"
    if not (dseg_dest.is_file() and dseg_dest.stat().st_size > 0):
        print("[Download] Fetching DSEG release zip ...")
        req = urllib.request.Request(DSEG_RELEASE_ZIP, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            zf = zipfile.ZipFile(io.BytesIO(resp.read()))
            for name in zf.namelist():
                if name.endswith("DSEG7Classic-Bold.ttf"):
                    data = zf.read(name)
                    dseg_dest.write_bytes(data)
                    print(f"[OK] Extracted {dseg_dest.name} ({len(data):,} bytes)")
                elif name.endswith("DSEG-License.txt"):
                    lic_dest = FONTS_DIR / "LICENSE-DSEG.txt"
                    lic_dest.write_bytes(zf.read(name))
                    print(f"[OK] Extracted LICENSE-DSEG.txt")

    # 3. README / ライセンス案内ファイルの作成
    readme_path = FONTS_DIR / "README.md"
    readme_content = """# 同梱フォントについて (Bundled Fonts)

本フォルダ (`fonts/`) に同梱されているフォントはすべて、商用利用・改変・再配布が認められたオープンソースライセンス（SIL Open Font License 1.1 または Apache License 2.0）に基づき提供されています。
OSのシステムフォントに依存せず、すべてのプラットフォームで一貫したレンダリングを自己完結で実現します。

| フォントファイル | スタイル / 用途 | ライセンス | 配布元 / 作者 |
|---|---|---|---|
| `RobotoCondensed-Bold.ttf` | クラシック・ファインダー細長（標準） | SIL OFL 1.1 | Google Fonts / Christian Robertson |
| `BebasNeue-Regular.ttf` | 映画調・縦長大文字 | SIL OFL 1.1 | Google Fonts / Ryoichi Tsunekawa |
| `DSEG7Classic-Bold.ttf` | 7セグメントデジタル液晶・タイムコード | SIL OFL 1.1 | KESHIKE (keshikan) |
| `ShareTechMono-Regular.ttf` | 計測機器・サイバー等幅 | SIL OFL 1.1 | Google Fonts / Carrois Apostrophe |
| `VT323-Regular.ttf` | 2000s レトロ・ドットマトリクス | SIL OFL 1.1 | Google Fonts / Peter Hull |
| `ZenKakuGothicNew-Bold.ttf` | 日本語ゴシック（文字化け防止） | SIL OFL 1.1 | Google Fonts / Yoshimichi Ohira |

## ユーザー自作フォントの追加
このフォルダに `.ttf` / `.otf` / `.ttc` を配置すると、ComfyUI のフォント選択リストに自動的に追加されます。
"""
    readme_path.write_text(readme_content, encoding="utf-8")
    print("[OK] Created fonts/README.md")


if __name__ == "__main__":
    download_fonts()
