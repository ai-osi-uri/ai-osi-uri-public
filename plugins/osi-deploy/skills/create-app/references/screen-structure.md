# 画面構成の原則 — ナビはオブジェクト、動詞は画面の中、横幅は画面いっぱい、待ちは必ず見せる

> create-app Phase 1-C から必ず読む。業務アプリの画面を組むときの、構造の決め方。
> 配色・余白・部品の見た目はここでは扱わない（デザインシステムの担当）。

## 原則（3行）

**1. ナビゲーション（サイドバー・上部メニュー）に並べるのは「オブジェクトの一覧」だけ。
「〜する」（動詞）は、そのオブジェクトの画面の中のボタンに置く。**

**2. 本文は画面の横幅いっぱいに使う。中央に寄せて左右を余らせない。**

**3. 画面遷移とボタンの処理には、必ずローディング表示を付ける。押したのに何も起きない時間を作らない。**

## なぜか

### 1. ナビはオブジェクト

人は「何をするか」より先に「何を見るか」で画面を探す。
メニューに動詞（注文を入れる・取り込む・使い方を見る）と名詞（受注票の一覧）が同じ列に混ざると、

- やりたいことが増えるたびにメニューの項目が増え、迷子になる
- 「この操作はどのオブジェクトに効くのか」が見えなくなる
- 一覧画面の右上に置けば済むボタンが、別画面として独立し、戻る導線が要るようになる

名詞だけが並んでいれば、動詞はそのオブジェクトの画面に自然に集まり、項目は増えない。
Salesforce・Notion・Linear など、業務アプリの定番はみなこの作りになっている。

### 2. 横幅は画面いっぱい

業務アプリの本文は、一覧（表）と入力欄が主役。表は列が多いほど横幅が要り、
中央に寄せて左右を余らせると、列が折り返して行が高くなり、一画面で見える件数が減る。
サイドバーがある時点で左は埋まっているので、本文まで幅を絞る理由がない。
`max-width` で中央に寄せる作りは、記事や LP のような「読む」ページの型であって、
「見る・入れる」業務アプリには向かない。

### 3. 待ちは必ず見せる

業務アプリの画面は、たいていサーバーでデータを読んでから表示される（Next.js の App Router なら全ページが動的）。
AIの処理を待つボタンは数秒〜数十秒かかる。その間に画面が何も変わらないと、

- 押せていないと思って何度も押す（二重登録・AIの二重課金）
- 「固まった」「遅い」と感じて、デモの場で印象が落ちる
- 実際は動いているのに、不具合として報告が来る

表示を付けるコストは数十行で、付け忘れたときの損のほうがずっと大きい。**デモ・試作でも省かない。**

## 置き場の決め方

| 種類 | 例 | 置き場 |
|---|---|---|
| オブジェクトの一覧 | 受注票・顧客・案件・商品・予約 | **サイドバーの本体**。1オブジェクト1項目 |
| 一覧の絞り込み（状態・区分） | 下書き／確定／納品済、今月／先月 | サイドバーの**子項目**か、一覧画面のフィルタ。別オブジェクトにしない |
| オブジェクトを新しく作る | ＋ 注文を入れる、＋ 顧客を登録 | **一覧画面の右上**の主ボタン（1つ） |
| オブジェクトに対する一括の操作 | 取り込み、一括更新、書き出し | 一覧画面の右上の**副ボタン**（控えめな見た目） |
| 1件に対する操作 | 確定する、指示書を出す、削除 | **その1件の画面の中**（上部の状態バー、タブ、ボタン） |
| 補助（オブジェクトに紐づかない） | 使い方・設定・ログアウト・接続状態 | サイドバーの**下端（フッター）**に小さく。本体の列に混ぜない |
| トップ（/） | — | 主オブジェクトの一覧へ転送。「ようこそ」画面を作らない |

## 横幅の決め方

| 要素 | 既定 |
|---|---|
| 本文（`main`） | `flex: 1; width: 100%; min-width: 0;` に左右 24〜32px の余白。**`max-width` を付けない** |
| 表 | `width: 100%`。列が多いなら横スクロールにし、折り返しで行を高くしない |
| 2カラム（入力＋プレビュー等） | `grid-template-columns` で画面幅を分け合う（例 `1fr 1fr`、`5fr 4fr`）。900px 以下で1列 |
| 入力フォーム | 2列グリッドで幅を使う。1列に縦長に並べない |
| ログイン・エラーなど単機能の1枚 | ここだけ `max-width: 380〜480px` で中央に寄せてよい |
| 文章を読むだけの画面（使い方・規約） | 読みやすさのため `max-width: 760〜880px` にしてよい。ただし左寄せ（サイドバーの隣）でよく、中央に寄せる必要はない |

