# 手順書 pptx の作り方（python-pptx）

SKILL.md の Step 5 から参照する。**そのまま貼って動く型**を置いてある。
毎回ゼロから座標を書き始めない。

前提: `pip install python-pptx`。QA には LibreOffice（`soffice`）と `pdftoppm`。

---

## 1. 影を必ず落とす（最初に踏む地雷）

python-pptx が作る図形には `<p:style>` が付き、その `effectRef` を
**LibreOffice がドロップシャドウとして描く**。`shadow.inherit = False` だけでは
`<a:effectLst/>` が空になるだけで、`<p:style>` が残っていると影が出る。

```python
PNS = '{http://schemas.openxmlformats.org/presentationml/2006/main}style'

def _flat(shp):
    shp.shadow.inherit = False
    st = shp._element.find(PNS)
    if st is not None:
        shp._element.remove(st)
    return shp
```

図形を作る関数は**全部この `_flat` を通す**。1つ通し忘れると、そこだけ浮いて見える。

---

## 2. 最小のヘルパー

座標をベタ書きしない。この5つだけで手順書は組める。

```python
from pptx import Presentation
from pptx.util import Inches as I, Pt
from pptx.dml.color import RGBColor as C
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

W, H, M = 10.0, 5.625, 0.66          # 16:9 と外余白

def rect(s, x, y, w, h, fill=None, line=None, lw=0.75):
    shp = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, I(x), I(y), I(w), I(h))
    if fill is None: shp.fill.background()
    else: shp.fill.solid(); shp.fill.fore_color.rgb = fill
    if line is None: shp.line.fill.background()
    else: shp.line.color.rgb = line; shp.line.width = Pt(lw)
    return _flat(shp)

def rule(s, x, y, w, color, t=0.008):   # 横罫
    return rect(s, x, y, w, t, color)

def vrule(s, x, y, h, color, t=0.008):  # 縦罫（段組みの仕切り）
    return rect(s, x, y, t, h, color)

def text(s, x, y, w, h, runs, size=12, color=None, bold=False, font=None,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, space=6, lh=1.55):
    """runs は文字列、または [(文, {size/color/bold/font/space/lh}), ...]"""
    tb = s.shapes.add_textbox(I(x), I(y), I(w), I(h))
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    if isinstance(runs, str): runs = [(runs, {})]
    for i, (t_, o) in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = o.get("align", align)
        p.space_after = Pt(o.get("space", space))
        p.line_spacing = o.get("lh", lh)
        r = p.add_run(); r.text = t_
        f = r.font
        f.size = Pt(o.get("size", size)); f.bold = o.get("bold", bold)
        f.name = o.get("font", font); f.color.rgb = o.get("color", color)
    return tb

def label(s, x, y, t, color, size=8.5, w=4.0):
    """小さく字間を空けた欧文ラベル。全角スペースで字間を作る"""
    return text(s, x, y, w, 0.2, "　".join(list(t)), size=size, color=color,
                bold=True, space=0, lh=1.0)
```

`text()` に**必ず高さを渡す**。python-pptx は自動縮小しないので、高さは
「そこに何行入る想定か」の宣言として使い、QA のときの手がかりにする。

---

## 3. ページ共通（見出し・手順行・ノンブル）

```python
def head(s, no, t, lead=None, dark=False):
    """明朝の通し番号 ＋ 見出し。タイトル下に線は引かない"""
    text(s, M, 0.38, 0.9, 0.6, "%02d" % no, size=34, color=ACCENT, font=MI,
         space=0, lh=1.0)
    text(s, M + 0.92, 0.40, W - M - 0.92 - M, 0.56, t, size=28,
         color=PAPER if dark else HEAD, bold=True, font=MI, space=0, lh=1.12)
    y = 1.14
    if lead:
        text(s, M + 0.92, y, W - M - 0.92 - M, 0.36, lead, size=12,
             color=SUBC, space=0, lh=1.6)
        y += 0.46
    return y            # 本文の開始 y をページ側へ返す

def rows(s, x, y, w, items, gap=0.46, sub=0.32):
    """番号 ＋ 太字の一行 ＋ 灰色の結果。行間は細い罫で分ける"""
    for i, it in enumerate(items):
        if i: rule(s, x, y - 0.13, w, HAIR)
        text(s, x, y - 0.03, 0.5, 0.3, "%02d" % (i + 1), size=14,
             color=ACCENT, font=MI, space=0, lh=1.0)
        tx = x + 0.56
        text(s, tx, y, w - 0.56, 0.3, it[0], size=13, color=INK, bold=True,
             space=0, lh=1.35)
        h = gap
        if len(it) > 1 and it[1]:
            text(s, tx, y + 0.28, w - 0.56, 0.4, it[1], size=11, color=SUBC,
                 space=0, lh=1.55)
            h = gap + sub
        y += h
    return y
```

**`head()` が返す y を起点に積む。** 各ページで `y = 1.6` などと書き始めると、
見出しの高さを変えた瞬間に全ページがずれる。

---

## 4. 図：画面のワイヤーフレーム

