# ext-deploy：デスクトップ拡張「Deploy」を入れる

手元のフォルダから Vercel に直接上げる・Terraform・Android の署名鍵の作成・Cloudflare Worker の直接デプロイは、Claude のデスクトップアプリに入れる拡張でだけ動く。

## 揃っているか
- `github_push` や `github_fetch` の道具が見えている → 揃っている。

## 手順
1. まず computer（デスクトップアプリ）を済ませる。
2. `references/install-extension.md` の手順で、Deploy の拡張（製品キー `ai-osi-uri-deploy`）を入れる・上げる。本人は「インストール」を1回押すだけ。
3. 拡張の設定欄に入れる鍵は、スキル setup-deploy-environment の手順で 1 つずつ案内する（鍵の値は会話に貼らせない）。
4. 新しい会話を開いてもらい、`health_check` が返るかで確かめる。

Git の push・取り込みだけなら、拡張は要らない（URL のコネクタの `github_upload_url` → `github_push_folder` ／ `github_download_folder`）。
