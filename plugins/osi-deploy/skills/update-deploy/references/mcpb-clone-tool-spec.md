# `AI OSI URI Deploy` 拡張への `github_clone_repo` 追加仕様

update-deploy の Phase 2「ローカル clone の確保」を MCP 一発で完結させるために、
`mcp/ai-osi-uri-deploy` 拡張に以下のツールを追加することを提案する。

## ツール仕様

```ts
// 追加先: server.tool(...)
server.tool("github_clone_repo", {
  description:
    "拡張内の GITHUB_PAT を使って GitHub リポを指定パスに clone（または tarball 展開）する。" +
    "既存ディレクトリは衝突回避のため拒否（force オプション無し）。",
  inputSchema: {
    type: "object",
    required: ["repo_name", "dest_dir"],
    properties: {
      repo_owner: {
        type: "string",
        description: "owner（Org slug or username）。未指定なら GITHUB_USERNAME",
      },
      repo_name: { type: "string" },
      dest_dir: {
        type: "string",
        description: "絶対パス。既存があれば失敗（先に削除/退避を案内）",
      },
      ref: {
        type: "string",
        description: "ブランチ / タグ / SHA。既定 main",
        default: "main",
      },
      mode: {
        type: "string",
        enum: ["git", "tarball"],
        default: "git",
        description: "git clone（履歴つき）か、tarball 展開（履歴なし・軽量）",
      },
    },
  },
  handler: async ({ repo_owner, repo_name, dest_dir, ref = "main", mode = "git" }) => {
    const owner = repo_owner ?? process.env.GITHUB_USERNAME;
    const pat = process.env.GITHUB_PAT;
    if (!pat) throw new Error("GITHUB_PAT が未設定（拡張設定で入力してください）");

    // 既存ディレクトリチェック
    if (fs.existsSync(dest_dir)) {
      throw new Error(
        `dest_dir が既に存在: ${dest_dir}。退避してください（mv ${dest_dir} ${dest_dir}.bak）`,
      );
    }

    if (mode === "git") {
      // PAT を URL に埋めて clone → 終了後に remote を書き換える
      const remote = `https://x-access-token:${pat}@github.com/${owner}/${repo_name}.git`;
      await execa("git", ["clone", "--branch", ref, remote, dest_dir]);
      await execa(
        "git",
        ["-C", dest_dir, "remote", "set-url", "origin", `https://github.com/${owner}/${repo_name}.git`],
      );
    } else {
      // tarball 一発取得
      const url = `https://api.github.com/repos/${owner}/${repo_name}/tarball/${ref}`;
      const res = await fetch(url, {
        headers: {
          Authorization: `Bearer ${pat}`,
          "X-GitHub-Api-Version": "2022-11-28",
          Accept: "application/vnd.github+json",
        },
        redirect: "follow",
      });
      if (!res.ok) throw new Error(`tarball fetch ${res.status}`);
      fs.mkdirSync(dest_dir, { recursive: true });
      await pipeline(
        Readable.fromWeb(res.body as any),
        gunzip(),
        tar.extract({ cwd: dest_dir, strip: 1 }),
      );
    }

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            ok: true,
            dest_dir,
            ref,
            mode,
            repo: `${owner}/${repo_name}`,
          }),
        },
      ],
    };
  },
});
```

## なぜ 2 モードを用意するか

| mode | 用途 | サイズ・速度 |
|---|---|---|
| `git` | 後続で `github_push` する | やや重い（履歴つき） |
| `tarball` | 読み取りのみ・1回限りの修正比較など | 軽量（履歴なし） |

update-deploy は **既定で `git` モード**を使う（push 必須のため）。

## セキュリティ上の注意

1. `dest_dir` は **既存ディレクトリ拒否**（ユーザーの作業中フォルダを巻き戻さない）
2. `mode: "git"` の場合、PAT 入りリモート URL は **clone 完了直後に置換**して `.git/config` に残さない
3. tarball モードは `pipeline` + `tar.extract` で展開し、`strip: 1` でトップディレクトリを剥がす

## 動作確認テスト

```bash
# 拡張内の test runner で
test("github_clone_repo: git mode", async () => {
  const r = await server.callTool("github_clone_repo", {
    repo_owner: "ai-osi-uri",
    repo_name: "ai-catalog-navigator",
    dest_dir: "/tmp/test-clone-" + Date.now(),
    mode: "git",
  });
  expect(r.ok).toBe(true);
  expect(fs.existsSync(`${r.dest_dir}/.git`)).toBe(true);
  // PAT が remote に残っていないことを確認
  const cfg = fs.readFileSync(`${r.dest_dir}/.git/config`, "utf8");
  expect(cfg).not.toMatch(/x-access-token:/);
});

test("github_clone_repo: tarball mode", async () => {
  const r = await server.callTool("github_clone_repo", {
    repo_owner: "ai-osi-uri",
    repo_name: "ai-catalog-navigator",
    dest_dir: "/tmp/test-tar-" + Date.now(),
    mode: "tarball",
  });
  expect(r.ok).toBe(true);
  expect(fs.existsSync(`${r.dest_dir}/package.json`)).toBe(true);
  expect(fs.existsSync(`${r.dest_dir}/.git`)).toBe(false); // 履歴なし
});
```

## リリース手順

1. `mcp/ai-osi-uri-deploy` リポにこのツールを追加した PR
2. CI 緑 → `mcpb-v0.6.0` でタグ
3. GitHub Releases に `ai-osi-uri-deploy-mcp.mcpb` を貼り直し
4. メンバーは Claude デスクトップで `.mcpb` を開き直すだけで反映

完了後、update-deploy の Phase 2-2 は MCP 1 コールに置換される。