## 組み方の手順

1. Phase 1-C の「エンティティ」から、**人が一覧で見たい名詞**を 1〜5 個選ぶ。これがサイドバーの項目
2. 各名詞について「作る／一括でやる／1件にやる」の動詞を洗い出し、上の表の置き場に振る
3. 動詞が一つも無い名詞は、サイドバーに出さない（参照だけなら別オブジェクトの画面の中で足りる）
4. 動詞しか無い項目（「取り込み」「使い方」）がサイドバーに残っていたら、どのオブジェクトの操作かを決めてそこへ移す
5. 1件の画面は「状態（どこまで進んだか）→ 中身 → 1件への操作」の順。操作は人が決める所だけに絞る
6. 本文の横幅は画面いっぱい。1280px 以上の画面で左右が余っていたら、`max-width` を探して外す

## ローディング表示の入れ方（全アプリ必須）

3つを必ずそろえる。どれか1つでは足りない（効く場面が違う）。

| 部品 | 効く場面 | Next.js（App Router）での置き方 |
|---|---|---|
| 画面上端の進み具合バー | リンク・ナビを押した瞬間〜次の画面が出るまで。フォーム送信→ redirect も | `components/NavigationProgress.tsx`（下のひな型）を `app/layout.tsx` の `<body>` 直下に `<Suspense fallback={null}>` で包んで置く |
| 本文の「読み込み中…」 | 次の画面のデータを読んでいる間、本文の場所に出す | `app/loading.tsx`（サイドバーは残り、本文だけ差し替わる）。重い画面は各フォルダにも置く |
| ボタンの処理中表示 | AI処理・保存などのボタン。二重押しも防ぐ | `useFormStatus` の `pending` で `disabled` にし、文言を「作成中…」などに変える（`SubmitButton`） |

**進み具合バーのひな型**（依存パッケージなし。リンク・フォーム送信・戻る/進むで始まり、次の画面の中身が出たら消える）:

```tsx
'use client';
import { useEffect, useRef, useState } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';

export default function NavigationProgress() {
  const pathname = usePathname();
  const search = useSearchParams();
  const [active, setActive] = useState(false);
  const [width, setWidth] = useState(0);
  const timers = useRef<number[]>([]);
  const clear = () => { timers.current.forEach((t) => window.clearTimeout(t)); timers.current = []; };
  const start = () => {
    clear(); setActive(true); setWidth(8);
    [[150, 30], [600, 55], [1500, 70], [4000, 82], [10000, 90]].forEach(([ms, w]) =>
      timers.current.push(window.setTimeout(() => setWidth(w), ms)));
    timers.current.push(window.setTimeout(() => done(), 60000)); // AI待ちがあるので長め
  };
  const done = () => {
    clear(); setWidth(100);
    timers.current.push(window.setTimeout(() => { setActive(false); setWidth(0); }, 250));
  };
  // URL が変わり、本文の「読み込み中…」（app/loading.tsx の .page-loading）が消えたら完了。
  // loading.tsx があると URL は押した直後に変わるので、URL だけで消すとバーが一瞬で終わってしまう
  useEffect(() => {
    if (!document.querySelector('.page-loading')) { done(); return; }
    const mo = new MutationObserver(() => {
      if (!document.querySelector('.page-loading')) { mo.disconnect(); done(); }
    });
    mo.observe(document.body, { childList: true, subtree: true });
    return () => mo.disconnect();
  }, [pathname, search]);
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const a = (e.target as HTMLElement | null)?.closest('a');
      if (!a || a.target === '_blank' || a.hasAttribute('download')) return;
      const href = a.getAttribute('href');
      if (!href || href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:')) return;
      const url = new URL(a.href, window.location.href);
      if (url.origin !== window.location.origin) return;
      if (url.pathname === window.location.pathname && url.search === window.location.search) return;
      start();
    };
    const onSubmit = (e: SubmitEvent) => { if (!e.defaultPrevented && (e.target as HTMLFormElement)?.target !== '_blank') start(); };
    const onPop = () => start();
    document.addEventListener('click', onClick, true);
    document.addEventListener('submit', onSubmit, true);
    window.addEventListener('popstate', onPop);
    return () => {
      document.removeEventListener('click', onClick, true);
      document.removeEventListener('submit', onSubmit, true);
      window.removeEventListener('popstate', onPop);
      clear();
    };
  }, []);
  return (
    <div className={`nav-progress${active ? ' on' : ''}`} aria-hidden={!active} role="progressbar" aria-label="読み込み中">
      <div className="nav-progress-bar" style={{ width: `${width}%` }} />
    </div>
  );
}
```

