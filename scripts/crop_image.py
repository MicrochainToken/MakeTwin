#!/usr/bin/env python3
"""Save a zoomed crop of an image to a new file, to open with an image viewer.

  python3 crop_image.py IN.png OUT.png LEFT TOP WIDTH HEIGHT [--scale 2]

Coordinates are in pixels of IN. Never print image data to the terminal to "see" it: the text
costs far more tokens than opening the saved file. Needs Pillow (any Python that has it).
"""
import argparse
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("crop_image.py needs Pillow: pip install pillow, or run it with a Python that has it")

ap = argparse.ArgumentParser()
ap.add_argument("image")
ap.add_argument("out")
ap.add_argument("box", nargs=4, type=int, metavar=("LEFT", "TOP", "WIDTH", "HEIGHT"))
ap.add_argument("--scale", type=float, default=2.0)
a = ap.parse_args()
left, top, width, height = a.box
im = Image.open(a.image).convert("RGB")
crop = im.crop((left, top, left + width, top + height))
if a.scale != 1:
    crop = crop.resize((max(1, round(width * a.scale)), max(1, round(height * a.scale))), Image.LANCZOS)
crop.save(a.out)
print(f"wrote {a.out} ({crop.width}x{crop.height}); open it with your image viewer")
