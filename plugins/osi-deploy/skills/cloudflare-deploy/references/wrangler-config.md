# wrangler.jsonc テンプレ集（フレームワーク別）

`cloudflare-deploy` スキルの Step 2 で使う。**`compatibility_date` は必ず作業時点の日付**に
差し替える（テンプレの日付をそのまま残さない）。

共通の注意:

- **`vars` に秘密を書かない**。リポに平文で入る。API キー類は `cloudflare_set_secret`。
- `d1_databases[].database_id` / `kv_namespaces[].id` は `cloudflare_d1_create` /
  `cloudflare_kv_create_namespace` の戻り値 `wrangler_snippet` をそのまま貼る。
- `observability.enabled: true` を入れておく（後からログを見られる。無料）。
- `wrangler.toml` でも動くが、**新規は jsonc 推奨**（コメントが書けて差分が読みやすい）。

---

## パターン A: SPA（Vite + React）+ API Worker + D1 — 既定の推奨形

いちばん壊れにくく、フル Cloudflare の利点（コールドスタート無し・エグレス無料）を
そのまま受けられる構成。認証が要らない、または Cloudflare Access で前段認証する案件向け。

```jsonc
{
  "$schema": "node_modules/wrangler/config-schema.json",
  "name": "flower-inventory",
  "main": "./src/worker.ts",
  "compatibility_date": "2026-08-01",
  "compatibility_flags": ["nodejs_compat"],

  // ./dist にビルドされた SPA を配信し、マッチしないものだけ Worker に流す
  "assets": {
    "directory": "./dist",
    "binding": "ASSETS",
    "not_found_handling": "single-page-application",
    // API だけは必ず Worker を先に通す（静的ファイルと衝突させない）
    "run_worker_first": ["/api/*"]
  },

  "observability": { "enabled": true },

  "d1_databases": [
    {
      "binding": "DB",
      "database_name": "flower-inventory-db",
      "database_id": "<cloudflare_d1_create の database_id>"
    }
  ],

  "r2_buckets": [
    { "binding": "BUCKET", "bucket_name": "flower-inventory-assets" }
  ],

  "kv_namespaces": [
    { "binding": "KV", "id": "<cloudflare_kv_create_namespace の id>" }
  ],

  // 秘密でない設定値だけ
  "vars": { "APP_ENV": "production" }
}
```

対応する `src/worker.ts`（Hono）:

```ts
import { Hono } from "hono";

type Env = {
  DB: D1Database;
  BUCKET: R2Bucket;
  KV: KVNamespace;
  ANTHROPIC_API_KEY: string; // cloudflare_set_secret で投入（vars に書かない）
};

const app = new Hono<{ Bindings: Env }>();

app.get("/api/items", async (c) => {
  const { results } = await c.env.DB.prepare(
    "SELECT id, name, stock FROM items ORDER BY name"
  ).all();
  return c.json(results);
});

app.post("/api/items", async (c) => {
  const { name, stock } = await c.req.json<{ name: string; stock: number }>();
  // 必ずプレースホルダで bind する（SQL 文字列連結は禁止）
  await c.env.DB.prepare("INSERT INTO items (name, stock) VALUES (?, ?)")
    .bind(name, stock)
    .run();
  return c.json({ ok: true }, 201);
});

export default app;
```

`package.json`:

```json
{
  "scripts": {
    "build": "vite build",
    "dev": "vite",
    "cf:types": "wrangler types"
  },
  "devDependencies": { "wrangler": "^4.0.0" },
  "dependencies": { "hono": "^4.0.0" }
}
```

`cloudflare_deploy_worker` は `package.json` の `build` を自動で拾う。

---

## パターン B: Next.js（App Router）— OpenNext アダプタ経由

Workers は Node.js ランタイムではないので、Next.js は**素の `next build` では動かない**。
`@opennextjs/cloudflare` でビルド成果物を Worker 形式に変換する。

```
npm install @opennextjs/cloudflare@latest
npm install --save-dev wrangler@latest
```

`open-next.config.ts`:

```ts
import { defineCloudflareConfig } from "@opennextjs/cloudflare";
import r2IncrementalCache from "@opennextjs/cloudflare/overrides/incremental-cache/r2-incremental-cache";

export default defineCloudflareConfig({
  incrementalCache: r2IncrementalCache,
});
```

`wrangler.jsonc`:

```jsonc
{
  "name": "my-next-app",
  "main": ".open-next/worker.js",
  "compatibility_date": "2026-08-01",
  "compatibility_flags": ["nodejs_compat", "global_fetch_strictly_public"],
  "assets": { "directory": ".open-next/assets", "binding": "ASSETS" },
  "observability": { "enabled": true },
  "services": [
    { "binding": "WORKER_SELF_REFERENCE", "service": "my-next-app" }
  ],
  "d1_databases": [
    { "binding": "DB", "database_name": "my-next-app-db", "database_id": "<id>" }
  ]
}
```

