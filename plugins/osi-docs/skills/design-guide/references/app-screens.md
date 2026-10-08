# アプリ・画面の部品の選び方（shadcn/ui）

参考。迷ったときの早見表。場面に合わなければ別の部品を選んでよい。

| やりたいこと | 使う部品 | 気をつけること |
|---|---|---|
| 操作を実行する | Button | 1画面で目立たせる（`default`）のは1つ。他は `outline` / `ghost` |
| 消す・取り消せない操作 | Button（`destructive`）＋ AlertDialog | 押す前に何が消えるかを書いて確認を取る |
| 1行の文字を入れる | Input ＋ Label | ラベルは入力欄の上。例文（placeholder）をラベル代わりにしない |
| 長い文章を入れる | Textarea | |
| 決まった選択肢から1つ | 5個以下：RadioGroup／それ以上：Select | 選択肢が見えている方が選びやすい |
| 選択肢を検索して選ぶ | Combobox（Command ＋ Popover） | 候補が多いとき |
| オン／オフ | 即時に効く：Switch／保存ボタンで効く：Checkbox | |
| 日付 | Calendar ＋ Popover（Date Picker） | |
| 入力のまとまり | Form（react-hook-form ＋ zod） | エラーはその入力欄のすぐ下に出す |
| 情報のまとまりを見せる | Card | 中身が少ないカードを横に並べない |
| 一覧・台帳 | Table（多いときは Data Table） | 並べ替え・絞り込みは列が5本を超えたら付ける |
| 画面を切り替える | Tabs | 3〜5個まで。それ以上はメニューにする |
| 別の画面に行かずに詳しく見せる | Sheet（横から出る）／Dialog | 入力が多いなら Sheet |
| 結果を知らせる | Sonner（トースト） | 失敗は消えないようにする |
| 状態を示す小さな札 | Badge | 色だけで区別しない。文字も入れる |
| 読み込み中 | Skeleton | くるくる回る印より、出てくる形を先に見せる |
| 補足の説明 | Tooltip | 大事なことは Tooltip に隠さない |
| 画面の左のメニュー | Sidebar | |

## 色の変数（6章で会社の色を入れる場所）

| 変数 | 役割 |
|---|---|
| `--primary` / `--primary-foreground` | 主色と、その上に乗る文字の色 |
| `--background` / `--foreground` | 地の色と本文の色 |
| `--destructive` | 注意色 |
| `--muted` / `--muted-foreground` | 補足の地と補足の文字（薄くしすぎない） |
| `--border` / `--ring` | 枠線と、選んでいる場所の印 |
| `--radius` | 角の丸み |

> 例（2026-10 / shadcn/ui の標準テーマ「neutral」）：色を持たないときは、このテーマをそのまま使えばよい。
> 会社の色を入れるときは `--primary` だけ差し替えても、全体の印象はほぼ揃う。
