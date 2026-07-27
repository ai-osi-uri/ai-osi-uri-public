# デプロイ落とし穴集（gotchas）

過去のデプロイ経験から蓄積した「踏んだら痛い」パターンを集約したリファレンス。
新規アプリ作成時に必ず目を通し、同じ轍を踏まないようにする。

---

## 1. Stripe は Deploy 拡張経由（test がデフォルト）

**問題**: 旧 standalone Stripe MCP を使うと、認証・モード管理が二重になり混乱する。

**ルール**:
- Stripe 操作はすべて **AI OSI URI Deploy コネクタ** 経由で行う
- デフォルトは `mode: "test"`（テストモード）
- 本番に切り替えるときは `confirm_live: true` を明示的に指定する
- 旧 standalone Stripe MCP は使わない（残っていたら接続を外す）

**確認コマンド例**:
```
stripe_create_product_and_price  →  mode: "test" が既定
stripe_create_payment_link       →  mode: "test" が既定
```

**本番切替時の手順**:
1. テストモードで全フローを検証完了
2. `switch-to-live-mode` スキルを使用
3. `confirm_live: true` を付与して本番オブジェクトを作成

---

## 2. Next.js Server Component キャッシュは最初から無効化

**問題**: `revalidate: 60` などのキャッシュ設定を入れると、データ更新が反映されず「固着」する事故が起きる。デモ中に「さっき変えたのに反映されない」となると致命的。

**ルール**: 初期段階では **最初からキャッシュを無効化** する。

**必ず入れる設定**:
```typescript
// app/layout.tsx または各ページ先頭
export const dynamic = "force-dynamic";

// fetch を使う場合
const res = await fetch(url, { cache: "no-store" });
```

**やってはいけないこと**:
- `revalidate: 60` などの ISR 設定を「とりあえず」で入れる
- `generateStaticParams` を動的データに対して使う

**パフォーマンス最適化はいつやるか**:
- 本番運用が安定し、顧客が「速度が気になる」と言ったタイミングで初めて検討する
- その際も `revalidate` ではなく、CDN キャッシュ（Vercel Edge Config 等）を先に検討

---

## 3. Next.js dynamic route x 日本語マルチバイト handle

**問題**: `[slug]` や `[category]` に日本語が入ると、URL エンコード/デコードの不一致でページが見つからない。ブラウザが二重エンコードするケースもある。

**ルール**: デコードは多段で行い、一覧からの find フォールバックを必ず併用する。

**実装パターン**:
```typescript
// app/products/[category]/page.tsx

export default async function Page({
  params,
}: {
  params: { category: string };
}) {
  // 多段デコード（二重エンコード対策）
  let decoded = params.category;
  try {
    decoded = decodeURIComponent(decoded);
    // まだエンコードされていれば更にデコード
    if (decoded !== decodeURIComponent(decoded)) {
      decoded = decodeURIComponent(decoded);
    }
  } catch {
    // デコード失敗時はそのまま使う
  }

  // 完全一致で見つからなければ一覧から find フォールバック
  let item = items.find((i) => i.slug === decoded);
  if (!item) {
    item = items.find(
      (i) =>
        i.slug === encodeURIComponent(decoded) ||
        encodeURIComponent(i.slug) === params.category
    );
  }

  if (!item) return notFound();
  // ...
}
```

**テスト必須項目**:
- 日本語カテゴリ名でのアクセス（例: `/products/和菓子`）
- ブラウザのアドレスバーからのコピペアクセス
- リンクからの遷移

---

## 4. localStorage はスキーマ変更時に LS_KEY のバージョンを上げる

**問題**: localStorage に保存したデータのスキーマ（構造）を変更すると、旧データを読み込んで `undefined.gid` 系のエラーが発生する。ユーザーのブラウザにはクリアするまで旧データが残り続ける。

**ルール**: スキーマを変更したら **LS_KEY のバージョンを上げる**。読み込み時にバリデーションし、不正なら破棄する。

