"""AI OSI URI 名刺 入稿用PDFジェネレーター
テンプレ(.ai / PDF互換)の可変部分（役職・氏名・ローマ字・Tel・E-mail）を差し替えて
ラクスル入稿用PDFを生成する。固定要素（ロゴ・社名・住所・URL・トンボ）は元のベクターを維持。
"""
import io, json, os, sys, tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.colors import CMYKColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont as RLTTFont
from pypdf import PdfReader, PdfWriter
import fontprep

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE_W, PAGE_H = 841.89, 595.276
PX = 300.0 / 72.0  # px per pt at 300dpi

BLACK = CMYKColor(0, 0, 0, 1)
RED = CMYKColor(0.168, 0.977, 0.895, 0)
WHITE = CMYKColor(0, 0, 0, 0)

# base templates
BASE_NOEMAIL = os.path.join(HERE, "template_noemail.pdf")  # 松尾ベース
BASE_EMAIL = os.path.join(HERE, "template_email.pdf")      # 坂口ベース

def pt_x(px): return px / PX
def pt_y(px): return PAGE_H - px / PX

# ---- layout parameters (px @300dpi, top-left origin) ----
# calibrated against the two original cards
# fonts: kanji = Noto Sans CJK JP / latin = Montserrat (matches original design font)
PARAMS = {
    "left_x": 1297,
    "title": {"baseline": 1111.5, "size": 7.1, "cs": 0.0, "font": "noto-medium",
              "latin_size": 8.4, "latin_font": "mont-500", "latin_baseline": 1114},
    "name": {"baseline": 1180.7, "size": 12.0, "cs": 2.4, "font": "noto-medium", "dx": -1},
    "romaji": {"baseline": 1223, "size": 5.64, "cs": 0.54, "font": "mont-500"},
    "tel": {"size": 5.49, "cs": 1.04, "font": "mont-500"},
    "email": {"size": 5.49, "cs": 0.575, "font": "mont-500"},
    # right column x and baselines per base
    "right_x": {"noemail": 1793, "email": 1751},
    "tel_baseline": 1224,
    "email_baseline": 1258,
}

MASKS = {
    "noemail": [
        (1286, 1076, 1600, 1232),   # left block
        (1784, 1196, 2300, 1232),   # tel line
    ],
    "email": [
        (1286, 1076, 1600, 1232),
        (1742, 1196, 2300, 1232),   # tel line
        (1742, 1232, 2300, 1268),   # email line
    ],
}

_registered = {}

def get_font(spec, text):
    """spec: 'noto-regular' | 'noto-medium' | 'noto-bold' | 'mont-400' | 'mont-500' | 'mont-600'"""
    family, variant = spec.split("-")
    if family == "mont":
        if spec not in _registered:
            name = f"Mont-{variant}"
            pdfmetrics.registerFont(RLTTFont(name, os.path.join(HERE, f"mont_{variant}.ttf")))
            _registered[spec] = {"name": name, "chars": None}
        return _registered[spec]["name"]
    cached = _registered.get(spec)
    if cached and set(text) <= cached["chars"]:
        return cached["name"]
    allchars = (cached["chars"] if cached else set()) | set(text)
    ttf = os.path.join(tempfile.gettempdir(), f"noto_{variant}_{abs(hash(''.join(sorted(allchars))))%99999}.ttf")
    fontprep.make_ttf(variant, "".join(sorted(allchars)), ttf)
    name = f"NotoJP-{variant}-{abs(hash(ttf))%99999}"
    pdfmetrics.registerFont(RLTTFont(name, ttf))
    _registered[spec] = {"chars": allchars, "name": name}
    return name

def draw_text(c, px_x, px_baseline, text, size, cs, weight, color, max_x_px=None):
    """max_x_px: 仕上がり内に収めるための右端上限(px)。超える場合は字間→サイズの順に自動縮小"""
    font = get_font(weight, text)
    if max_x_px and len(text) > 1:
        avail = pt_x(max_x_px) - pt_x(px_x)
        u = pdfmetrics.stringWidth(text, font, 1.0)
        if size * u + cs * (len(text) - 1) > avail:
            cs = max(0.0, (avail - size * u) / (len(text) - 1))
            if size * u > avail:
                size = avail / u
    c.setFillColor(color)
    c.setFont(font, size)
    obj = c.beginText(pt_x(px_x), pt_y(px_baseline))
    obj.setCharSpace(cs)
    obj.textOut(text)
    c.drawText(obj)

