# 管理画面パターン（社内向け CRUD コンソール）

> `create-app` が「運営が日々さわる管理画面」を含むアプリを作るときの型。
> AI同友会（会員管理・予約システム）の実装で確立し、実運用のフィードバックで固めたもの。
> Next.js App Router + Supabase 前提。**この型から始めて、要件に応じて足す**。

---

## 0. いつ使うか

アプリ定義に「**運営／管理者が使う画面**」がひとつでもあるなら、この型で作る。判定は単純で、

- 利用者（顧客・会員・申込者）と、運営（社内）の**二者が存在する**
- 運営側が一覧を見て、作って、直して、消す（＝CRUD）

これに当てはまれば管理画面。当てはまらない（LP のみ、利用者しかいない）なら不要。

**やってはいけないこと**：1ページに審査も開催回も会員管理も全部積む。
最初は動くが、項目が増えた瞬間に「下までスクロールしないと目的の操作に届かない」画面になる。
最初からセクションごとに URL を分ける。

---

## 1. 画面の骨格：左サイドバー ＋ 一覧 ＋ 右上に新規作成

社内ツールで最も学習コストが低い形。3つの約束だけ守る。

| 約束 | 内容 |
|---|---|
| **左サイドバー** | 縦に機能を並べる。現在地をハイライト。要対応件数はバッジで出す |
| **一覧が起点** | 各機能のトップは必ずリスト。ダッシュボードから始めない |
| **新規作成は右上** | `＋ ◯◯を作る` を `admin-head` の右端に固定。位置を全画面で揃える |

遷移は **一覧 → 詳細 → その中で編集**。詳細を別ページにすることで、
一覧が軽いまま保て、URL を共有でき、ブラウザバックが期待通りに効く。
ただし**削除は一覧からもできるようにする**（→ 5章）。詳細に入らないと消せないのは不便。

サイドバーは「よく使う順」ではなく「**業務の流れ順**」に並べる。
運営が頭の中で辿る順番と一致していないと、毎回探すことになる。

---

## 2. ディレクトリ構成（ルートグループで分ける）

```
app/
  layout.tsx                    ← html/body と globals.css だけ。ヘッダを置かない
  (site)/                       ← 利用者が見る側
    layout.tsx                  ← 公開サイトのヘッダ・フッタ
    page.tsx  apply/  login/  me/  ...
  admin/
    login/page.tsx              ← サイドバーの外（未ログインでも見える）
    setup/[token]/page.tsx      ← 同上（招待からのパスワード設定）
    actions.ts                  ← 管理者の認証まわりのサーバーアクション
    (dash)/
      layout.tsx                ← ここで認証チェック＋サイドバー
      nav.tsx                   ← "use client"。usePathname で現在地を判定
      page.tsx                  → /admin        ダッシュボード
      events/page.tsx           → /admin/events 一覧
      events/new/page.tsx       →               新規作成
      events/[id]/page.tsx      →               詳細（編集・削除）
      events/[id]/reception/    →               その回に紐づく作業画面
      members/ ...              同じ形
  api/                          ← ルートハンドラ（レイアウトの影響を受けない）
```

**ルートグループ `( )` は URL に出ない。** これを使うと、ヘッダの有無を
レイアウト単位で完全に分けられる。`app/layout.tsx` に共通ヘッダを置いてしまうと
管理画面にも出てしまうので、**ルートは器だけ**にするのが要点。

`admin/login` と `admin/setup` を `(dash)` の外に置くのを忘れないこと。
中に入れると「ログインするためにログインが必要」になる。

---

## 3. 認証チェックはレイアウトに1か所

```tsx
// app/admin/(dash)/layout.tsx
export default async function DashLayout({ children }) {
  const me = await currentAdmin();
  if (!me) redirect("/admin/login");
  // ...サイドバー＋ {children}
}
```

各ページで毎回チェックすると、**新しい画面を足したときに守り忘れる**。
レイアウトに置けば、配下に増やすページは自動的に保護される。

