# クラウドサービス対応（GCP↔AWS）とアイコン種別

## arch_diagram.py のアイコン種別（icon引数）
lb=ロードバランサ / armor=WAF・シールド / iap=認証(鍵シールド) / webapp=Webアプリ /
apigw=API Gateway({ }) / chat=会話/分析API / agent=AIエージェント(ロボット) /
vertex=AIモデル基盤(4色スパーク) / bigquery=DWH(リング+ルーペ) / dataform=ELT(テーブル) /
build=CI/CD(ギア) / datastream=取込(矢印) / connector=VPCコネクタ / memory=Redis(チップ) /
nat=NAT(ルーター) / globe=外部API(地球)

## GCP ↔ AWS 早見
| 役割 | GCP | AWS |
|---|---|---|
| ロードバランサ | Cloud Load Balancing | ALB/ELB(+Global Accelerator) |
| WAF/DDoS | Cloud Armor | AWS WAF + Shield |
| 認証ゲート | Identity-Aware Proxy(IAP) | ALB認証+Cognito(≒Verified Access) |
| サーバーレス実行 | Cloud Run | Fargate / App Runner |
| API Gateway | API Gateway | API Gateway |
| LLM/AI基盤 | Vertex AI / Gemini | Bedrock / SageMaker |
| AIエージェント | Vertex AI Agent(ADK) | Bedrock Agents |
| DWH/分析 | BigQuery | Redshift / Athena |
| ELT変換 | Dataform | dbt (on Glue) |
| CI/CD | Cloud Build | CodeBuild / CodePipeline |
| データ取込/CDC | DTS / Datastream | DMS / Glue / AppFlow |
| VPC接続(サーバーレス) | Serverless VPC Access | Lambda/Fargate VPC(ENI) |
| キャッシュ | Memorystore(Redis) | ElastiCache |
| 外向き出口 | Cloud NAT | NAT Gateway |
| 権限 | Cloud IAM | IAM |
| シークレット | Secret Manager | Secrets Manager |
| データ持出境界 | VPC Service Controls | (直接の等価なし)≒データ境界+PrivateLink |
| ログ/監視 | Cloud Logging/Monitoring | CloudWatch(+CloudTrail) |
| IaC | Terraform | Terraform |

## GCP固有の注意（突っ込まれ対策）
- サブネットに public/private の区別を持ち込まない。Cloud Run はサーバーレスで、VPCへは
  Serverless VPC Access コネクタ経由。外向き通信は Cloud NAT。エッジは Google Front End。
- 分析は BigQuery 中心（Redshift+Athena を1本に）。
- 「保存しない」設計は VPC Service Controls＋Cloud NAT＋ログ抑止で構造的に担保。