```css
.nav-progress{position:fixed;top:0;left:0;right:0;height:3px;z-index:1000;pointer-events:none;opacity:0;transition:opacity .2s}
.nav-progress.on{opacity:1}
.nav-progress-bar{height:100%;background:#3B82F6;transition:width .3s ease}
.page-loading{display:flex;align-items:center;gap:10px;padding:40px 4px}
.spinner{width:20px;height:20px;border:3px solid #EEF2FF;border-top-color:currentColor;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
```

- `useSearchParams` を使うので、layout では必ず `<Suspense fallback={null}>` で包む（包まないとビルドで止まる）。
- `app/loading.tsx` の外側の要素には必ず `className="page-loading"` を付ける（バーはこれが消えるのを待つ）。
- 確かめ方：Playwright でネットワークを2秒遅らせてナビを押し、0.05秒後にバーが出ていて（`.nav-progress.on`）、本文に「読み込み中…」があり、中身が出たらバーが消えることを見る。
- 色はアプリの主色に合わせてよい。高さは 3px 程度で、本文を押し下げない（`position: fixed`）。
- Next.js 以外（Vite の SPA など）でも同じ3つをそろえる。ルーターの遷移開始／終了のイベントに進み具合バーをつなぎ、データ読み込み中は本文に「読み込み中…」を出す。

## URL の切り方

- 一覧: `/<objects>`（例 `/orders`）
- 作る: `/<objects>/new`
- 一括の操作: `/<objects>/<verb>`（例 `/orders/import`）
- 1件: `/<objects>/<id>`。1件への操作は同じ画面内（タブ・ボタン）で、別 URL にしない
- `/` は主オブジェクトの一覧へ redirect

## チェック（Phase 3 のプラン提示と app-smoke-test で見る）

- [ ] サイドバーの項目は全部「名詞」か（「〜する」「使い方」が混ざっていないか）
- [ ] 一覧画面の右上に「＋ 作る」の主ボタンがあるか
- [ ] 一括の操作（取り込み・書き出し）が一覧画面の中から始まるか
- [ ] 「使い方」「設定」はフッターに退いているか
- [ ] `/` を開いたら主オブジェクトの一覧に着くか
- [ ] 1440px 幅のスクリーンショットで、本文の右側に余白が残っていないか（`main` に `max-width` が無いか）
- [ ] 画面上端の進み具合バーがあるか（layout に `NavigationProgress`）。ナビを押した瞬間に出るか
- [ ] `app/loading.tsx` があり、本文に「読み込み中…」が出るか
- [ ] AI処理・保存のボタンが、処理中に押せなくなり文言が変わるか

## 直すときの目安

既存アプリで動詞がサイドバーに並んでいたら、**ページの中身は変えずに場所だけ動かす**。
「作る」ページは `/<objects>/new` に移して一覧の右上からリンク、旧 URL は redirect で残す。
中身のコードを触らずに済むので、30 分程度で直る。

横幅が余っていたら、たいてい `main` の `max-width` 1 行。外して `width: 100%` にするだけ。

> 実例（2026-10）：受注の試作で「注文を入れる／受注票一覧／過去案件の取り込み／使い方」を
> サイドバーに横並びにして指摘を受けた。受注票だけを残し（状態を子項目に）、
> 「注文を入れる」「取り込み」は受注票一覧の右上のボタン、「使い方」はフッターへ移した。
> 同じアプリで本文に `max-width: 1280px` が付いていて右側が余っていたのも指摘を受け、外した。
>
> 実例（2026-10）：商談用の試作で、ボタンの処理中表示はあったが、画面遷移のローディング表示が無く、
> 「入っていない」と指摘を受けた（それまでにも繰り返し指摘されていた）。進み具合バーと `app/loading.tsx` を足し、
> この原則の3つ目として全アプリの必須にした。