サイドバーのバッジ（審査待ち件数など）もレイアウトで集計して `nav.tsx` に渡す。
全画面で同じ数字が出て、対応漏れに気づける。

---

## 4. 運営アカウントは利用者と完全に分ける

「管理者フラグを持った利用者」にしない。**別系統にする。**

| | 利用者 | 運営 |
|---|---|---|
| 入口 | `/login` | `/admin/login` |
| 認証 | パスワード／メールリンク | メール＋パスワード |
| 保存先 | Supabase Auth | `admin_users` テーブル |
| セッション | Supabase のクッキー | 独自の署名付きクッキー |

分ける理由は3つ。**片方の認証が破られてももう片方に波及しない**。
利用者の一覧に運営が混ざらない。そして「管理者だけ挙動が違う」分岐がコードから消える。

**環境変数にメールアドレスを列挙して判定するのは初期だけ。**
人が増える・辞める運用になった時点でテーブルに移す。デプロイしないと権限を変えられないのは事故のもと。

### パスワードは必ず本人が決める

管理者が他人のパスワードを設定できる作りにしない。**招待方式**にする。

1. 既存の運営が管理画面からメールアドレスを入れて招待
2. `setup_token`（期限つき）を発行し、設定用リンクをメールで送る
3. **招待された本人がリンクを開いてパスワードを決める**
4. 設定と同時にトークンを無効化してログイン状態にする

パスワードを忘れた場合も同じ招待を再送すれば再設定できる。専用のリセット機能はいらない。
退任者は物理削除せず `disabled` フラグで止める（記録が残る）。**自分自身は無効にできない**ようにする。

### 実装（外部ライブラリを増やさない）

```ts
// scrypt は Node 標準。bcrypt を入れるほどの理由がない
export function hashPassword(plain: string): string {
  const salt = crypto.randomBytes(16);
  const key = crypto.scryptSync(plain.normalize("NFKC"), salt, 64, { N: 16384, r: 8, p: 1 });
  return `scrypt$${salt.toString("hex")}$${key.toString("hex")}`;
}

export function verifyPassword(plain: string, stored: string | null): boolean {
  if (!stored) return false;                      // 招待中（未設定）は必ず false
  const [alg, saltHex, keyHex] = stored.split("$");
  if (alg !== "scrypt") return false;
  const key = crypto.scryptSync(plain.normalize("NFKC"), Buffer.from(saltHex, "hex"), 64,
    { N: 16384, r: 8, p: 1 });
  const expected = Buffer.from(keyHex, "hex");
  return expected.length === key.length && crypto.timingSafeEqual(key, expected);
}
```

セッションは `payload.HMAC` 形式の署名付きクッキー（HttpOnly / Secure / SameSite=Lax / 12時間）。
検証は `timingSafeEqual` で行い、**セッションが有効でも DB の `disabled` を毎回見る**
（無効化を即座に効かせるため）。署名鍵は `ADMIN_SESSION_SECRET`。

ログイン失敗のメッセージは**1種類にそろえる**。
「そのメールは存在しません」と返すと、アカウントの有無を外から調べられる。

パスワードの条件は**長さだけ**にする（8文字以上など）。記号や大文字の強制は、
付箋に書かれる・使い回されるという別のリスクを生む。**依頼主が指定した長さに従う。**

---

## 5. 危険な操作の扱い

**削除は一覧からもできるようにする。** 詳細に入らないと消せない管理画面は不便で、
1件ずつ開いて戻ってを繰り返すことになる。**確認を挟めば一覧に置いてよい。**

| 場所 | 確認の強さ |
|---|---|
| 一覧の行 | 確認ダイアログ1枚。**対象の名前と、一緒に消えるものを文面に必ず入れる** |
| 詳細の `danger-zone` | `delete` と入力させる（その1件に向き合っている場面なので、より強く） |

```tsx
// components/RowDelete.tsx  — 一覧の行から消すための最小実装
"use client";
export default function RowDelete({ action, id, label, warning }) {
  return (
    <form action={action} onSubmit={(e) => {
      if (!confirm(`「${label}」を削除します。\n\n${warning}\n\nこの操作は取り消せません。よろしいですか？`))
        e.preventDefault();
    }}>
      <input type="hidden" name="id" value={id} />
      <input type="hidden" name="confirm" value="delete" />
      <button className="btn btn-ghost btn-sm btn-danger" type="submit">削除</button>
    </form>
  );
}
```

