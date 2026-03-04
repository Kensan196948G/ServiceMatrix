# Terraform デプロイガイド

## 前提条件

- Terraform >= 1.6.0
- AWS CLI 設定済み（適切なIAMロール）
- S3 バケット（Terraform state 保存用）

## クイックスタート

```bash
# 初期化（State バックエンド設定）
terraform init \
  -backend-config="bucket=servicematrix-terraform-state" \
  -backend-config="key=servicematrix/terraform.tfstate" \
  -backend-config="region=ap-northeast-1"

# 開発環境プラン確認
terraform plan \
  -var-file="environments/dev.tfvars" \
  -var="db_password=<your-password>"

# 開発環境デプロイ
terraform apply \
  -var-file="environments/dev.tfvars" \
  -var="db_password=<your-password>"
```

## モジュール構成

| モジュール | リソース |
|---------|---------|
| vpc | VPC・サブネット・NAT Gateway |
| rds | PostgreSQL 16・バックアップ設定 |
| ecs | Fargate クラスター・ALB・IAM |
| cloudfront | CDN・S3（フロントエンド）・APIプロキシ |

## セキュリティ考慮事項

- RDS は Private Subnet のみ配置（Public IP なし）
- ECS タスクは Private Subnet で動作
- `db_password` は `-var` で渡し、`.tfvars` に記述しない
- `deletion_protection = true`（RDS 誤削除防止）

## J-SOX コンプライアンス

- RDS バックアップ保持: 7日（最低要件）
- CloudWatch ログ保持: 30日（監査ログは別途対応）
- ストレージ暗号化: 有効
