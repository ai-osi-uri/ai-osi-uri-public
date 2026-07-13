# 最終フレーム連鎖でシームレスに繋ぐ（正本）

「地図の物語」実写CMで確立。**継ぎ目を消す＝前カットの最終フレームを次カットの起点画像にして i2v で生成する**。

## 1. 手順（連鎖生成）

```bash
# A の最終フレームを抜く（末尾0.05秒＝実質ラストフレーム）
ffmpeg -nostdin -loglevel error -sseof -0.05 -i A.mp4 -update 1 -frames:v 1 -q:v 2 A_last.png
# 連携コネクタが読める場所（Driveマウント＝FAL_OUTPUT_DIR）に置く
```

```text
submit_video(
  model="kling25-i2v",            # 人物・実写モーションはkling25-i2vが安定
  image_url=".../A_last.png",     # ← B の1フレーム目になる
  prompt="Cinematic live-action, seamless continuous camera motion, no cuts. <この先の動き>. never move backward.",
  duration_seconds=5 or 10
)
```

- B の1フレーム目＝A の最終フレームなので、`concat` すると継ぎ目が消える。
- **カスケード規則**：途中カットを差し替えたら、その最終フレームが変わる → **以降のカットは全部この手順で作り直す**（例：g09差し替え→g10→g11→g12を連鎖再生成）。
- 起点フレームは“クリーンな絵”を渡す（テロップ・線なし）。寄り（クローズアップ）で終えたいなら、A側の末尾を軽いズームインで終える（`zoompan`）と、その寄った絵から自然に次へ入れる。

## 2. 尺同期（固定タイムラインを壊さない）

単一ナレ音声＋`adelay` で組んだ動画は、各カットの尺を**元と一致**させる。

```python
# 生成クリップ real 秒 → タイムライン target 秒へ
f = round(target/real, 4)
# 全カメラアークを残す（圧縮/伸長）：
vf = f"scale=1920:1080:...,setpts={f}*PTS,fps=30,format=yuv420p"  # + -t {target}
```

- `setpts`＝全体を等速で圧縮/伸長。**`trim`（-t だけ）は先頭N秒を切るのでグランドリビール等の山場を落とす**。空撮の“引きの到達点”を残したいときは必ず `setpts`。
- 長い枠（10s前後）は10s生成、短い枠は5s生成してから `setpts` で合わせる。

## 3. frame-diff 検証（QA・数値でOK/NG）

`meanAbsDiff`（0–255）で自動判定。しきい値は経験則：

```python
import cv2, numpy as np, subprocess
def frame(p, t):
    subprocess.run(["ffmpeg","-nostdin","-loglevel","error","-ss",str(t),"-i",p,"-frames:v","1","-y","/tmp/f.png"])
    return cv2.imread("/tmp/f.png")
def diff(a,b): return float(np.mean(np.abs(a.astype(int)-cv2.resize(b,(a.shape[1],a.shape[0])).astype(int))))
```

| 検証 | 測り方 | 合格の目安 |
|---|---|---|
| (a) モーション有無（静止画化していないか） | カット内の2フレーム差 | **> 約3**（動いている）。<3 は “止めて揺らし” 疑い→i2v で作り直し |
| (b) 継ぎ目のシームレス | A の最終フレーム vs B の1フレーム目 | **< 約5**（実測 2.4〜2.8 が良好） |
| (c) ムーブボード線の非映り込み（reference-to-video） | 赤ピクセル比（r>150 & g<90 & b<90） | 画面比ごく僅か（線・番号が出ていない） |

各繋ぎ目・各カットで回し、コンタクトシート（数カットを1枚に並べたjpg）で目視も併用する。

## 4. フラッシュ繋ぎ（代替・味付け）

どうしても連鎖生成できない/絵が飛ぶ時のみ、白フラッシュ等で“味付け”する（尺は各カット内で完結させ、xfadeで尺を縮めないこと＝#20）。
- A末：`fade=t=out:st=(D-0.2):d=0.2:color=white`／B頭：`fade=t=in:st=0:d=0.3:color=white`
- ただし本命は常に「最終フレーム連鎖」。ユーザーが「繋がっていない/フラッシュはやめて」と言ったら 1. に戻す。