削除ボタンは他のボタンと**見た目を変える**（`btn-danger`：赤い枠線）。並びの中で見分けがつかないと誤クリックする。

| 操作 | 扱い |
|---|---|
| 退会・停止 | 削除ではなく**状態の変更**を既定にし、画面上でそう案内する |
| 課金の停止・返金 | **管理画面からは実行させない。表示のみ**にして決済側の管理画面へ誘導 |

削除で何が一緒に消えるか（関連レコード）を、確認の文面と画面の両方に日本語で書く。
「本当に削除しますか？」だけでは、何が失われるか分からない。

課金操作を1クリックで実行できる管理画面は、便利さより事故のほうが大きい。
**読むのは自動、止めるのは手動**が既定。依頼主が明示的に求めたときだけ足す。

---

## 6. 外部サービスの状態は「一覧はキャッシュ、詳細はライブ」

決済状態のような外部 API 由来の情報は、取得コストが高い。

- **一覧**：Webhook で自テーブルに同期した状態を出す（API を呼ばない）
- **詳細**：開いたときだけ外部 API を叩き、最新の状態・次回請求日・履歴を出す

一覧で N 件ぶん API を呼ぶと、件数に比例して画面が重くなる。
外部 API は**必ず失敗する前提**で書き、落ちても画面は出す。

```ts
export async function getBilling(subscriptionId: string | null): Promise<Billing> {
  if (!subscriptionId) return { status: "none", statusJa: "未契約", ... };
  try {
    const s = await stripe.subscriptions.retrieve(subscriptionId);
    return { status: s.status, statusJa: JA[s.status] ?? s.status, ... };
  } catch {
    return { status: "unknown", statusJa: "取得できず", ... };   // 画面は落とさない
  }
}
```

状態は**日本語に翻訳して出す**。`past_due` のまま出しても運営には伝わらない。

---

## 7. 作業画面は、対象に紐づける

当日の受付、棚卸し、発送処理といった「特定の対象に対する現場作業」は、
サイドバーに独立して置かず、**対象の詳細配下**に置く。

```
✗ /admin/reception            ← 画面上で対象を選ばせる（別の対象を操作する事故が起きる）
✓ /admin/events/[id]/reception ← URL で対象が固定される
```

現場は急いでいる。選択の余地を残すと必ず間違える。**URL で固定してしまう**のが安全。
旧 URL は直近の対象へリダイレクトさせておくと、印刷物やブックマークが生きる。

現場用の画面は、管理画面の他のページと**別の設計にする**。
文字を大きく、ボタンを大きく、絞り込みを最上部に、進捗（`受付 12 / 28`）を常に見せる。

---

## 8. CSS（そのまま使える最小セット）

`globals.css` の末尾に足す。トークンは各案件のブランド色に置き換える。