def _is_latin(ch):
    return ord(ch) < 0x2000

def draw_title(c, px_x, title, tp):
    """役職: 漢字かな=Noto / 英字(CIO等)=Montserrat を混植で描く"""
    runs = []
    for ch in title:
        kind = "latin" if _is_latin(ch) else "cjk"
        if runs and runs[-1][0] == kind:
            runs[-1][1] += ch
        else:
            runs.append([kind, ch])
    x_pt = pt_x(px_x)
    for kind, text in runs:
        if kind == "latin" and text.strip() == "":
            x_pt += tp["latin_size"] * 0.30 * len(text)  # word space
            continue
        if kind == "cjk":
            font = get_font(tp["font"], text)
            size, cs, base = tp["size"], tp["cs"], tp["baseline"]
        else:
            n_lead = len(text) - len(text.lstrip(" "))
            n_trail = len(text) - len(text.rstrip(" "))
            x_pt += tp["latin_size"] * 0.30 * n_lead
            font = get_font(tp["latin_font"], text)
            size, cs, base = tp["latin_size"], 0.0, tp["latin_baseline"]
            text = text.strip()
            if not text:
                continue
        c.setFillColor(BLACK)
        c.setFont(font, size)
        obj = c.beginText(x_pt, pt_y(base))
        obj.setCharSpace(cs)
        obj.textOut(text)
        c.drawText(obj)
        x_pt += pdfmetrics.stringWidth(text, font, size) + cs * len(text)

def generate(name, romaji, title, tel, email=None, out="meishi.pdf", params=None):
    p = params or PARAMS
    variant = "email" if email else "noemail"
    base_path = BASE_EMAIL if email else BASE_NOEMAIL

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))
    # masks
    c.setFillColor(WHITE)
    for (x0, y0, x1, y1) in MASKS[variant]:
        c.rect(pt_x(x0), pt_y(y1), pt_x(x1 - x0), (y1 - y0) / PX, stroke=0, fill=1)
    lx = p["left_x"]
    name = name.replace("　", " ")  # 区切りは半角スペース+トラッキング（原本と同じ組み方）
    draw_title(c, lx, title, p["title"])
    # 仕上がり(トンボ実測): x 1216-2291 / y 915-1565 @300dpi（=91×55mm）
    LEFT_MAX = 1730   # 左ブロックの右端上限（右カラムに食い込まない）
    RIGHT_MAX = 2250  # 右カラムの右端上限（仕上がり線2291の約3.5mm内側＝原本デザインと同じ余白）
    draw_text(c, lx + p["name"].get("dx", 0), p["name"]["baseline"], name, p["name"]["size"], p["name"]["cs"], p["name"]["font"], BLACK, max_x_px=LEFT_MAX)
    draw_text(c, lx, p["romaji"]["baseline"], romaji, p["romaji"]["size"], p["romaji"]["cs"], p["romaji"]["font"], RED, max_x_px=LEFT_MAX)
    rx = p["right_x"][variant]
    draw_text(c, rx, p["tel_baseline"], f"Tel. {tel}", p["tel"]["size"], p["tel"]["cs"], p["tel"]["font"], BLACK, max_x_px=RIGHT_MAX)
    if email:
        draw_text(c, rx, p["email_baseline"], f"E-mail: {email}", p["email"]["size"], p["email"]["cs"], p["email"]["font"], BLACK, max_x_px=RIGHT_MAX)
    c.save()
    buf.seek(0)

    base = PdfReader(base_path)
    overlay = PdfReader(buf)
    page = base.pages[0]
    page.merge_page(overlay.pages[0])
    w = PdfWriter()
    w.add_page(page)
    with open(out, "wb") as f:
        w.write(f)
    return out

if __name__ == "__main__":
    args = json.loads(sys.argv[1])
    print(generate(**args))
