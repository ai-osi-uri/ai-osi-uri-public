# 不正アクセスの見張り — ポータルの受け口につなぐ

> create-app の Phase 4（作るとき）と完了の前、update-deploy でログインまわりを直すときに読む。
> ログインのあるアプリは全部が対象（試作でも省かない）。access-control.md の原則 7「おかしな動きを知らせる」の、決まった入れ方。

## なぜか

弱いところ（コードの穴・部品の脆弱性）が無くても、外から攻撃は来る。ログインの総当たり、入口を探して回るアクセス、
漏れたパスコードでのログイン。アプリが黙っていると、誰も気づけない。

見つける仕組みをアプリごとに作ると、入ったり入らなかったりする。だから **アプリは「起きたこと」を送るだけ**にし、
数える・判定する・知らせる・記録を見せるのは、全部ツールポータルが受け持つ。しきい値や届け先を変えるときに、アプリを直さなくてよい。

## アプリが送るもの（4 種類だけ）

| 種類 | いつ送るか |
|---|---|
| `login_failed` | ログインに失敗したとき（パスコード違い・パスワード違い） |
| `login_succeeded` | ログインに成功したとき（見慣れない場所からの成功を見つけるため） |
| `unauthorized` | ログインしていないのに、データの口（API）を呼ばれたとき（401 を返す所） |
| `ping` | 毎日 1 回（Cron）。何も起きていない日も、見張りが止まっていないことをポータルが確かめる |

一緒に送るのは、送信元の IP・国（Vercel なら `x-vercel-ip-country`）・ブラウザの種類・どの口か だけ。
**パスワード・パスコード・メールアドレス・画面の中身（お客さまの情報）は送らない。**

## 部品（Next.js ＋ Vercel の例。ほかの作りでも同じ形で書く）

`lib/intrusion.ts`：

```ts
// 不正アクセスの見張り：ツールポータルの受け口に「起きたこと」を送る。
// INTRUSION_URL と INTRUSION_KEY の両方があるときだけ送る。届かなくてもアプリの動きは止めない（1.5 秒で諦める）。
export type IntrusionKind = 'login_failed' | 'login_succeeded' | 'unauthorized' | 'ping';

export function intrusionEnabled(): boolean {
  return Boolean(process.env.INTRUSION_URL && process.env.INTRUSION_KEY);
}

function clientIp(h: Headers): string | null {
  const xff = h.get('x-forwarded-for');
  return (xff ? xff.split(',')[0].trim() : h.get('x-real-ip')) || null;
}

export async function reportIntrusion(kind: IntrusionKind, req?: { headers: Headers; nextUrl?: { pathname: string } }): Promise<void> {
  if (!intrusionEnabled()) return;
  const h = req?.headers;
  const event = {
    kind,
    ip: h ? clientIp(h) : null,
    country: h?.get('x-vercel-ip-country') ?? null,
    ua: h?.get('user-agent')?.slice(0, 200) ?? null,
    route: req?.nextUrl?.pathname ?? null,
  };
  try {
    await fetch(process.env.INTRUSION_URL!, {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: `Bearer ${process.env.INTRUSION_KEY}` },
      body: JSON.stringify({ events: [event] }),
      signal: AbortSignal.timeout(1500),
      cache: 'no-store',
    });
  } catch {
    // 届かなくても止めない
  }
}

/** 見つけたら止める：ログインを確かめる前に聞く。止められていれば残り秒数。ポータルに届かないときは止めない（0） */
export async function intrusionBlockedFor(req: { headers: Headers }): Promise<number> {
  if (!intrusionEnabled()) return 0;
  const ip = clientIp(req.headers);
  if (!ip) return 0;
  try {
    const res = await fetch(process.env.INTRUSION_URL!.replace(/\/events$/, '/check'), {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: `Bearer ${process.env.INTRUSION_KEY}` },
      body: JSON.stringify({ ip }),
      signal: AbortSignal.timeout(1500),
      cache: 'no-store',
    });
    if (!res.ok) return 0;
    const j = (await res.json()) as { retry_after?: number };
    return Math.max(0, Number(j.retry_after) || 0);
  } catch {
    return 0;
  }
}
```

呼ぶ場所：

