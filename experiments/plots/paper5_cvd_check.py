#!/usr/bin/env python3
"""Accessibility check for the WPC figures: render each figure as printed in greyscale and as seen with
full protanopia, deuteranopia, and tritanopia (Machado, Oliveira and Fernandes 2009 matrices), side by side.

Usage: paper5_cvd_check.py OUTDIR FIG.pdf [FIG.pdf ...]
Writes OUTDIR/<name>_cvd.png with five rows: original, greyscale, protan, deutan, tritan.
"""
import os
import subprocess
import sys

import numpy as np
from PIL import Image

M = {"protan": np.array([[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]]),
     "deutan": np.array([[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]]),
     "tritan": np.array([[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]])}


def lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def delin(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)


def views(rgb):
    x = rgb.astype(float) / 255
    out = [x]
    y = lin(x) @ np.array([0.2126, 0.7152, 0.0722])
    out.append(np.repeat(delin(y)[..., None], 3, axis=2))
    for k in ("protan", "deutan", "tritan"):
        out.append(delin(lin(x) @ M[k].T))
    return [(255 * v).astype(np.uint8) for v in out]


def main():
    outdir, pdfs = sys.argv[1], sys.argv[2:]
    os.makedirs(outdir, exist_ok=True)
    for pdf in pdfs:
        name = os.path.splitext(os.path.basename(pdf))[0]
        png = os.path.join(outdir, name)
        subprocess.run(["pdftoppm", "-r", "110", "-singlefile", "-png", pdf, png], check=True)
        rgb = np.asarray(Image.open(png + ".png").convert("RGB"))
        rows = views(rgb)
        Image.fromarray(np.concatenate(rows, axis=0)).save(os.path.join(outdir, name + "_cvd.png"))
        os.remove(png + ".png")
        print(name)


if __name__ == "__main__":
    main()