デプロイ時は build コマンドを明示する（`next build` だけでは足りない）:

```
cloudflare_deploy_worker({
  repo_dir,
  build_command: "npx opennextjs-cloudflare build"
})
```

`services.binding` の `service` は **自分の Worker 名と一致**させる（自己参照）。
名前を変えたらここも直す。

> **判断**: Next.js の機能（ISR / middleware / server actions）をフルに使う案件で、
> OpenNext のビルドが通らずに時間を溶かしそうなら、**Vercel パスに戻す**判断を早めに出す。
> 「Cloudflare に寄せること」自体は目的ではない。

---

## パターン C: 静的サイトのみ（LP・コーポレート）

API が要らないなら `main` も不要。Worker コードゼロで配信できる。

```jsonc
{
  "name": "corp-lp",
  "compatibility_date": "2026-08-01",
  "assets": { "directory": "./dist" },
  "observability": { "enabled": true }
}
```

---

## D1 マイグレーション

`migrations/` 配下に連番 SQL を置く。ファイル名の連番が適用順。

`migrations/0001_init.sql`:

```sql
CREATE TABLE IF NOT EXISTS items (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  name       TEXT    NOT NULL,
  stock      INTEGER NOT NULL DEFAULT 0,
  created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_items_name ON items (name);
```

適用（**`--remote` 必須**。付けないとローカル SQLite にしか当たらない）:

```
cloudflare_wrangler({
  repo_dir,
  args: ["d1", "migrations", "apply", "flower-inventory-db", "--remote"]
})
```

適用済み確認:

```
cloudflare_d1_query({
  database: "flower-inventory-db",
  sql: "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
})
```

### D1（SQLite）で Postgres と違うところ

Supabase から移す場合の主な差分。これを知らずに Postgres 前提のスキーマを流すと落ちる。

| Postgres | D1 / SQLite | 対処 |
|---|---|---|
| `SERIAL` / `IDENTITY` | 無い | `INTEGER PRIMARY KEY AUTOINCREMENT` |
| `uuid` 型・`gen_random_uuid()` | 無い | `TEXT` に `crypto.randomUUID()` をアプリ側で入れる |
| `timestamptz` / `now()` | 無い | `TEXT` に `datetime('now')`（UTC）。TZ はアプリで扱う |
| `jsonb` + 演算子 | `TEXT` + `json_extract()` | クエリの書き換えが必要 |
| `boolean` | `INTEGER` 0/1 | アプリ側で変換 |
| RLS（行レベルセキュリティ） | **無い** | 認可を全部アプリコードで担保する（設計上いちばん重要な差分） |
| `ILIKE` | 無い | `LIKE`（SQLite は既定で ASCII 大小無視）or `lower()` 比較 |

**RLS が無い**点は特に注意。Supabase では DB が最後の防壁になっていたが、D1 では
アプリのハンドラが唯一の防壁になる。テナント ID / ユーザー ID の絞り込みを
共通ヘルパに集約し、クエリごとに書かない。

---

## R2 の使い方（最小）

```ts
// アップロード
await c.env.BUCKET.put(`invoices/${id}.pdf`, await c.req.arrayBuffer(), {
  httpMetadata: { contentType: "application/pdf" },
});

// 取得（公開せずに Worker 経由で出す＝認可をかけられる）
const obj = await c.env.BUCKET.get(`invoices/${id}.pdf`);
if (!obj) return c.notFound();
return new Response(obj.body, {
  headers: { "content-type": obj.httpMetadata?.contentType ?? "application/octet-stream" },
});
```

バケットを公開 URL で直接配信することもできるが、**業務データは Worker 経由**にして
認可を通す。公開してよいのは画像・静的アセットだけ。

---

## KV の使い方（セッション・レート制限）

```ts
// セッション（TTL つき）
await c.env.KV.put(`sess:${sid}`, JSON.stringify({ userId }), { expirationTtl: 60 * 60 * 24 });
const raw = await c.env.KV.get(`sess:${sid}`);
```

KV は**結果整合性**（書いた直後に別リージョンで古い値が返ることがある）。
「書いた値を即座に厳密に読む」用途には使わない。それは D1 を使う。

---

## ローカル開発

```
npx wrangler dev          # D1/KV/R2 はローカルエミュレート
npx wrangler dev --remote # 本番リソースに繋ぐ（データを壊しうるので注意）
```

`wrangler dev` は対話プロセスなので `cloudflare_wrangler` からは実行しない
（ユーザーが自分のターミナルで叩く）。

型定義の生成:

```
cloudflare_wrangler({ repo_dir, args: ["types"] })
```

`worker-configuration.d.ts` が生成され、`env.DB` などに型が付く。バインディングを
足したら毎回これを流す。