```css
.admin-shell{display:flex;min-height:100vh;background:#F5F4F0}
.admin-side{width:230px;flex:none;background:var(--ink);color:#EBE7DD;
  display:flex;flex-direction:column;position:sticky;top:0;height:100vh}
.admin-brand{display:flex;align-items:center;gap:10px;padding:20px 18px 18px;
  border-bottom:1px solid #2C2820}
.admin-nav{padding:10px;display:flex;flex-direction:column;gap:2px;overflow-y:auto;flex:1}
.admin-nav a{display:flex;align-items:center;justify-content:space-between;gap:8px;
  padding:9px 12px;border-radius:3px;text-decoration:none;color:#C9C4B6;font-size:13.5px}
.admin-nav a:hover{background:#241F16;color:#fff}
.admin-nav a.on{background:var(--accent);color:#fff;font-weight:700}
.admin-nav .count{font-size:11px;background:rgba(255,255,255,.16);padding:1px 7px;border-radius:9px}
.admin-nav .sep{font-size:10.5px;letter-spacing:.16em;color:#6E6959;padding:16px 12px 6px}
.admin-foot{padding:14px 16px;border-top:1px solid #2C2820;font-size:12px;color:#8A8478}

.admin-main{flex:1;min-width:0;padding:26px 32px 80px}
.admin-head{display:flex;align-items:flex-end;gap:14px;margin-bottom:22px;flex-wrap:wrap}
.admin-head h1{font-size:26px;font-weight:700;letter-spacing:.04em;margin:0}
.admin-head .sub{color:var(--ink-3);font-size:13px;margin:4px 0 0}
.admin-head .actions{margin-left:auto;display:flex;gap:8px;align-items:center}

.panel{background:#fff;border:1px solid var(--line);border-radius:4px;overflow:hidden;margin-bottom:20px}
.panel-head{padding:13px 18px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:12px}
.panel-head .right{margin-left:auto;display:flex;gap:8px;align-items:center}
.panel-body{padding:18px}
.panel th{padding:10px 18px;background:#FAF9F6}
.panel td{padding:12px 18px}
.panel tbody tr:hover{background:#FCFBF7}
.tlink{font-weight:700;color:var(--ink);text-decoration:none}
.tlink:hover{text-decoration:underline}

.stats{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));margin-bottom:22px}
.stat{background:#fff;border:1px solid var(--line);border-radius:4px;padding:16px 18px}
.stat .k{font-size:12px;color:var(--ink-3)}
.stat .v{font-size:30px;font-weight:700;line-height:1.2;margin-top:2px}

.empty{padding:40px 18px;text-align:center;color:var(--ink-3);font-size:13.5px}
.formgrid{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}
.formgrid .wide{grid-column:1 / -1}
.danger-zone{border:1px solid #F0D2CF;background:#FBEDEC;border-radius:4px;padding:16px 18px}
.btn-danger{border-color:#E8C9C6;color:var(--danger)}
.btn-danger:hover{background:#FBEDEC;border-color:var(--danger)}

@media (max-width:880px){
  .admin-shell{display:block}
  .admin-side{width:auto;height:auto;position:static}
  .admin-nav{flex-direction:row;flex-wrap:wrap}
  .admin-nav .sep{display:none}
  .admin-main{padding:20px 16px 60px}
}
```

**空の状態（`.empty`）を必ず作る。** 立ち上げ直後は全部ゼロ件で、
そこに「まだありません」と次の一手のボタンが出るかどうかで、印象がまるで変わる。

---

## 9. 日本語の文言

社内ツールでも、画面の言葉は**運営が使う言葉**にそろえる。

| 避ける | 使う |
|---|---|
| 作成 / 登録 / 編集 | ◯◯を作る / 追加する / 保存する |
| ステータス: active | 状態: 有効 |
| Save / Submit | 保存する / この内容で申し込む |
| エラーが発生しました | いまのパスワードが違います |

DB の enum をそのまま出さない。必ず日本語のラベルに対応表を持つ。
ボタンには**押すと何が起きるか**を書く（「承認」ではなく「承認して案内を送る」）。

---

## 10. 実装の順番

1. `(site)` / `admin/(dash)` のルートグループを先に切る（後から分けるのは面倒）
2. `admin/(dash)/layout.tsx` に認証チェックとサイドバー
3. 主要エンティティごとに 一覧 → 新規 → 詳細 の3枚を作る
4. ダッシュボードは**最後**に作る（何を出すべきかは他の画面ができてから分かる）
5. 現場作業の画面は、対象の詳細配下に足す

## 検証

管理画面は**ログインしないと中が見えない**。ビルドが通っただけで「できた」と言わない。

- 依頼主にログインしてもらい、ブラウザ操作で全画面を実際に見る
- テスト用のレコードを1件作り、一覧 → 詳細 → 作業画面 → 削除まで通して**必ず消す**
- 未ログインで各 URL を叩き、ログイン画面に飛ぶことを確認する
- 利用者側の画面に管理画面へのリンクが混ざっていないか grep で確認する