**実装パターン**:
```typescript
// v1 → v2 にスキーマ変更した場合
const LS_KEY = "myapp-cart-v2"; // ← バージョンを上げる

function loadCart(): Cart {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return DEFAULT_CART;

    const parsed = JSON.parse(raw);

    // バリデーション: 必須フィールドの存在確認
    if (!parsed.items || !Array.isArray(parsed.items)) {
      localStorage.removeItem(LS_KEY);
      return DEFAULT_CART;
    }

    // 各アイテムのスキーマ検証
    const valid = parsed.items.every(
      (item: any) => item.id && item.quantity != null
    );
    if (!valid) {
      localStorage.removeItem(LS_KEY);
      return DEFAULT_CART;
    }

    return parsed;
  } catch {
    localStorage.removeItem(LS_KEY);
    return DEFAULT_CART;
  }
}
```

**チェックリスト**:
- [ ] スキーマ変更時に LS_KEY のサフィックスバージョンを上げたか
- [ ] `JSON.parse` を try-catch で囲んでいるか
- [ ] 必須フィールドのバリデーションを入れたか
- [ ] バリデーション失敗時に旧データを破棄しているか

---

## 5. Vercel デプロイは「Push 成功」と「Build 成功」を分けて確認

**問題**: GitHub への Push が成功しても、Vercel の Build が失敗していることがある。Push 成功だけで「デプロイ完了」と報告すると嘘になる。

**ルール**: 3段階で確認する。

**確認手順**:

### Step 1: Push のコミットが Vercel に認識されたか
```
vercel_get_deployment_status で最新デプロイを取得
→ meta.githubCommitSha が push したコミットハッシュと一致するか
```

### Step 2: Build が成功したか
```
readyState === "READY" を確認
（"BUILDING" / "ERROR" / "CANCELED" ではないこと）
```

### Step 3: 中身が正しいか
```bash
curl -s https://your-app.vercel.app | head -20
# 期待するタイトルやコンテンツが含まれているか
```

**よくある Build 失敗原因**:
- TypeScript の型エラー（ローカルでは warning だが Vercel では error）
- 環境変数の未設定（Vercel の Environment Variables に入れ忘れ）
- Node.js バージョンの不一致

---

## 6. GitHub PAT 期限切れの突然死対策

**問題**: GitHub Personal Access Token (PAT) は期限付きで発行されることが多く、期限切れに気づかず突然デプロイできなくなる。

**ルール**: 発行日と期限を記録し、デプロイ前に疎通確認する。

**`.env` への注記**:
```bash
# GitHub PAT（発行日: 2026-01-15 / 期限: 2026-07-15）
# ⚠️ 期限切れ前に再発行すること
GITHUB_PAT=ghp_xxxxxxxxxxxx
```

**デプロイ前の疎通確認**:
```bash
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: token $GITHUB_PAT" \
  https://api.github.com/user
# → 200 なら OK / 401 なら期限切れ
```

**予防策**:
- PAT 発行時に期限をカレンダーに登録（期限の 1 週間前にリマインダー）
- 可能なら Fine-grained PAT を使い、必要最小限のスコープにする
- チーム共有の PAT は避け、個人 PAT を使う

---

## 7. 顧客サイトと管理画面は最初から完全分離

**問題**: 「あとから分ければいい」と同じ layout に顧客サイトと管理画面を混ぜると、ナビゲーション・配色・認証が絡み合って分離コストが膨大になる。

**ルール**: **最初から route group で分離する**。

**ディレクトリ構成**:
```
app/
├── (shop)/          # 顧客向けサイト
│   ├── layout.tsx   # 顧客用レイアウト（配色・書体・ナビ）
│   ├── page.tsx     # トップページ
│   └── products/
│       └── [slug]/
│           └── page.tsx
├── admin/           # 管理画面
│   ├── layout.tsx   # 管理用レイアウト（別配色・別書体・別ナビ）
│   ├── page.tsx     # ダッシュボード
│   └── products/
│       └── page.tsx
└── layout.tsx       # ルートレイアウト（共通の <html>/<body> のみ）
```

