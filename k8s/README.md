# ServiceMatrix Kubernetes デプロイメントガイド

## 前提条件

- Kubernetes 1.25+
- Helm 3.10+
- kubectl コンフィグ設定済み
- Nginx Ingress Controller インストール済み

## ディレクトリ構成

```
k8s/
└── helm/
    └── servicematrix/
        ├── Chart.yaml
        ├── values.yaml           # デフォルト値
        ├── values-prod.yaml      # 本番用オーバーライド
        └── templates/
            ├── _helpers.tpl
            ├── namespace.yaml
            ├── backend/          # FastAPI バックエンド
            ├── frontend/         # Next.js フロントエンド
            ├── postgres/         # PostgreSQL (StatefulSet)
            ├── redis/            # Redis
            ├── ingress.yaml      # Nginx Ingress
            └── secrets.yaml      # Kubernetes Secret
```

## インストール

### 1. イメージのビルドとプッシュ

```bash
# バックエンドイメージ
docker build -t your-registry/servicematrix-backend:0.7.0 .
docker push your-registry/servicematrix-backend:0.7.0

# フロントエンドイメージ
docker build -t your-registry/servicematrix-frontend:0.7.0 ./frontend
docker push your-registry/servicematrix-frontend:0.7.0
```

### 2. 開発環境へのインストール

```bash
helm install servicematrix k8s/helm/servicematrix \
  --set backend.env.SECRET_KEY="your-secret-key" \
  --set postgres.env.POSTGRES_PASSWORD="your-db-password" \
  --set redis.password="your-redis-password"
```

### 3. 本番環境へのインストール

```bash
helm install servicematrix k8s/helm/servicematrix \
  -f k8s/helm/servicematrix/values-prod.yaml \
  --set global.imageRegistry="your-registry.example.com/" \
  --set backend.env.SECRET_KEY="$(openssl rand -hex 32)" \
  --set postgres.env.POSTGRES_PASSWORD="$(openssl rand -hex 16)" \
  --set redis.password="$(openssl rand -hex 16)" \
  --set ingress.host="servicematrix.your-domain.com"
```

### 4. アップグレード

```bash
helm upgrade servicematrix k8s/helm/servicematrix \
  -f k8s/helm/servicematrix/values-prod.yaml \
  --set backend.image.tag="0.8.0" \
  --set frontend.image.tag="0.8.0" \
  --reuse-values
```

## Helm Lint

```bash
helm lint k8s/helm/servicematrix/
```

## デプロイ確認

```bash
# Pod 状態確認
kubectl get pods -n servicematrix

# Service 確認
kubectl get svc -n servicematrix

# Ingress 確認
kubectl get ingress -n servicematrix

# HPA 確認
kubectl get hpa -n servicematrix

# バックエンドログ確認
kubectl logs -n servicematrix -l app.kubernetes.io/component=backend --tail=100
```

## アンインストール

```bash
helm uninstall servicematrix
# Namespace は手動削除（helm.sh/resource-policy: keep により Secret は残る）
kubectl delete namespace servicematrix
```

## セキュリティ注意事項

- `values.yaml` に含まれるパスワードはデフォルト値です。**本番環境では必ず上書きしてください**。
- Secret の値は `stringData` で管理され、Kubernetes が自動的に Base64 エンコードします。
- 本番環境では [External Secrets Operator](https://external-secrets.io/) や Vault との連携を推奨します。
- `helm.sh/resource-policy: keep` により `helm uninstall` 後も Secret は保持されます。

## アーキテクチャ

```
Internet
    │
    ▼
[Nginx Ingress]
    │
    ├── /api/* ──► [Backend Service :8000] ──► [Backend Pods (HPA: 2-10)]
    │                                               │
    │                                         ┌─────┴─────┐
    │                                    [PostgreSQL]   [Redis]
    │                                    (StatefulSet)
    │
    └── /* ──────► [Frontend Service :3000] ──► [Frontend Pods (HPA: 2-5)]
```
