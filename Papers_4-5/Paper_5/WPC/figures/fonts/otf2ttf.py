#!/usr/bin/env python3
"""Convert the Latin Modern Roman OpenType (CFF) fonts to TrueType outlines, so Matplotlib can embed them as
TrueType (Type 42) in PDF and EPS. Latin Modern is the Computer Modern design that the manuscript's body text uses.
The converted files are renamed "LM Roman TT" to mark them as converted copies (GUST Font License).
Usage: otf2ttf.py   (reads /usr/share/texmf/fonts/opentype/public/lm, writes next to this file)"""
import os
from fontTools.ttLib import TTFont, newTable
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

SRC = "/usr/share/texmf/fonts/opentype/public/lm"
OUT = os.path.dirname(os.path.abspath(__file__))


def convert(name, style):
    f = TTFont(f"{SRC}/{name}.otf")
    order = f.getGlyphOrder(); gs = f.getGlyphSet()
    glyf = newTable("glyf"); glyf.glyphOrder = order; glyf.glyphs = {}
    for g in order:
        pen = TTGlyphPen(gs)
        gs[g].draw(Cu2QuPen(pen, max_err=1.0, reverse_direction=True))
        glyf.glyphs[g] = pen.glyph()
    f["glyf"] = glyf; f["loca"] = newTable("loca")
    del f["CFF "]
    if "VORG" in f:
        del f["VORG"]
    f.sfntVersion = "\000\001\000\000"
    maxp = newTable("maxp"); maxp.tableVersion = 0x00010000
    for k in ("maxZones", "maxTwilightPoints", "maxStorage", "maxFunctionDefs", "maxInstructionDefs", "maxStackElements",
              "maxSizeOfInstructions", "maxComponentElements"):
        setattr(maxp, k, 1 if k == "maxZones" else 0)
    maxp.numGlyphs = len(order)
    f["maxp"] = maxp
    f["post"].formatType = 2.0; f["post"].extraNames = []; f["post"].mapping = {}; f["post"].glyphOrder = order
    for rec in f["name"].names:
        if rec.nameID in (1, 16):
            rec.string = "LM Roman TT"
        elif rec.nameID in (4,):
            rec.string = f"LM Roman TT {style}"
        elif rec.nameID == 6:
            rec.string = f"LMRomanTT-{style.replace(' ', '')}"
        elif rec.nameID in (2, 17):
            rec.string = style
    f.save(f"{OUT}/LMRomanTT-{style.replace(' ', '')}.ttf")


for n, s in (("lmroman10-regular", "Regular"), ("lmroman10-bold", "Bold"), ("lmroman10-italic", "Italic"), ("lmroman10-bolditalic", "Bold Italic")):
    convert(n, s)
print("done")
