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

## 5〜8. 日本語TTSの誤読（対処は発音辞書方式に移行済み）

**現象は今も起きる。変わったのは直し方。**

起きる誤読（v1〜v24 で観測）：
- 純粋ひらがなにすると助詞「は」が「ha」と読まれる
- 小書き仮名（ゃゅょっ）の脱落
- 長音「ー」のスキップ／逆に余計な長音の挿入
- 「エー」が「イー」化、カタカナ短語が無駄に伸びる
- 固有名詞の長音脱落・頑固な長音化
- 複数読みの漢字（27年→「しちねん」、力→「ちいら」等）
- 英字の綴り読み（OKWEB→「オーケーダブリューイービー」）
- 「・」の誤読

**❌ 旧対処（廃止）**：原稿の字面を壊す。二重母音化（データ→デエタ）、カタカナ強制、
ひらがな化、々（ふりがな）ハック。案件ごとに作り直す属人的な暗黙知になっていた。

**✅ 現行の対処**：原稿はクリーンな漢字かな混じりのまま保ち、**読みは発音辞書(.pls)に外出し**する。
1. `../../narration/scripts/jp_yomi_check.py` で誤読を機械検出（pyopenjtalk の G2P）
2. 正読みを glossary CSV に追記 → `.pls` を再生成
3. `create_pronunciation_dictionary` で登録し、`generate_speech` の `pronunciation_dictionaries` で適用
4. alias で直らない頑固な箇所だけ IPA(phoneme) ルールへ（**v3 / flash_v2 のみ有効**）

正本は `../../narration/SKILL.md` と `../../narration/templates/narration-rules.md`。
辞書は案件横断で蓄積できる資産になる（共通辞書＋会社別辞書）。

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

**根本解決（2026-06 追記・推奨）**：i2v ではなく **Seedance 2.0 `reference-to-video`（`bytedance/seedance-2.0/reference-to-video`）** を使う。これは渡した画像を**参照(reference)**として使い1フレーム目にしないので、**赤線・番号入りの絵コンテをそのまま渡しても線が出力に出ない**（元ネタ「only use it for instructions」が成立）。頭トリックも不要。線駆動のカメラムーブはこのモードが正解。詳細は `moveboard.md`。

---

## 18. カメラムーブが回りきらない／途中でカット（2026-06 発見）

**症状**：(a) 360°オービットが半周で別カットに切り替わる。(b) 短尺に動きを詰め込むと途中でハードカットが入る（例：近景push-in→広域orbitの“距離戻し”で4秒地点に飛びが出る）。

**原因**：短尺×多ビートで各動きの尺が足りない／1枚絵からの360°は背面創作が必要で破綻しやすい／近景と広域を混ぜるとカメラの再配置でカットが生じる。

**対処**：
- 主役の動き（例：360°オービット）は**そのビートに尺の大半を割く**。寄り/引きは最小化。
- きれいな360°は**一定距離の純オービット**（push-in/pull-back を混ぜない）。回りきらせるためなら**速度を上げる**（多少のオーバー許容）。
- 1枚絵で無理なら 180–270° に留める、または**ビート数を減らす**。
- 検証は ffmpeg で 3〜5 秒付近を 0.3 秒刻みで抜いて“飛び”が無いか確認。

---

## 19. カメラの向きを反転させると気持ち悪い（2026-07 発見）

**症状**：連続シーンで「一度引いて（プルバック）→次で寄る（プッシュイン）」と繋ぐと、カメラが後退→前進に切り替わって見え、視聴者が“気持ち悪い”と感じる。

**原因**：1本の移動として認識されている尺で、カメラの進行方向が反転する。

**対処**：
- 1本のジャーニーは**方向を一貫**させる（前進なら最後まで前進）。
- 「引きながら（視界を広げつつ）前へ進む」は、**前進ドリー＋クレーンアップ**で表現（“引く”＝後退ではなく“広がる”）。
- 到達点で被写体（人物等）に寄るのは、前進の延長として**減速＋フォーカス送り**で行う（後退しない）。
- 詳細は `../../vp-seamless-journey/`。

---

## 20. 固定タイムライン（単一ナレ＋adelay）でカット差し替えると尺がズレる（2026-07 発見）

