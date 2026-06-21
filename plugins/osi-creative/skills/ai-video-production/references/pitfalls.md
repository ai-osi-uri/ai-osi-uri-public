# 落とし穴集（実戦で得た知見）

OKWEB × JINEN動画制作で実際に遭遇した問題と回避策。**毎回ここを参照してから着手する。**

---

## 1. fal.ai 並列ジョブ制限（Forbidden）

**症状**：5〜6本以上を同時に `submit_video` すると、4〜5本目以降が `Error: Forbidden` で受理されない。

**原因**：fal.ai のアカウント並列実行枠の上限。Pay-as-you-go アカウントではモデル毎に約5〜6本同時が上限と推測。

**対処**：
- 5本ずつ2バッチに分けて投入
- バッチ間に10秒待機
- Forbidden時は30秒待機後、1本ずつ間隔をあけて再投入

```bash
# OK
for i in 01 02 03 04 05; do submit; done
sleep 10
for i in 06 07 08 09 10; do submit; done

# NG（Forbidden発生）
for i in 01 02 03 04 05 06 07 08 09 10; do submit; done
```

---

## 2. fal.ai クレジット切れ後の塩漬けキュー

**症状**：投入したジョブが `IN_QUEUE` のまま延々動かない。クレジット追加しても再開しない。

**原因**：クレジット切れの状態で submit したジョブはキューに入るが、後でクレジット追加されても自動再開しない。

**対処**：
- 古いジョブは無視（自動的にタイムアウト消滅）
- クレジット追加後、新規 `submit_video` で再投入
- ユーザーには fal.ai dashboard でキャンセルしてもらう案内も可

---

## 3. Veo 3（fast でない方）のパラメータ厳格性

**症状**：`Error: Unprocessable Entity` が返る。

**原因**：Veo 3 は duration_seconds 等の入力フォーマットが厳しい。"5" では受理されない。Veo 3 は固定 8s。

**対処**：
- `Veo 3 Fast` を優先（より許容的）
- どうしても Veo 3 を使うなら duration_seconds を送らずデフォルト依存
- または `extra: { duration: "8s" }` を試す

---

## 4. MCP ブロッキング呼び出しのタイムアウト

**症状**：`generate_video`（ブロッキング）で `MCP error -32001: Request timed out`。

**原因**：Cowork のMCPツール呼び出しは 60〜120秒でタイムアウト。Veo 3 の生成は 1〜5分かかる。

**対処**：
- 動画生成は必ず **`submit_video` + `check_status`** の非同期パターンを使う
- ブロッキング `generate_video` は 30秒以内で完了する用途のみ
- ナレーションTTS（5〜15秒）は `generate_speech` ブロッキングでOK

---

## 5. ElevenLabs：純粋ひらがなで助詞「は」が誤読

**症状**：「世界は」が "せかい・ha"（hの音）と読まれる。

**原因**：ひらがなだけだと、ElevenLabs の音素エンジンが「は」を助詞（wa）か地音（ha）か判別できない。

**対処**：
- 漢字を残す：「世界は」（漢字+はの並びで助詞と認識）
- 全部ひらがなにしない

---

## 6. ElevenLabs：小書き仮名の脱落

**症状**：
- 「みっつ」→「みつつ」（小書き「っ」脱落）
- 「きょだい」→「きよだい」（小書き「ょ」脱落）
- 「4,800万件」→「よんじゅうはっぴゃくまんけん」（数字の桁誤認識）

**対処**：
- カタカナに切り替え（ミッツ、キョダイ）
- または漢字に戻す（3つ、巨大）
- 数字は半角＋カタカナ単位＋空白（ヨンセン ハッピャク マンケン）

---

## 7. ElevenLabs：長音「ー」のスキップ

**症状**：
- 「プラットフォーム」→「プラットフォム」
- 「サービス」→「サビス」
- 「データ」→「デタ」
- 「エンゲージメント」→「エンゲジメント」（v6で発見）

**対処**：二重母音表記
- プラットフォーム → **プラットフォオム**
- サービス → **サアビス**
- データ → **デエタ**
- エンゲージメント → **エンゲエジメント**

## 7-2. ElevenLabs：「エー」が「イー」化（v6で発見）

**症状**：
- 「エーアイ」→「イーアイ」
- 「AI」をカタカナ化しても同じ
- シーン⑧では更に悪化して「イーアイアイ」と読まれた

**原因**：長音「エー」の「エ」が脱落・置換される

**対処**：二重母音「エエ」に書き換え
- エーアイ → **エエアイ**
- エース → エエス

## 7-3. ElevenLabs：余計な長音挿入（v6で発見）

**症状**：「グラティカ」→「グラティーカ」（ティの後ろに勝手に長音）

**原因**：小書き「ィ」を「ティー」のように長音化して読む

**対処**：小書き仮名を消すか簡素化
- グラティカ → **グラチカ**
- ティアラ → チアラ（必要に応じて）

