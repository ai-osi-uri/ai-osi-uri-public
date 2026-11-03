# アプリに SMS の本人確認を入れる（Twilio Verify）

会員登録・ログイン・大事な操作の前に「その携帯を本人が持っているか」を確かめたいときに使う。
確認コードを作る・送る・照合するのは Twilio Verify で、アプリはコードを持たない（DB にコードを書かない）。

## 使う条件

- 会社の鍵（または本人の鍵）に Twilio の 3 点（アカウント SID・API キー SID・Secret）が入っている
  （道具 `twilio_status` が返れば入っている。返らなければ `credential-handoff` で鍵設定の「SMS を送る（Twilio）」へ）
- 送れるのは**日本の携帯（070・080・090）だけ**。海外の番号は受け付けない作りにする

## 手順（Claude がやる）

1. 道具 `twilio_verify_create` に `app_name` を渡す（相手の SMS に「◯◯の確認コード」と出る名前。英数字 30 文字まで）。
   アプリごとに 1 つ作る（同じ名前があればそれを使う）。返った SID（VA…）は秘密ではない
2. アプリに環境変数を入れる（値は会話に出さない）

   | 環境変数 | 入れ方（Vercel） | 入れ方（Cloud Run） |
   |---|---|---|
   | `TWILIO_VERIFY_SERVICE_SID` | `vercel_set_env` の `value` に 1. の SID | `gcp_secret_put` ではなく通常の環境変数 |
   | `TWILIO_API_KEY_SID` | `vercel_set_env` の `from_extension: "twilio_api_key_sid"` | `gcp_secret_put`（`twilio_api_key_sid`） |
   | `TWILIO_API_KEY_SECRET` | `vercel_set_env` の `from_extension: "twilio_api_key_secret"`・`type: "sensitive"` | `gcp_secret_put`（`twilio_api_key_secret`） |

3. 下のサーバー側のコードを入れ、`vercel_redeploy` で反映する
4. 本人の携帯で 1 回通す（コードが届く → 入れる → 通る／違うコードで止まる）

## コード（サーバー側だけ。画面のコードに鍵を置かない）

```ts
// lib/sms-verify.ts — 確認コードを送る・照合する（Twilio Verify）
const VERIFY = "https://verify.twilio.com/v2";
const auth = () => `Basic ${Buffer.from(`${process.env.TWILIO_API_KEY_SID}:${process.env.TWILIO_API_KEY_SECRET}`).toString("base64")}`;

/** 日本の携帯だけを +81 の形にそろえる。それ以外は null */
export function jpMobile(raw: string): string | null {
  const v = raw.replace(/[\s\-()（）ー－]/g, "");
  if (/^\+81[789]0\d{8}$/.test(v)) return v;
  if (/^0[789]0\d{8}$/.test(v)) return `+81${v.slice(1)}`;
  return null;
}

async function call(path: string, form: Record<string, string>) {
  const res = await fetch(`${VERIFY}/Services/${process.env.TWILIO_VERIFY_SERVICE_SID}/${path}`, {
    method: "POST",
    headers: { authorization: auth(), "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams(form).toString(),
    signal: AbortSignal.timeout(15_000),
  });
  return (await res.json().catch(() => ({}))) as { status?: string; message?: string };
}

export async function sendCode(phone: string) {
  const to = jpMobile(phone);
  if (!to) return { sent: false, reason: "日本の携帯番号を入れてください" };
  const r = await call("Verifications", { To: to, Channel: "sms", Locale: "ja" });
  return { sent: r.status === "pending", reason: r.message };
}

export async function checkCode(phone: string, code: string) {
  const to = jpMobile(phone);
  if (!to || !/^\d{4,10}$/.test(code)) return { ok: false };
  const r = await call("VerificationCheck", { To: to, Code: code });
  return { ok: r.status === "approved" };
}
```

## 守ること

- **送る回数を数える**：同じ番号・同じ人には 1 分に 1 回・1 日 5 回まで、など上限を DB で数えてから `sendCode` を呼ぶ（SMS は 1 通ごとにお金がかかる。悪用されると請求が膨らむ）
- **照合の回数を数える**：同じ番号で 5 回間違えたら止める（Twilio 側でも止まるが、アプリでも数える）
- **通ったことだけを記録する**：「◯月◯日 ◯時に末尾 1234 の携帯で確認した」を残す。コードそのものは残さない
- 画面には番号の末尾 4 桁だけを出す（「末尾 1234 の携帯に送りました」）
- 鍵（`TWILIO_API_KEY_SECRET`）は会社の Twilio と同じ鍵。ブラウザに渡す変数（`NEXT_PUBLIC_*`）には絶対に入れない