**分離すべき要素**:
| 要素 | 顧客サイト (shop) | 管理画面 (admin) |
|------|-------------------|------------------|
| 配色 | ブランドカラー | ニュートラル（灰/白） |
| 書体 | ブランドフォント | システムフォント |
| ナビ | 商品カテゴリ中心 | CRUD 操作中心 |
| 認証 | 不要 or 顧客ログイン | 管理者認証必須 |

---

## 8. route group (shop) の括弧はシェルで quote する

**問題**: `(shop)` のような route group ディレクトリは、シェルが括弧をサブシェルや glob として解釈してしまい、`cp` / `mv` / `find` が意図通り動かない。

**ルール**: シェルコマンドで括弧付きパスを扱うときは **必ずクォートで囲む**。

**正しい書き方**:
```bash
# ダブルクォートで囲む
cp src.tsx "app/(shop)/page.tsx"
mv "app/(shop)/old.tsx" "app/(shop)/new.tsx"
find "app/(shop)" -name "*.tsx"

# シングルクォートでも OK
cp src.tsx 'app/(shop)/page.tsx'
```

**間違い（エラーになる）**:
```bash
# クォートなし → シェルが括弧を解釈してエラー
cp src.tsx app/(shop)/page.tsx        # NG
find app/(shop) -name "*.tsx"         # NG
```

**エスケープでも可（ただし読みにくい）**:
```bash
cp src.tsx app/\(shop\)/page.tsx
```

---

## 9. 構成選定：「説明のシンプルさ」を最初に評価

**問題**: Headless Shopify + Stripe + Supabase + Vercel のような多サービス連携構成は、1つのサービスの仕様変更で全体が壊れる。顧客への説明も複雑になり、手戻りリスクが高い。

**ルール**: 構成を決める前に「説明のシンプルさ」を最初に評価する。

**構成選定チェックリスト**:

| # | 評価項目 | 合格基準 |
|---|----------|----------|
| 1 | 顧客に構成を 1 文で説明できるか | 「Next.js でサイトを作り、Stripe で決済します」レベル |
| 2 | サービス間の依存が 2 つ以下か | A→B→C までは OK、A→B→C→D は危険 |
| 3 | 各サービスの無料枠で検証可能か | 検証段階で課金が必要なサービスは避ける |
| 4 | 障害時に原因特定が 1 サービスに絞れるか | 「Stripe か Shopify かわからない」は NG |
| 5 | 顧客が自分でデータを見れるか | ダッシュボードや管理画面があるか |

**判定**:
- 5 項目中 4 つ以上合格 → その構成で進める
- 3 つ以下 → 構成を簡素化する（サービスを減らす・自前実装に置き換える）

**よくある過剰構成の例**:
- Headless Shopify + 別 CMS + Stripe + Supabase → Supabase + Stripe だけで済むことが多い
- Firebase Auth + Supabase DB + Vercel → Supabase Auth + DB に統一

---

## 10. 顧客向けご案内資料に含める項目

**問題**: アプリを作って渡すだけだと、顧客が「何を見ればいいか」「どこに連絡すればいいか」がわからない。

**ルール**: 納品時に必ず以下の項目を含むご案内資料を作成する。

**必須項目**:

### A. URL と認証情報
```
公開 URL: https://example.vercel.app
管理画面: https://example.vercel.app/admin
管理者メール: admin@example.com
初期パスワード: （別途お知らせ）
```

### B. 確認ポイント（3-5 個）
顧客に「ここを見てください」と伝える具体的なポイント。
```
1. トップページが正しく表示されるか
2. 商品一覧の写真と価格が正しいか
3. カートに入れて決済画面まで進めるか
4. 管理画面でログインして商品を編集できるか
5. スマートフォンで表示が崩れていないか
```

### C. デモ版の制約と本番解消
```
【デモ版の制約（現在）】
- 決済はテストモード（実際の課金は発生しません）
- テスト用カード番号: 4242 4242 4242 4242

【本番リリース時に解消される項目】
- 決済が本番モードに切り替わり、実際の入金が発生します
- 独自ドメインが設定されます
- SSL 証明書が有効になります
```

### D. 連絡先
```
ご不明点・修正依頼:
- Slack: #proj-xxxxx チャンネル
- メール: support@ai-osi-uri.com
- 担当: ○○
```
