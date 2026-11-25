#!/usr/bin/env python3
"""Turn reference photos (and a PDF manual) into a few labelled contact sheets.

  python3 contact_sheet.py INPUT_DIR OUT_DIR [--per-sheet 12] [--tile 360] [--pdf manual.pdf]

Looking at 3 sheets costs far fewer model tokens than opening 30 photos one by one, and every
image you open stays in the conversation for all later steps. Each tile is labelled with its
file name (often a part/view label). Writes OUT_DIR/photos-NN.jpg, OUT_DIR/index.md, and with
--pdf also OUT_DIR/manual-NN.jpg (page sheets) and OUT_DIR/manual.txt (text, if pdftotext exists).
Open a single original photo only when a detail is unreadable on the sheet.
Runs with system Python + Pillow (not Blender's Python).
"""
import argparse
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp"}


def font(size):
    for p in ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def wrap(draw, text, fnt, width):
    lines, line = [], ""
    for ch in text:
        trial = line + ch
        if draw.textlength(trial, font=fnt) > width and line:
            lines.append(line)
            line = ch
        else:
            line = trial
    return (lines + [line])[:2]


def sheets(paths, out_dir, prefix, per_sheet, tile, label=True):
    cols = 4 if per_sheet >= 8 else 2
    rows = math.ceil(per_sheet / cols)
    fnt = font(max(12, tile // 22))
    label_h = (tile // 22 + 4) * 2 + 6 if label else 0
    written = []
    for s in range(0, len(paths), per_sheet):
        chunk = paths[s:s + per_sheet]
        r = math.ceil(len(chunk) / cols)
        sheet = Image.new("RGB", (cols * tile, r * (tile + label_h)), "white")
        draw = ImageDraw.Draw(sheet)
        for i, p in enumerate(chunk):
            im = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
            im.thumbnail((tile - 8, tile - 8))
            x, y = (i % cols) * tile, (i // cols) * (tile + label_h)
            sheet.paste(im, (x + (tile - im.width) // 2, y + (tile - im.height) // 2))
            if label:
                for j, ln in enumerate(wrap(draw, f"{s + i + 1}. {p.stem}", fnt, tile - 8)):
                    draw.text((x + 4, y + tile + 2 + j * (tile // 22 + 4)), ln, fill="black", font=fnt)
        name = out_dir / f"{prefix}-{s // per_sheet + 1:02d}.jpg"
        sheet.save(name, quality=82)
        written.append((name, chunk))
    return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--per-sheet", type=int, default=12)
    ap.add_argument("--tile", type=int, default=360)
    ap.add_argument("--pdf")
    a = ap.parse_args()
    src, out = Path(a.input_dir), Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    photos = sorted(p for p in src.rglob("*") if p.suffix.lower() in EXTS and out not in p.parents)
    index = ["# Contact sheets", ""]
    for name, chunk in sheets(photos, out, "photos", a.per_sheet, a.tile):
        index.append(f"## {name.name}")
        index += [f"- {photos.index(p) + 1}. {p.relative_to(src)}" for p in chunk]
        index.append("")
        print(f"[c3d] wrote {name} ({len(chunk)} photos)")
    if a.pdf and shutil.which("pdftoppm"):
        tmp = Path(tempfile.mkdtemp())
        subprocess.run(["pdftoppm", "-r", "90", "-png", a.pdf, str(tmp / "page")], check=True)
        pages = sorted(tmp.glob("page*.png"))
        for name, chunk in sheets(pages, out, "manual", 4, 760):
            index.append(f"## {name.name}: manual pages {pages.index(chunk[0]) + 1}-{pages.index(chunk[-1]) + 1}")
            print(f"[c3d] wrote {name} ({len(chunk)} pages)")
        shutil.rmtree(tmp)
    if a.pdf and shutil.which("pdftotext"):
        subprocess.run(["pdftotext", "-layout", a.pdf, str(out / "manual.txt")], check=True)
        print(f"[c3d] wrote {out / 'manual.txt'}")
    (out / "index.md").write_text("\n".join(index) + "\n")
    print(f"[c3d] wrote {out / 'index.md'}")


if __name__ == "__main__":
    main()
