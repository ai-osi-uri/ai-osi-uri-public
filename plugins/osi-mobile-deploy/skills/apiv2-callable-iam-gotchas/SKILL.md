---
name: apiv2-callable-iam-gotchas
description: |
  Firebase Cloud Functions v2 の callable がクライアントから呼べないときの復旧。原因は
  IAM 未付与（Cloud Run が既定で認証必須）か、snake_case
  エンコーディングによるフィールド名の食い違いのいずれか。「callable が
  unauthenticated」「PERMISSION_DENIED runInvoker」「USER_UNKNOWN_FIELDS」「apiv2
  が呼べない」「deploy したらクライアントから呼べない」で発動する。
version: 0.1.0
requires_connectors:
  - server: AI_OSI_URI_Deploy
    provision: mcpb
---

# apiv2-callable-iam-gotchas — Cloud Functions v2 / apiv2 が呼べない時の 2 大原因

Firebase Cloud Functions v2 は内部で Cloud Run サービスとして deploy される。
1st gen とは違って **allUsers への invoker 付与が既定では行われない**。加えて、
express aggregator で複数 handler をラップする apiv2 パターンは payload 検証が
strict なので、client 側のフィールド名変換で簡単に壊れる。両方セットで潰す。

---

## 症状の切り分け

| 症状 | 原因 |
|---|---|
| Client: `FunctionsError.internal / functionsErrorCode = UNAUTHENTICATED` | (A) allUsers invoker が付いていない |
| Client: `communication error` / `NSURLErrorDomain -1005` 断続的 | (A) 同上（Cloud Run 側で 403） |
| Server log: `Function returned undefined, expected Promise or value` | (B) payload validation error（snake_case） |
| Server log: `USER_UNKNOWN_FIELDS: content_id, target_uid, post_id` | (B) client が snake_case を送っている |
| gcloud: `PERMISSION_DENIED: setIamPolicy` on Cloud Run | deploy 実行 SA に `roles/run.admin` が無い |

---

## Part A: 新規 apiv2-* サービスに allUsers invoker を付与

### 症状

Firebase Cloud Functions v2 を `firebase deploy --only functions` した直後、
iOS/Android クライアントから callable を叩くと 401 / UNAUTHENTICATED。
Cloud Console → Cloud Run で該当サービスを開くと `Authentication: Require
authentication` になっている。

これは Google の既定挙動：v2 の新規サービスは ID token を要求する。
Firebase callable convention（`{ data: { ... } }` を送る形）は ID token を
送らないので、認証必須のサービスは呼べない。

### 対処

deploy の**後に**、apiv2-* / content-* の全サービスへ `roles/run.invoker` を
`allUsers` メンバーに付与する。CI workflow の post-deploy step で自動化する:

```yaml
- name: Post-deploy — grant allUsers invoker on callable services
  run: |
    set -e
    TOKEN=$(gcloud auth print-access-token)
    SERVICES=$(curl -s -H "Authorization: Bearer $TOKEN" \
      -H "X-Goog-User-Project: $PROJECT" \
      "https://run.googleapis.com/v2/projects/$PROJECT/locations/asia-northeast1/services?pageSize=200" \
      | grep -oE '"services/[a-z0-9-]+"' | sort -u | sed 's|"services/||;s|"||')
    for SVC in $SERVICES; do
      case "$SVC" in
        apiv2-*|content-*) ;;       # ← callable 系だけ絞る
        *) continue ;;
      esac
      URL="https://run.googleapis.com/v2/projects/$PROJECT/locations/asia-northeast1/services/${SVC}:setIamPolicy"
      curl -s -o /tmp/setiam.json -w "%{http_code}\n" -X POST \
        -H "Authorization: Bearer $TOKEN" \
        -H "X-Goog-User-Project: $PROJECT" \
        -H "Content-Type: application/json" \
        -d '{"policy":{"bindings":[{"role":"roles/run.invoker","members":["allUsers"]}]}}' \
        "$URL"
    done
```

### MCP から冪等に叩く

```
mcp__AI_OSI_URI_Deploy__gcp_iam_add_roles_batch({
  project_id: "mustpost-dev",
  resources: [
    { type: "cloud-run", location: "asia-northeast1", name: "apiv2-account" },
    { type: "cloud-run", location: "asia-northeast1", name: "apiv2-posts" },
    ...
  ],
  bindings: [{ role: "roles/run.invoker", members: ["allUsers"] }]
})
```

### 事前に組織ポリシーを緩める

一部の組織は `iam.allowedPolicyMemberDomains` で `allUsers` を許可していない。
その場合は先に override policy を貼る（プロジェクト単位で allowAll）:

```yaml
- name: Allow public IAM members on this project (org policy override)
  run: |
    TOKEN=$(gcloud auth print-access-token)
    curl -s -X POST \
      -H "Authorization: Bearer $TOKEN" \
      -H "X-Goog-User-Project: $PROJECT" \
      -H "Content-Type: application/json" \
      -d '{"name":"projects/'"$PROJECT"'/policies/iam.allowedPolicyMemberDomains","spec":{"rules":[{"allowAll":true}]}}' \
      "https://orgpolicy.googleapis.com/v2/projects/$PROJECT/policies"
    # HTTP 200 = created / 409 = already exists (どちらも OK)
```

