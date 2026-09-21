# アプリに判定（Jev）を組み込む

アプリの中に「振り分ける・チェックする・分類する・点数をつける」処理があるときの標準形。
文章を書く・要約する処理は従来どおり Claude（`ANTHROPIC_API_KEY`）で作る。**判定の部分だけを Jev にする。**

## なぜ Jev にするか（提案で説明する言葉）

- 1 回の判定がほぼ無料（100 万トークンで約 6 円）で速い。使う人が増えても毎月の費用がほとんど増えない。
- 同じ入力には毎回同じ答えが返る（Claude に判定させると回ごとにぶれる）。
- 答えに「どれくらい自信があるか」が付くので、自信が低いものだけ人に確認させる画面が作れる。

## 鍵（誰の鍵を入れるか）

- **お客様に納めるアプリは、お客様自身の TypeSafe の鍵を使う。** 当社の鍵（拡張設定・共用の鍵）はアプリに入れない。
  データと費用がお客様の名義で分かれるため。
  - お客様に TypeSafe の順番待ち登録 → アカウント作成 → 鍵の発行をしてもらい、`credential-handoff` で
    Vercel（または AWS）の環境変数 `TYPESAFE_API_KEY` に直接貼ってもらう（値は Claude を通さない）。
- **当社内のデモ・見本**は当社の鍵でよい。本番へ移すときにお客様の鍵へ差し替える（差し替えを完了レポートの「次にやること」に書く）。
- 鍵がまだ無い間も**アプリは動くようにする**: `TYPESAFE_API_KEY` が空なら判定をせず「確認待ち」に回す（下の部品がそうなっている）。

## 設計のきまり

1. 判定ごとに問いを 1 つ決め、`lib/jev.ts` の問い一覧に置く（画面や API の中に問いを散らさない）。
2. **自信が低いもの（unsure）は必ず人が確認する画面・状態を用意する**（「確認待ち」一覧など）。自動で確定させない。
3. 金額・日付・件数の判断はコードで行い、Jev には聞かない。
4. 医療情報（患者・検査結果）を扱うアプリでは、Jev に送る前にお客様と送ってよい範囲を決め、決定を `nonfunctional.yaml` に書く。
5. 判定結果（答え・自信・モデルの版）を DB に残す。閾値の見直しに使う。本番では `model` を `jev-1.13.0` のように版で固定する。
6. 問いは、20〜50 件の実データで正解率を見てから本番に入れる（`osi-core:jev-judge` の「検証済みの問い」の手順）。

## 部品（Next.js / サーバ側だけで使う）`lib/jev.ts`

```ts
// サーバ側専用（鍵をブラウザに出さない）。Route Handler / Server Action から呼ぶ。
const API = "https://api.typesafe.ai/v1/systemone";
const MODEL = process.env.TYPESAFE_MODEL || "jev-1.13.0";

export type Question =
  | { type: "noul"; instructions: string }
  | { type: "choice"; instructions: string; criteria: Record<string, string> }
  | { type: "score"; instructions: string; criteria: string[] };

export type Verdict = {
  status: "decided" | "needs_review" | "unavailable";
  answers: Record<string, { value: string | number | boolean | null; confidence: number }>;
  model?: string;
};

/** 1 件の文章に問いをまとめて聞く。自信が threshold 未満（noul は 0.2〜0.8）の問いがあれば needs_review */
export async function judge(state: string, questions: Record<string, Question>, threshold = 0.8): Promise<Verdict> {
  const key = process.env.TYPESAFE_API_KEY;
  if (!key) return { status: "unavailable", answers: {} };
  const res = await fetch(API, {
    method: "POST",
    headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
    body: JSON.stringify({ model: MODEL, state: state.slice(0, 30000), questions }),
  });
  if (!res.ok) return { status: "unavailable", answers: {} };
  const json = await res.json();
  let review = false;
  const answers: Verdict["answers"] = {};
  for (const [id, a] of Object.entries<any>(json.answers ?? {})) {
    if (a.type === "noul") {
      answers[id] = { value: a.noul >= 0.5, confidence: Math.abs(a.noul - 0.5) * 2 };
      if (a.noul > 0.2 && a.noul < 0.8) review = true;
    } else {
      answers[id] = { value: a.type === "choice" ? a.choice : a.score, confidence: a.confidence ?? 0 };
      if ((a.confidence ?? 0) < threshold) review = true;
    }
  }
  return { status: review ? "needs_review" : "decided", answers, model: json.model };
}
```

- `status: "unavailable"`（鍵が無い・API が落ちている）のときも処理を止めず、「確認待ち」に回す。
- 使う側の例: 問い合わせフォームの送信時に `judge(本文, { kind: {type:"choice", …}, urgent: {type:"noul", …} })` → `decided` なら担当へ自動で振り分け、それ以外は確認待ち一覧へ。