矩形3つで足りる。**実寸比にする**（左レールが実際に画面幅の2割なら 0.20）。

```python
def wire(s, x, y, w, h, dark=False):
    rect(s, x, y, w, h, MID if dark else PAPER, DHAIR if dark else HAIR)
    rect(s, x, y, w * 0.20, h, RAIL)                       # 左レール
    rect(s, x + w * 0.795, y, w * 0.205, h, PANEL, HAIR)   # 右パネル
```

ナビ項目は小さな矩形を等間隔に並べ、**いま開いている項目だけ差し色**にする。
「どこを見ればいいか」がそれだけで伝わる。

---

## 5. 図：物の形（歯・部材・帳票）

`ROUND_2_SAME_RECTANGLE`（同じ側の2角だけ丸い矩形）を回転させると、
片側だけ丸い形が作れる。歯なら「歯茎側は角、切縁側は丸」。

```python
def tooth(s, x, y, w, h, corner=0.30, fill=ENAM, line=HAIR, lw=0.75):
    shp = s.shapes.add_shape(MSO_SHAPE.ROUND_2_SAME_RECTANGLE,
                             I(x), I(y), I(w), I(h))
    shp.adjustments[0] = corner    # 丸みの半径比（0〜0.5）
    shp.adjustments[1] = 0.02
    shp.rotation = 180             # 丸い側を下へ
    shp.fill.solid(); shp.fill.fore_color.rgb = fill
    shp.line.color.rgb = line; shp.line.width = Pt(lw)
    return _flat(shp)
```

`corner` と `h` を振るだけで「自然のまま／丸く／四角く／長く」の比較図になる。

### 並びを作る

幅・高さ・上端のずれを距離ごとの表で持つと、それらしい列になる。

```python
ORDER = [4, 3, 2, 1, 0, 0, 1, 2, 3, 4]   # 正中からの距離
TW_ = [0.30, 0.20, 0.22, 0.19, 0.17]     # 幅の比
TH_ = [0.60, 0.48, 0.55, 0.42, 0.38]     # 高さ
TY_ = [0.00, 0.035, 0.00, 0.02, 0.05]    # 上端のずれ

def arch(s, cx, y, w=3.2, hl=0, scale=1.0):
    """hl 本だけ差し色の輪郭で立てる。4/6/10 の比較図がこれ1つで作れる"""
    k = w / sum(TW_[ORDER[i]] for i in range(10))
    x = cx - w / 2
    for i in range(10):
        d = ORDER[i]; tw = TW_[d] * k; lit = d < hl / 2
        tooth(s, x + 0.012, y + TY_[d] * scale, tw - 0.024, TH_[d] * scale,
              fill=PAPER if lit else ENAM,
              line=ACCENT if lit else HAIR, lw=1.5 if lit else 0.75)
        x += tw
```

**選ばれている方を「濃くする」のではなく「輪郭を差し色にして塗りを白く抜く」。**
濃くすると、選ばれていない方が汚れて見える。

---

## 6. 図：値の比較

金額や数量は、値に比例した細いバーを名前の右に置く。表を作るより早く、
「どれくらい違うのか」が一目で入る。

```python
BARW = 1.86                                   # 最大値のときの長さ
rect(s, M + 2.2, y + 0.13, BARW * val / vmax, 0.055, ACCENT_LIGHT)
```

バーの右端と、右寄せした金額の左端が**重ならないこと**を必ず確認する
（初回は必ず重なる）。

---

## 7. QA ループ

```bash
OUT="…/guide.pptx"; QA=/tmp/qa; rm -rf "$QA"; mkdir -p "$QA"
cp "$OUT" "$QA/g.pptx"
cd "$QA" && HOME=/tmp soffice --headless --convert-to pdf --outdir . g.pptx
pdftoppm -jpeg -r 110 g.pdf p       # p-01.jpg … を全部見る
```

Drive などの読み取り専用マウント上では `rm` が通らないことがある。
**QA は `/tmp` でやって、画像だけコピーする。**

直す順番は、上から順に効く：

1. 文を削って行数を減らす
2. ボックスの高さを増やす
3. ブロックの開始位置を上げる（見出しの下の余白を詰める）
4. 2ページに割る

---

## 8. 実際に踏んだ順に並べた失敗

| 症状 | 原因 | 直し方 |
| --- | --- | --- |
| 図形に薄い影 | `<p:style>` の effectRef | `_flat()` を全図形に通す |
| 段組みの見出しが1文字だけ折り返す | 列幅の見積もり不足 | 列幅を広げるか、見出しを1〜2字削る |
| 表・帯の最終行が下の要素に隠れる | 行が折り返して伸びた | セル文字数を削る（高さを足すより確実） |
| 注意の一行がノンブルに被る | 下端 0.44" にランナー／ノンブルがある | 最終要素は `H - 0.86` より上で終える |
| 濃い面の中で左レールが見えない | 支配色と面の色が近すぎ | レールは支配色より**さらに暗く**する |
| 表紙の図がタイトルに重なる | 図を先に置いて文字幅を後から決めた | 文字のブロックを先に確定し、図は残りに置く |