### org-level 権限がない場合の fallback

`iam.orgPolicy.update` が organization レベルでしか許可されていない環境では、
プロジェクト owner 権限ではポリシーを貼れない。その場合は組織 admin に依頼するか、
そもそも allUsers 呼び出しを諦めて **App Check + ID token 認証** に切り替える。

---

## Part B: camelCase を pin する（snake_case 変換を止める）

### 症状

deploy 済み、IAM も通っている。Client から callable を叩くと 200 で返るが、
server log に `USER_UNKNOWN_FIELDS: content_id, target_uid` が出て、レスポンス body が
`{ error: "invalid argument" }`。ペイロードのフィールド名が snake に化けている。

### 原因

Firebase Callable convention のサーバ側 validator は camelCase（`contentId`,
`targetUid`）を期待している。iOS の JSONEncoder / Android の Retrofit / Kotlin Serialization
の既定を放置すると勝手に snake に変える設定が入っていることがある。

### iOS (Swift) の修正

```swift
// CloudFunctionsClient.swift
public init(functions: Functions = .functions(region: AppEnvironment.current.functionsRegion)) {
    self.functions = functions
    let encoder = JSONEncoder()
    encoder.dateEncodingStrategy = .iso8601
    // ⚠️ Backend (apiv2) validates against camelCase field names
    // (contentId, targetUid, postId, …). Do NOT convert to snake_case
    // here — that would trigger USER_UNKNOWN_FIELDS validation errors.
    // encoder.keyEncodingStrategy = .convertToSnakeCase   ← 絶対にやらない
    self.encoder = encoder

    let decoder = JSONDecoder()
    decoder.dateDecodingStrategy = .iso8601
    // Server responses also use camelCase; keeping .convertFromSnakeCase
    // is harmless (no underscores → no change) and lets legacy
    // snake_case fields still decode if present.
    decoder.keyDecodingStrategy = .convertFromSnakeCase
    self.decoder = decoder
}
```

### Android (Kotlin) の修正

Retrofit + Moshi:

```kotlin
// Moshi の @Json annotation を明示的に使う（camelCase 名を書く）
data class ContentResolveLinkRequest(
    @Json(name = "linkId")    val linkId: String,
    @Json(name = "targetUid") val targetUid: String? = null,
)

// または Moshi の adapter で FieldNamingPolicy を LOWER_CAMEL_CASE に固定
val moshi = Moshi.Builder()
    .add(KotlinJsonAdapterFactory())
    .build()
```

Kotlinx Serialization:

```kotlin
@Serializable
data class ContentResolveLinkRequest(
    val linkId: String,          // Kotlin プロパティ名が camelCase なので既定で OK
    val targetUid: String? = null,
)

// SerializersModule に SnakeCaseJsonNamingStrategy を刺していないか確認
val json = Json {
    // namingStrategy = JsonNamingStrategy.SnakeCase   ← やらない
}
```

### 検証

Client 送信 payload をログに出して確認:

```swift
Logger.network.debug("→ callable \(endpoint.name) payload=\(payload.keys.sorted())")
```

`["contentId","targetUid"]` が出れば OK。`["content_id","target_uid"]` が出たら
encoder 設定を疑う。

### サーバ側の validator を確認

apiv2 の handler で zod / joi の schema を使っている場合、schema が camelCase を
書いていることを確認:

```typescript
// functions/src/api/posts.ts
const CreatePostRequest = z.object({
  contentId: z.string(),      // ← camelCase
  targetUid: z.string().optional(),
});
```

**しかし** 例外的に snake_case を許容したい場合（旧クライアント併存など）は、
schema 側で両方受ける:

```typescript
const CreatePostRequest = z.object({
  contentId: z.string().or(z.string().transform((s) => s)),   // strict
})
// or preprocess で snake → camel に寄せる:
const CreatePostRequestLoose = z.preprocess((obj: any) => ({
  contentId: obj.contentId ?? obj.content_id,
  targetUid: obj.targetUid ?? obj.target_uid,
}), CreatePostRequest);
```

`references/callable-schema-preprocess.ts` にサンプル。

---

## 完全チェックリスト

deploy 直後に必ず以下を確認する:

- [ ] `firebase deploy --only functions --project $PROJECT --force` が成功
- [ ] `gcloud functions list --project $PROJECT --regions asia-northeast1` に対象関数が居る
- [ ] `gcloud run services list --project $PROJECT --region asia-northeast1` に apiv2-* が居る
- [ ] Cloud Console → Cloud Run → apiv2-xxx → Permissions で allUsers = Cloud Run Invoker
- [ ] Client から test call が 200 で戻る
- [ ] server log に `USER_UNKNOWN_FIELDS` が出ていない
- [ ] （任意）`firebase functions:log --only apiv2Xxx --limit 20` で最新エラーを確認

---

## 関連スキル

- `mobile-firebase-setup` — 初回の Firebase プロビジョニング（本 skill は deploy 後の
  gotcha 潰し）
- `mobile-update-deploy` — client 側の payload エンコーディング修正を CI に流す
- `firestore-bulk-index-sync` — 同じ deploy workflow に組み込む REST 直叩き step