## 7-4. ElevenLabs：カタカナ短語が無駄に伸ばされる（v7で発見）

**症状**：「ジネン」→「ジイネン」（ジの後に余計な「イ」が挿入される）

**原因**：2〜3音節の短いカタカナ固有名詞でエンジンが音を伸ばす癖

**対処**：ひらがな表記に切り替える（カタカナの読み癖を回避）
- ジネン → **じねん**
- 短い固有名詞は カタカナ より ひらがな の方が安定する場合あり

## 7-5. ElevenLabs：固有名詞の長音脱落（v7で発見）

**症状**：「オーケーウェブ」→「オーケウェブ」（2つ目の長音が短くなる）

**原因**：問題7と同様の長音スキップだが、固有名詞で特に頻発

**対処**：すべての長音を二重母音化
- オーケーウェブ → **オオケエウェブ**
- 固有名詞の中の **すべての** 長音記号を二重母音に書き換える

## 7-6. ElevenLabs：短い固有名詞の頑固な長音化（v8/v10で発見・最強の対処法）

**症状**：「ジネン」のような2-3音節カタカナで、**何をしても「ジーネン」と長音化される**
- カタカナ → 長音化
- ひらがな → 長音化
- 英字 (Jinen) → 「キネン」と全く違う音
- ヂ表記 → 効果なし
- stability MAX → 効果なし
- 空白挿入 → 効果なし

**原因**：エンジンの強い構造的バイアス。スペル変更だけでは突破不能。

**対処：「々（ふりがな）」フォーマット**

「漢字（ふりがな）」では**ふりがな部分のイントネーションが正しく発音される**性質がある。漢字部分を「々」（くりかえし符号、ほぼ無視される）に置換することで、ふりがな部分の発音だけ抽出できる：

```
× ジネン                → ジーネン
× じねん                → ジーネン
× Jinen                 → キネン
× 自然（じねん）        → しぜん・じねん（漢字も読まれる）
✅ 々（じねん）          → ジネンに近い発音 ← これがベスト
```

**応用例**（他の固有名詞でも使える）：
- ジネン → **々（じねん）**
- ヤマ   → **々（やま）**
- ナナ   → **々（なな）**

**運用上の注意**：
- まず通常スペルで試し、誤読が確認されたら**該当箇所のみ**この技法を適用
- 文章全体に適用すると「々」が変な音として聞こえることがある
- ふりがな部分は ひらがな で書く（カタカナだとそこも長音化される）

**Web検索でのリサーチ参考**：
- ElevenLabs公式は Pronunciation Dictionary（発音辞書）を推奨だが、fal.ai 経由では使えない
- そのため、テキスト内の発音ヒント（フリガナ括弧）が現実的な唯一解

---

## 8. ElevenLabs：「・」の誤読

**症状**：「コミュニティ・プラットフォーム」→「コミュニティ**あら**プラットフォーム」

**対処**：「・」を半角空白に置換
- 「コミュニティ プラットフォオム」

---

## 9. ffmpeg + Drive sync 干渉

**症状**：ffmpeg の出力をDriveに直接書き込むと `moov atom not found` でファイルが壊れる。サイズも中途半端（42MB期待→22MB）。

**原因**：Google Drive の自動同期がffmpegの最終write中に介入し、moov atom（mp4ヘッダ）の書き込みが完了しない。

**対処**：
- ffmpeg は **必ず /tmp 配下に出力**
- 完了後に `cp` で Drive にコピー
- `cp` 後に `sync; sleep 2` で確実に書き出し

```bash
# OK
ffmpeg ... /tmp/work/final.mp4
cp /tmp/work/final.mp4 "$DRIVE/final.mp4"
sync; sleep 2

# NG
ffmpeg ... "$DRIVE/final.mp4"
```

---

## 10. ffmpeg 長時間処理が bash timeout で切られる

**症状**：字幕焼き込みなど 30秒以上かかる ffmpeg 処理が bash の45秒上限で中断され、不完全ファイル化。

**対処**：バックグラウンド実行＋ポーリング

```bash
nohup ffmpeg ... > /tmp/log 2>&1 &
PID=$!
sleep 40
ps -p $PID && echo "running" || echo "done"
```

---

## 11. 動画とナレ尺が合わない

**症状**：5秒動画に23秒ナレを乗せると、最後5秒だけ画があってあとは静止画。

**対処**：PTS（presentation timestamp）でビデオを伸縮

```bash
target=$(awk -v n="$NARR_DUR" -v vd="$VIDEO_DUR" \
  'BEGIN{ if(n<vd) n=vd; printf "%.3f", n+0.3 }')
pts=$(awk -v t="$target" -v vd="$VIDEO_DUR" 'BEGIN{ printf "%.4f", t/vd }')

ffmpeg -i video.mp4 -i narr.mp3 \
  -filter_complex "[0:v]setpts=${pts}*PTS[v];[1:a]apad,atrim=0:${target}[a]" \
  -map "[v]" -map "[a]" -t "$target" out.mp4
```