| 場所 | 入れ方 |
|---|---|
| ログインの口（`/api/login` など） | **まず** `const wait = await intrusionBlockedFor(req)`。`wait > 0` なら、パスコードを確かめずに 429（`retry-after` に秒数）で断り、画面には「間違いが続いたため、この端末からのログインを止めています。約◯分後にもう一度」と出す。そのあと、失敗を返す直前に `await reportIntrusion('login_failed', req)`、成功の直前に `await reportIntrusion('login_succeeded', req)` |
| 関所（`middleware.ts`） | ログインしていない API の呼び出しに 401 を返す所で `event.waitUntil(reportIntrusion('unauthorized', req))`（返事を待たせない。`middleware(req, event: NextFetchEvent)`） |
| つながりの知らせ | `app/api/intrusion/ping/route.ts` で `reportIntrusion('ping')`。`vercel.json` の `crons` に毎日 1 回（例 `"10 21 * * *"`）。関所の「ログインなしで通す道」に足す。`CRON_SECRET` があれば `Authorization` を確かめる |
| `/api/health` | `intrusion: intrusionEnabled()` を足す（つないだかを外から確かめられる） |
| `.env.example` | `INTRUSION_URL=` と `INTRUSION_KEY=` を足す |

ログインの作り方による違い：

- **自前のパスコード・パスワード**：上の表のとおり。
- **Supabase Auth を画面から直接呼ぶ作り**：失敗はアプリのサーバを通らないので、送れない。ログインは自前のサーバの口
  （`/api/login` でサーバ側から `signInWithPassword` を呼ぶ）を通す作りにして、そこで送る。メールのリンクだけでログインする作りは、
  `login_failed` は無くてよい（`unauthorized` と `ping` は送る）。

## つなぐ（鍵を会話に出さない）

公開したあと、URL のコネクタの道具でつなぐ。**鍵の値を読む・会話に出す・人に貼ってもらう、はしない。**

1. `vercel_set_env`：`key: INTRUSION_KEY`・`from_extension: intrusion_key`（このアプリの受け口の鍵を出して、値を見せずに入れる。出し直すと前の鍵は使えなくなる）
2. `vercel_set_env`：`key: INTRUSION_URL`・`value:` ポータルの受け口（`vercel_set_env` の説明に書いてある URL）・`type: plain`
3. `vercel_redeploy` で作り直す

案件台帳に結びついていない Vercel プロジェクトには鍵を出せない（先に案件として台帳に載せる）。
Vercel 以外（Cloud Run・AWS など）は、ポータルのアプリ詳細 → セキュリティ → 外からのアクセス → 「つなぐ」で鍵を出し、
その仕組みの鍵の置き場（Secret Manager など）に本人が入れる。

## 確かめる（完了の条件）

1. `/api/health` が `intrusion: true` を返す
2. `ping` の口を 1 回呼ぶ（Cron を待たない） → ポータルのアプリ詳細 → セキュリティの「外からのアクセス」が「いまは大丈夫です」になる
3. 間違ったパスコードで、続けてログインを失敗させる（同じ IP から 10 回、または合わせて 30 回）→ 検知が 1 件立つ
   （送信元の IP が毎回変わる環境では、同じ IP の決まりに当たらず「合わせて 30 回」で立つ。これは正しい動き）
4. 続けて失敗させると、途中から 429（止めている）が返る。送信元の IP が毎回変わる環境では、合わせて 30 回を超えたあと、3 回失敗した IP から止まる
5. 立った検知を開いて「テストだった」と書いて「確認した」で閉じる。完了レポートに「不正アクセスの見張り：つないだ・検知を確かめた」と書く

## 見つけたら止める（決まり）

- 止めるのは**その送り元（IP）だけ**。全体を止めると、攻撃する側がお店の人を締め出せてしまう。
- 同じ IP から 15 分で 10 回失敗 → 最後の失敗から 15 分止める。場所を変えた総当たりの最中（直近 5 分に合わせて 30 回以上）は、3 回失敗した IP から止める。
- ポータルに届かないときは止めない（ログインできなくなる方が困る）。これで access-control.md の原則 6（入口に回数の上限）を満たす。

## まだ入っていないもの（入れたら、ここを直す）

- しきい値と届け先（LINE・メール・お客さまの監視の仕組み）を変える画面
