# ServiceMatrix API SDK ガイド

## TypeScript SDK

### インストール

```typescript
// sdk/typescript/schema.d.ts を直接インポート
import type { components, paths } from '../sdk/typescript/schema'
```

### 型の使い方

```typescript
// APIレスポンス型
type IncidentResponse = components['schemas']['IncidentResponse']
type PaginatedIncidents = components['schemas']['PaginatedResponse_IncidentResponse_']

// APIクライアント例（fetch）
async function getIncidents(): Promise<PaginatedIncidents> {
  const res = await fetch('/api/v1/incidents/')
  return res.json()
}
```

### 再生成

```bash
./scripts/generate_sdk.sh
```

## Python SDK

Python クライアントは FastAPI の httpx ベースクライアントで直接利用可能です。

```python
import httpx

async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
    response = await client.get("/api/v1/incidents/")
    data = response.json()
```
