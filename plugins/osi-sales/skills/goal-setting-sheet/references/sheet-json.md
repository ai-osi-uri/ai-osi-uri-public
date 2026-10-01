# sheet.json の形

`assets/build-sheet.js` に渡すデータ。例は `assets/sheet.example.json`。

| キー | 中身 |
|---|---|
| `client` | 相手先の正式社名（公式サイトの表記） |
| `author` | 自社名（`{{company.name}}`） |
| `note` | 表紙の1行の断り書き |
| `sections` | 1〜3章（今の課題／現状の対応／進みたい方針）。`title`・`lead`（任意）・`bullets` |
| `proposalLead` | 4章「弊社のご提案」の冒頭の一文 |
| `proposals` | ご提案の配列。`title` と `rows`（`[項目名, 中身の配列]`） |
| `plan` | 最後のプラン。`lead`・`name`・`rows`・`note`（任意） |

- 中身の配列の要素は、文字列なら段落、`{"bullet": "…"}` なら箇条書き。
- `**…**` で囲んだところは濃紺の太字になる。
- 箇条書きの頭に「見出し：」を付けない。
- ご提案は2つ目以降が改ページされる。表がページをまたぐときは、そのご提案の行を減らす。

## 作り方

```bash
cd assets && npm i docx   # 未インストールなら
node build-sheet.js sheet.json 目標設定シート.docx
# 確認: soffice で PDF にして pdftoppm で画像化し、全ページを目で見る
```