**症状**：後半カットを作り直したら、以降のナレーションが全部ズレた（例：あるカットの尺を 4.834s のところ 8.467s で作ってしまい、以降の行が後ろへズレた）。

**原因**：単一ナレ音声トラックに `adelay` で各行を固定配置している場合、動画側の各セグメント尺が変わると、それ以降のカット開始時刻がナレとずれる。

**対処**：
- 差し替えるカットの尺を**元と1フレーム単位で一致**させる（`ffprobe` で元尺を確認）。
- 全カメラアークを残すなら `setpts=(target/real)*PTS` ＋ `-t target`（等速で圧縮/伸長）。
- **`trim`（-t だけ）は先頭N秒を切るのでグランドリビール等の山場を落とす**。到達点を残したいカットは必ず `setpts`。
- 合計尺と各カット尺を検算してから連結・remux。

---

## 21. 人物カットを「静止画＋ズーム/パン（Ken Burns）」で誤魔化すと死んで見える（2026-07 発見）

**症状**：人物カットを静止画のスロー・ズーム（zoompan）で作ると、“止めて揺らしている”だけで生命感が無く見える。

**対処**：
- 被写体が人なら **i2v で実際に動かす**（手・表情・体の自然な微動）。静止画＋ズームで代用しない。
- 顔ドアップの不気味の谷は #16 と併用（引き・後ろ姿・横顔・手元、屋外自然光）。
- 別カットで人物が“別人化”したら、正しいカットの1枚を key visual にして `edit_image` で「同一人物のまま別の感情/ポーズ」に編集 → i2v（同じ場面の2回目もクリップ再利用でなく edit_image で別アングルを作る）。
- 検証は frame-diff：カット内2フレームの meanAbsDiff > 約3 で「動いている」を担保（`../../vp-seamless-journey/references/seamless-continuation.md`）。

## 22. submit は通るのに check_status で 422 になる（2026-08 発見・コネクタ v2.1 で対策済み）

**症状**：`submit_video` は `request_id` を返して成功するのに、`check_status` が
`Unprocessable Entity` だけを返す。ログにも理由が出ないので原因が見えない。

**原因**：fal はモデルごとに引数の形が違う。
- Veo 3.1 系は `duration` が **`"8s"` 形式**で、受け付けるのは **4/6/8秒のみ**。`"5"` を送ると落ちる。
- `veo31-i2v` / `-ref` / `-flf` は **`aspect_ratio` を受け付けない**（起点画像から決まるため）。
- Seedance 系は `"8"` 形式で、`resolution`（480p/720p）を取る。

キューへの投入自体は通ってしまうので、**submit の成功はモデル引数の正しさを何も保証しない**。

**対策**：コネクタ v2.1 でモデル定義に引数のクセ（`durationStyle` / `durations` / `aspectRatio` /
`resolution`）を持たせ、送信直前に正規化するようにした。受け付けない秒数は最も近い値に丸める。
`list_models` の各モデルに `※` で制約が出るので、迷ったらそこを見る。

**それでも詰まったら**：`extra` は最後に重ねられる＝利用者の明示指定が常に勝つので、
`extra` に生の形で書けば正規化を飛ばせる。

**2026-08 の実害**：この件で5本のクリップを丸ごと捨てた。原因の切り分けは
「パラメータを全部外して最小構成で1本投げる」が最短。

---

## 23. 生成物の置き場が Cowork から見えないと合成できない（2026-08 発見）

コネクタは `FAL_OUTPUT_DIR` に書き出すが、そこが Cowork に接続されたフォルダの外だと、
生成したナレ・BGM・クリップを**読み取れず合成に進めない**。動画は Source URL から拾えるが、
`generate_speech` は URL を返さない（ローカル保存のみ）ので詰む。

**対策**：案件を始める前に `FAL_OUTPUT_DIR` が接続フォルダ配下かを確認する。
違う場合は先にそのフォルダへのアクセスを1回もらう。

---

---

## チェック手順（着手前に必ず）

1. `pitfalls.md`（このファイル）を読み返す
2. `../../narration/templates/narration-rules.md` を読み返す
3. `model-comparison.md` でモデル使い分けを確認
4. ユーザーへのヒアリングを Phase 0 で実施
5. 試作（Phase 4）を必ず挟む
6. 一気にフル生成しない
