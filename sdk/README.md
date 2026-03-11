# ServiceMatrix TypeScript SDK

FastAPI の OpenAPI スキーマから自動生成された TypeScript 型定義です。

## 使用方法

```typescript
import type { components, paths } from './typescript/schema'

// インシデント一覧 API の型
type ListIncidentsResponse = paths['/api/v1/incidents/']['get']['responses']['200']['content']['application/json']

// インシデント作成リクエストの型
type CreateIncidentBody = paths['/api/v1/incidents/']['post']['requestBody']['content']['application/json']
```

## 再生成

```bash
./scripts/generate_sdk.sh
```
