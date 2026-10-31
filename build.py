#!/usr/bin/env python3
"""Build the OpenCode Mirror handbook and portable download."""
import argparse
import base64
from pathlib import Path
import re
import shutil
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
FONT_URL = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Newsreader:opsz,wght@6..72,500&family=Plus+Jakarta+Sans:wght@800&display=swap"
APP_FILES = ("mirror.py", "analyze.py", "build.py", "README.md", "agent-setup.md", "FONT_LICENSES.txt")


def refresh_fonts():
    request = urllib.request.Request(FONT_URL, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"})
    with urllib.request.urlopen(request, timeout=30) as response:
        stylesheet = response.read().decode()
    faces = re.findall(r"/\* latin \*/\s*(@font-face\s*\{.*?\})", stylesheet, re.S)
    if not faces:
        raise ValueError("The font service did not return Latin font faces.")
    css = "\n".join(faces)
    for url in dict.fromkeys(re.findall(r"url\((https://[^)]+)\)", css)):
        if not url.startswith("https://fonts.gstatic.com/"):
            raise ValueError("Unexpected font asset host.")
        with urllib.request.urlopen(url, timeout=30) as response:
            data = response.read()
        css = css.replace(url, "data:font/woff2;base64," + base64.b64encode(data).decode())
    if "https://" in css or css.count("@font-face") < 3:
        raise ValueError("Fonts were not embedded completely.")
    (ROOT / "assets/fonts.css").write_text(css + "\n", encoding="utf-8")


def package_files():
    files = [ROOT / name for name in APP_FILES]
    for directory in ("assets", "tests", "handbook"):
        files.extend(path for path in (ROOT / directory).rglob("*")
                     if path.is_file() and "__pycache__" not in path.parts and not path.name.startswith(".") and path.suffix != ".pyc")
    return sorted(files)


def build(out=ROOT / "site"):
    out = Path(out)
    fonts = (ROOT / "assets/fonts.css").read_text(encoding="utf-8")
    if "@font-face" not in fonts or re.search(r"url\([\"']?https?://", fonts):
        raise ValueError("Embedded fonts are required; run build.py --refresh-fonts.")
    out.mkdir(parents=True, exist_ok=True)
    (out / "assets").mkdir(exist_ok=True)
    for name in ("theme.css", "fonts.css"):
        shutil.copyfile(ROOT / "assets" / name, out / "assets" / name)
    shutil.copyfile(ROOT / "handbook/style.css", out / "style.css")
    shutil.copyfile(ROOT / "FONT_LICENSES.txt", out / "FONT_LICENSES.txt")
    shutil.copyfile(ROOT / "agent-setup.md", out / "agent-setup.md")
    index = (ROOT / "handbook/index.html").read_text(encoding="utf-8").replace("../assets/", "assets/").replace("../FONT_LICENSES.txt", "FONT_LICENSES.txt").replace("../agent-setup.md", "agent-setup.md")
    (out / "index.html").write_text(index, encoding="utf-8")
    with zipfile.ZipFile(out / "opencode-mirror.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in package_files():
            info = zipfile.ZipInfo("opencode-mirror/" + str(path.relative_to(ROOT)))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    for link in re.findall(r'(?:href|src)="([^"]+)"', index):
        if not link.startswith(("https://", "http://", "data:", "#")) and not (out / link).is_file():
            raise ValueError(f"Broken handbook link: {link}")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "site")
    parser.add_argument("--refresh-fonts", action="store_true", help="Explicitly download and re-embed the bundled fonts")
    args = parser.parse_args()
    if args.refresh_fonts:
        refresh_fonts()
    print(f"Built: {build(args.out).resolve() / 'index.html'}")


if __name__ == "__main__":
    main()
