"""Subset Noto Sans CJK JP (CFF .ttc/.otf) to needed glyphs and convert to TrueType
so reportlab can embed it.

Font resolution is defensive on purpose: Cowork のサンドボックス実装によっては
NotoSansCJK-Medium.ttc が入っておらず（Regular / Bold のみ）、以前はここで
FileNotFoundError になって名刺生成そのものが失敗していた。ローカル候補を順に探し、
無ければ notofonts の公式 OTF をキャッシュへ取得する。太さを黙って別のものに
差し替えることはしない（印刷物なので気付かないまま刷られる方が事故）。
"""
import os
import sys
import tempfile
import urllib.request
from fontTools import subset
from fontTools.ttLib import TTFont, newTable
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

CACHE_DIR = os.path.join(tempfile.gettempdir(), "meishi-noto-cache")

# 探索順: 環境変数の明示指定 → OS 同梱 → キャッシュ済みDL
LOCAL_CANDIDATES = {
    "regular": [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.otf",
        "/System/Library/Fonts/NotoSansCJK-Regular.ttc",
    ],
    "medium": [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Medium.otf",
        "/System/Library/Fonts/NotoSansCJK-Medium.ttc",
    ],
    "bold": [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Bold.otf",
        "/System/Library/Fonts/NotoSansCJK-Bold.ttc",
    ],
}

DOWNLOAD_URLS = {
    "regular": [
        "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Regular.otf",
        "https://cdn.jsdelivr.net/gh/notofonts/noto-cjk@main/Sans/OTF/Japanese/NotoSansCJKjp-Regular.otf",
    ],
    "medium": [
        "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Medium.otf",
        "https://cdn.jsdelivr.net/gh/notofonts/noto-cjk@main/Sans/OTF/Japanese/NotoSansCJKjp-Medium.otf",
    ],
    "bold": [
        "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Bold.otf",
        "https://cdn.jsdelivr.net/gh/notofonts/noto-cjk@main/Sans/OTF/Japanese/NotoSansCJKjp-Bold.otf",
    ],
}

ENV_OVERRIDE = {
    "regular": "MEISHI_NOTO_REGULAR",
    "medium": "MEISHI_NOTO_MEDIUM",
    "bold": "MEISHI_NOTO_BOLD",
}


def resolve_font(weight):
    """Return a usable Noto Sans CJK JP file for `weight`, downloading it if needed."""
    override = os.environ.get(ENV_OVERRIDE[weight])
    if override:
        if not os.path.exists(override):
            raise FileNotFoundError(
                f"{ENV_OVERRIDE[weight]} で指定されたフォントが見つかりません: {override}")
        return override
    for path in LOCAL_CANDIDATES[weight]:
        if os.path.exists(path):
            return path
    os.makedirs(CACHE_DIR, exist_ok=True)
    cached = os.path.join(CACHE_DIR, f"NotoSansCJKjp-{weight.capitalize()}.otf")
    if os.path.exists(cached) and os.path.getsize(cached) > 1_000_000:
        return cached
    errors = []
    for url in DOWNLOAD_URLS[weight]:
        try:
            print(f"[fontprep] Noto Sans CJK JP {weight} が見つからないため取得します: {url}",
                  file=sys.stderr)
            tmp = cached + ".part"
            urllib.request.urlretrieve(url, tmp)
            if os.path.getsize(tmp) < 1_000_000:
                raise OSError(f"downloaded file too small ({os.path.getsize(tmp)} bytes)")
            os.replace(tmp, cached)
            return cached
        except Exception as e:  # noqa: BLE001 - 次の候補URLへ
            errors.append(f"{url}: {e}")
    raise FileNotFoundError(
        "Noto Sans CJK JP " + weight + " を用意できませんでした。\n"
        "  探した場所: " + ", ".join(LOCAL_CANDIDATES[weight]) + "\n"
        "  ダウンロード失敗: " + " / ".join(errors) + "\n"
        "  対処: フォントを手元に用意して環境変数 " + ENV_OVERRIDE[weight] + " にパスを指定してください。\n"
        "  （太さを勝手に別のものへ落とすと印刷物の見た目が変わるため、自動フォールバックはしません）")


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
    src = resolve_font(weight)
    if src.lower().endswith(".ttc"):
        font = TTFont(src, fontNumber=_jp_face_index(src))
    else:
        font = TTFont(src)
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
