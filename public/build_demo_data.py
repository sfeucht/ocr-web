#!/usr/bin/env python3
"""Build src/demo_data.js (the data for the interactive demo in index.html)
out of the big public_demo.html export.

To change which examples appear on the website, edit the config block below
and re-run:  python3 src/build_demo_data.py
"""
import json
import os
import sys

# ---------------------------------------------------------------- config --
SOURCE = "src/public_demo.html"
OUTPUT = "src/demo_data.js"

# Models to show, in tab order. Must match keys in the source export.
KEEP_MODELS = [
    "Qwen3-VL-2B-Instruct",
    "Qwen3-VL-8B-Instruct",
    "llava-v1.6-34b-hf",
    "Molmo2-O-7B",
]

# Images to show, in tab order, as {filename: display label}.
# All 11 images from the export are listed; comment out the ones you don't
# want on the website and re-run this script. Fewer images = smaller
# demo_data.js = faster page load.
KEEP_IMAGES = {
    "pathway.png": "\"PATHWAY ENDS\" sign",
    "COCO_val2014_000000019036.jpg": "Pizza kitchen",
    # "COCO_val2014_000000022929.jpg": "Baby and teddy bear",
    "COCO_val2014_000000035594.jpg": "Elephants",
    # "COCO_val2014_000000039671.jpg": "Sven & Ole's sign",
    # "COCO_val2014_000000305480.jpg": "TAM airplane",
    "COCO_val2014_000000359540.jpg": "Baseball batter",
    # "COCO_val2014_000000401926.jpg": "Boy in pinstripe suit",
    "COCO_val2014_000000493610.jpg": "Crowded truck",
    # "COCO_val2014_000000549560.jpg": "Crosswalk barriers",
    # "COCO_val2014_000000573853.jpg": "Pesto pizza",
}

# Which patch is selected when an image first loads, as exact (row, col)
# coordinates in that model's own patch grid. Grid sizes differ per model AND
# per image, so each combination is listed separately; the comment after each
# line is that combination's grid size (rows x cols).
#
# Anything missing or set to None falls back to the center of the grid.
# Two ways to find coordinates: open the demo with your browser console
# visible and click a patch (it logs model, grid size, row and col), or run
#     python3 src/build_demo_data.py --patch-template
# to print this whole table pre-filled with centers and correct grid sizes
# (useful after you add or remove an image).
DEFAULT_PATCHES = {
    "Qwen3-VL-2B-Instruct": {
        "pathway.png": (1, 3),                           # "PATHWAY ENDS" sign, grid 16x21
        "COCO_val2014_000000019036.jpg": (6, 10),         # Pizza kitchen, grid 13x20
        "COCO_val2014_000000035594.jpg": (7, 10),         # Elephants, grid 15x20
        "COCO_val2014_000000359540.jpg": (6, 10),         # Baseball batter, grid 13x20
        "COCO_val2014_000000493610.jpg": (6, 8),          # Crowded truck, grid 12x16
    },
    "Qwen3-VL-8B-Instruct": {
        "pathway.png": (8, 10),                           # "PATHWAY ENDS" sign, grid 16x21
        "COCO_val2014_000000019036.jpg": (6, 10),         # Pizza kitchen, grid 13x20
        "COCO_val2014_000000035594.jpg": (7, 10),         # Elephants, grid 15x20
        "COCO_val2014_000000359540.jpg": (6, 10),         # Baseball batter, grid 13x20
        "COCO_val2014_000000493610.jpg": (6, 8),          # Crowded truck, grid 12x16
    },
    "llava-v1.6-34b-hf": {
        "pathway.png": (12, 12),                          # "PATHWAY ENDS" sign, grid 24x24
        "COCO_val2014_000000019036.jpg": (12, 12),        # Pizza kitchen, grid 24x24
        "COCO_val2014_000000035594.jpg": (12, 12),        # Elephants, grid 24x24
        "COCO_val2014_000000359540.jpg": (12, 12),        # Baseball batter, grid 24x24
        "COCO_val2014_000000493610.jpg": (12, 12),        # Crowded truck, grid 24x24
    },
    "Molmo2-O-7B": {
        "pathway.png": (7, 7),                            # "PATHWAY ENDS" sign, grid 14x14
        "COCO_val2014_000000019036.jpg": (7, 7),          # Pizza kitchen, grid 14x14
        "COCO_val2014_000000035594.jpg": (7, 7),          # Elephants, grid 14x14
        "COCO_val2014_000000359540.jpg": (7, 7),          # Baseball batter, grid 14x14
        "COCO_val2014_000000493610.jpg": (7, 7),          # Crowded truck, grid 14x14
    },
}

