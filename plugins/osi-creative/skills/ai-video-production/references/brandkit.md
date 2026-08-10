# ブランドキット（動画名刺の量産単位）

`vp-corporate-card` / `vp-personal-intro` が共通で使う。
**1社の1本目を作るときに、副産物としてキットを確定させる。** これがある状態なら、2本目以降に人が触るのは Phase 0（ブリーフ）と Phase 1（台本承認）だけになる。

## 構造

```
brandkit/<company>/
├─ kit.yaml              # 配色・フォント・画風アンカー文・声ID・音源ID・ロゴ位置
├─ style_anchor.txt      # 全画像プロンプトの先頭に固定で入る画風固定文
├─ characters/           # 人物ごとのキャラ設定シート（L1アバター）
│   ├─ <person>.png
│   └─ <person>_refs/    # 別角度・別表情（nano-banana-2 は人物参照 最大4枚）
├─ music/                # signature_a.mp3 / signature_b.mp3 / signature_c.mp3 / sting.mp3
├─ telop/                # テロップテンプレ（フォント・色・アニメーション）
└─ outro/                # B6の共通ロゴカード（全員同じ絵で終わる）
```

## kit.yaml

```yaml
company: 株式会社◯◯
palette:
  primary: "#C8102E"
  sub: "#1B1B1B"
  bg: "#FAF7F2"
font:
  telop: "Noto Sans JP Bold"
  logo: "（ブランド指定）"
style_anchor: |
  2D hand-drawn anime, soft watercolor texture, warm natural light,
  clean line art, muted palette of #FAF7F2 and #C8102E, no text overlays
voice: konoha                 # narration の voice_id
music:
  corporate: signature_a
  personal:  signature_b
  quiet:     signature_c
  sting:     sting            # 全動画のB6に共通で置く
outro: outro/logo_card.mp4
aspects: [16:9, 9:16, 1:1]
```

## style_anchor.txt の役割

**全画像プロンプトの先頭に必ず入れる固定文**。ここを共有することで、別の人が別の日に作っても同じ絵柄で揃う。
`generate_image` の参照画像（`image_urls`）と併用すると更に安定する。

> IPリスク：固有スタジオ名（「ジブリ風」等）を書かない。`2D hand-drawn anime / watercolor / hand-painted` でアンカーする。
> 詳細は `pitfalls.md` と `../templates/prompts-anime-ghibli.md`。

## シリーズに見せる仕掛け

10本並べたときに「同じ会社の動画」に見えるかが、この機能の価値。効かせる順に：

1. **B6のロゴカードを全員共通にする**（`outro/`）。終わり方が同じだと、それだけでシリーズに見える。
2. **スティング（2秒のロゴ音）を全動画のB6に置く**。耳のロゴ。
3. **テロップのフォント・色・出方を固定する**（`telop/`）。
4. **画風アンカーを共有する**（`style_anchor.txt`）。

逆に**BGMを1本ごとに生成し直すと、この効果が全部消える**。音源はキット内の3〜5本を使い回す（`music` スキル参照）。

## バッチ運用

- `brief_*.yaml` をフォルダに並べて順に流す。1セッションで10人分を想定。
- 生成待ちが支配的なので、**複数人分を重ねて流す**と1人あたりの実時間が大きく落ちる（10人分で60〜80分）。
- 出力は `out/<company>/<person>/` に配信キット一式。