抽象的・シネマティックな映像なら 2〜3倍 slow motion でも自然に見える。

---

## 12. ディスク不足（ENOSPC）

**症状**：`npm error nospc ENOSPC: no space left on device`

**原因**：
- /sessions ドライブ（Drive mount）が100%
- /tmp ドライブが80%以上

**対処**：
- 古い `/tmp/anime_*`, `/tmp/falbuild` 等を `rm -rf`
- node_modules を削除
- npm cache を削除：`npm cache clean --force`

---

## 13. 日本語フォントが sandbox にない

**症状**：ffmpeg字幕で日本語が「□」（豆腐）になる。

**対処**：Google Fonts の gstatic CDN から Noto Sans JP を取得

```bash
mkdir -p /tmp/fonts
curl -sSL -A "Mozilla/5.0" -o /tmp/fonts/NotoSansJP-Regular.ttf \
  "https://fonts.gstatic.com/s/notosansjp/v56/-F6jfjtqLzI2JPCgQBnw7HFyzSD-AsregP8VFBEj75s.ttf"
# Bold, Medium も同様
```

ffmpeg では `-vf "subtitles=...:fontsdir=/tmp/fonts:force_style='FontName=Noto Sans JP'"`。

---

## 14. fal.ai音楽生成のレスポンス形式の罠

**症状**：`check_music` で「Job COMPLETED but no audio URL」エラー。

**原因**：Stable Audio は `audio_file.url` フィールドで返してくる（他のTTSは `audio.url`）。MCP の `extractMediaUrl` はこの形式を見落としている。

**対処**（暫定）：エラーメッセージの中にURLが入っているので、bash + curl で直接DL。

```bash
curl -sSL -o "$DIR/bgm.wav" "$URL_FROM_ERROR"
```

長期的には MCP コードを更新（`extractMediaUrl` に `data.audio_file?.url` を追加）。

---

## 15. Veo 3 が西洋人を生成しがち

**症状**：「Japanese office worker」と書いても白人ぽい人物が生成される。

**対処**：プロンプトを強化
- "Japanese ethnicity, asian features"
- "Japanese man / Japanese woman"
- 「日本人」を3〜4回プロンプト内で言及
- 失敗したら Kling に切替（人物のアジア系再現が強い）

---

## 16. 顔のクローズアップで不気味の谷

**症状**：表情のクローズアップで顔が崩れる、目が変、口の動きが不自然。

**対処**：
- 顔のクローズアップを避け、引き気味の構図に
- 後ろ姿、手のクローズアップ、横顔を多用
- 屋外・自然光のシーンで誤魔化す
- 不気味な場合は再生成（コストかかるが）

---

## 17. image-to-video の入力画像はそのまま「1フレーム目」になる（2026-06 発見）

**症状**：飛行ルートを作り込もうとして「俯瞰図＋赤い飛行ルート＋番号付き指示ボックス」の絵コンテ画像を `image_to_video` の入力にしたら、動画が**その絵コンテ（赤線・崩れた文字・上下分割レイアウト）から始まってしまう**。冒頭の数秒が破綻して見える。

**原因**：i2v（Seedance / Veo i2v / Kling i2v いずれも）は、渡した画像を**動画の最初のフレームそのもの**として使う。設計図やテロップ入り画像を渡すと、それが冒頭に映り込む。プロンプトで「線を出すな」と書いても、1フレーム目は入力画像が優先される。

**対処（確定パターン）**：
- **絵コンテ（俯瞰図＋ルート）は“設計図／プランニング”としてだけ使い、動画の起点には渡さない。**
- i2v の入力（＝1フレーム目）には、**クリーンなヒーロー写真**（テロップ・線・分割なしの 16:9 キーフレーム）を渡す。
- 飛行ルートは、絵コンテで決めた順番を**文章プロンプトの「6ビート」**に落として制御する（例：谷間を抜ける→寄る→旋回→上昇→引き→グランドリビール）。
- プロンプトに `no title cards, no split screen, no diagrams, no text, no red lines/arrows/markers at any point` を明示。
- これで「クリーンな出だし」と「ルート制御」が両立する。検証は ffmpeg で1フレーム目を抜いて目視（`ffmpeg -i out.mp4 -vf "select=eq(n\,0)" -vframes 1 first.png`）。

> 「絵コンテを reference として使いたい」場合は、Seedance 2.0 の reference/multi-reference 系を使う手もあるが、起点フレームは必ずクリーン画像にすること。

---

## チェック手順（着手前に必ず）

1. `references/pitfalls.md`（このファイル）を読み返す
2. `templates/narration-rules.md` を読み返す
3. `references/model-comparison.md` でモデル使い分けを確認
4. ユーザーへのヒアリングを Phase 0 で実施
5. 試作（Phase 4）を必ず挟む
6. 一気にフル生成しない
