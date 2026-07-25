"""Subset Noto Sans CJK JP (CFF .ttc) to needed glyphs and convert to TrueType
so reportlab can embed it."""
import os
from fontTools import subset
from fontTools.ttLib import TTFont, newTable
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

TTC_PATHS = {
    "regular": "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "medium": "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc",
    "bold": "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
}


def _jp_face_index(path):
    from fontTools.ttLib import TTCollection
    coll = TTCollection(path, lazy=True)
    for i, f in enumerate(coll.fonts):
        name = f["name"].getDebugName(1) or ""
        if "JP" in name:
            return i
    return 0


def make_ttf(weight, text, out_path):
    """Subset the JP face of the given weight to `text` chars and convert CFF->glyf."""
    src = TTC_PATHS[weight]
    idx = _jp_face_index(src)
    font = TTFont(src, fontNumber=idx)
    # subset
    sub = subset.Subsetter(subset.Options(notdef_outline=True, drop_tables=["GSUB", "GPOS", "vhea", "vmtx", "VORG"]))
    sub.populate(text=text + " 　")
    sub.subset(font)
    # CFF -> glyf conversion
    glyph_order = font.getGlyphOrder()
    glyf = newTable("glyf")
    glyf.glyphs = {}
    glyf.glyphOrder = glyph_order
    charstrings = font["CFF "].cff.topDictIndex[0].CharStrings
    hmtx = font["hmtx"]
    for gname in glyph_order:
        ttpen = TTGlyphPen(None)
        pen = Cu2QuPen(ttpen, max_err=1.0, reverse_direction=True)
        try:
            charstrings[gname].draw(pen)
        except KeyError:
            pass
        glyf.glyphs[gname] = ttpen.glyph()
    font["glyf"] = glyf
    loca = newTable("loca")
    font["loca"] = loca
    del font["CFF "]
    if "VDMX" in font:
        del font["VDMX"]
    font.sfntVersion = "\x00\x01\x00\x00"
    # required for glyf fonts
    font["maxp"].tableVersion = 0x00010000
    for attr in ("maxZones", "maxTwilightPoints", "maxStorage", "maxFunctionDefs",
                 "maxInstructionDefs", "maxStackElements", "maxSizeOfInstructions",
                 "maxComponentElements"):
        setattr(font["maxp"], attr, 0)
    font["head"].indexToLocFormat = 1
    # unique internal name: reportlab caches faces by PostScript name, so two subsets
    # of the same font would otherwise clobber each other's glyph mapping
    uid = "NotoSub" + hex(abs(hash(out_path + text)) % 16**8)[2:]
    name_table = font["name"]
    for nid in (1, 3, 4, 6):
        name_table.setName(uid, nid, 3, 1, 0x409)
    font.save(out_path)
    return out_path


if __name__ == "__main__":
    p = make_ttf("medium", "松尾夏実秘書TelNatsumi Matsuo0123456789.-", "/tmp/test_med.ttf")
    t = TTFont(p)
    print("ok", p, t.sfntVersion, len(t.getGlyphOrder()))