# How many predictions to keep per patch per lens.
TOP_K = 5
# ---------------------------------------------------------------------------


def grab(txt, name):
    i = txt.index("const %s = " % name) + len("const %s = " % name)
    j = txt.index("\n", i)
    return json.loads(txt[i:j].rstrip().rstrip(";"))


def default_patch(model, name, grid_h, grid_w):
    """Resolve the configured default patch to a flat index into the grid."""
    coords = DEFAULT_PATCHES.get(model, {}).get(name)
    if coords is None:
        row, col = grid_h // 2, grid_w // 2
    else:
        row, col = coords
    row = max(0, min(grid_h - 1, row))
    col = max(0, min(grid_w - 1, col))
    return row * grid_w + col


def patch_template(src_models):
    """Print a DEFAULT_PATCHES block covering every kept model x image."""
    print("DEFAULT_PATCHES = {")
    for m in KEEP_MODELS:
        print("    %s: {" % json.dumps(m))
        for name in KEEP_IMAGES:
            dd = src_models[m]["images"][name]
            h, w = dd["grid_h"], dd["grid_w"]
            cur = DEFAULT_PATCHES.get(m, {}).get(name) or (h // 2, w // 2)
            entry = "        %s: (%d, %d)," % (json.dumps(name), cur[0], cur[1])
            print("%-58s# %s, grid %dx%d" % (entry, KEEP_IMAGES[name], h, w))
        print("    },")
    print("}")


def main():
    txt = open(SOURCE, encoding="utf-8").read()
    src_models = grab(txt, "MODELS")
    if "--patch-template" in sys.argv:
        patch_template(src_models)
        return
    src_images = grab(txt, "IMAGES")
    src_words = grab(txt, "WORDS")
    src_trans = grab(txt, "TRANSLATIONS")

    used = {}  # old word index -> new word index

    def remap(results):
        out = []
        for r in results[:TOP_K]:
            w = r[0]
            if w not in used:
                used[w] = len(used)
            out.append([used[w], r[1]])
        return out

    models = {}
    for m in KEEP_MODELS:
        if m not in src_models:
            raise SystemExit("unknown model %r" % m)
        d = src_models[m]
        images = {}
        for name in KEEP_IMAGES:
            if name not in d["images"]:
                raise SystemExit("model %s has no image %r" % (m, name))
            dd = d["images"][name]
            images[name] = {
                "grid_h": dd["grid_h"],
                "grid_w": dd["grid_w"],
                "default_patch": default_patch(m, name, dd["grid_h"], dd["grid_w"]),
                "by_layer": {
                    layer: {
                        # latentlens is deliberately dropped: the website demo
                        # only compares the verbalization lens to the logit lens.
                        "verballens": [remap(p) for p in ld["verballens"]],
                        "raw": [remap(p) for p in ld["raw"]],
                    }
                    for layer, ld in dd["by_layer"].items()
                },
            }
        models[m] = {"k": d["k"], "layers": d["layers"], "images": images}

    words = [None] * len(used)
    for old, new in used.items():
        words[new] = src_words[old]
    trans = {w: src_trans[w] for w in words if w in src_trans}
    images = {name: src_images[name] for name in KEEP_IMAGES}
    labels = dict(KEEP_IMAGES)

    dump = lambda o: json.dumps(o, separators=(",", ":"))
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("// Generated by build_demo_data.py -- do not edit by hand.\n")
        f.write("const DEMO_IMAGES = %s;\n" % dump(images))
        f.write("const DEMO_LABELS = %s;\n" % dump(labels))
        f.write("const DEMO_WORDS = %s;\n" % dump(words))
        f.write("const DEMO_TRANSLATIONS = %s;\n" % dump(trans))
        f.write("const DEMO_MODELS = %s;\n" % dump(models))
    print("wrote %s (%.1f MB), %d words" % (
        OUTPUT, os.path.getsize(OUTPUT) / 1e6, len(words)))


if __name__ == "__main__":
    main()
