"""Write small JPEG copies of reference photos (for reviewers: far fewer image tokens per look).

  blender.sh -b --python resize_images.py -- --src PHOTOS_DIR --out OUT_DIR [--max 1024]

Runs inside Blender so it needs no extra Python packages. Each copy keeps the original file name
(with a .jpg extension when the original was something else) and fits within --max pixels.
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from c3d import core  # noqa: E402

A = core.args()
SRC, OUT, LIMIT = A["src"], A["out"], int(A.get("max", 1024))
os.makedirs(OUT, exist_ok=True)
done = 0
for name in sorted(os.listdir(SRC)):
    if os.path.splitext(name)[1].lower() not in (".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"):
        continue
    try:
        img = bpy.data.images.load(os.path.join(SRC, name))
    except RuntimeError as err:
        print(f"[c3d] skipped {name}: {err}")
        continue
    w, h = img.size
    if w and h and max(w, h) > LIMIT:
        k = LIMIT / max(w, h)
        img.scale(max(1, round(w * k)), max(1, round(h * k)))
    stem, ext = os.path.splitext(name)
    target = name if ext.lower() in (".jpg", ".jpeg") else stem + ".jpg"
    img.filepath_raw = os.path.join(OUT, target)
    img.file_format = "JPEG"
    img.save()
    bpy.data.images.remove(img)
    done += 1
print(f"[c3d] wrote {done} small copies to {OUT}")
