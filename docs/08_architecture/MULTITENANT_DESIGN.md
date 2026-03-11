# マルチテナントアーキテクチャ設計書

**Issue**: #48 マルチテナント対応
**作成日**: 2026-03-11
**ステータス**: 設計完了・実装待ち

---

## 1. 概要

### 目的

ServiceMatrix を複数の組織（テナント）が安全に共有利用できるマルチテナント SaaS 基盤へ進化させる。

### スコープ

| 対象 | 内容 |
|------|------|
| データ分離 | PostgreSQL Row Level Security (RLS) によるテナント間完全分離 |
| 認証拡張 | JWT ペイロードへの `org_id` 追加 |
| API フィルタリング | 全エンドポイントでのテナントスコープ強制 |
| 既存データ移行 | デフォルト組織への割り当て |

### 除外スコープ

- フロントエンドマルチテナント UI（Phase D にて対応）
- テナント課金・使用量計測
- カスタムドメイン対応

---

## 2. テナント識別方式

### 基本方針

JWT claims の `org_id` フィールドをテナント識別子として使用する。

### 識別フロー

```
クライアント
  ↓ Bearer Token (JWT)
FastAPI ミドルウェア
  ↓ JWT デコード → org_id 抽出
  ↓ PostgreSQL SET LOCAL app.current_org_id = '{org_id}'
RLS ポリシー
  ↓ current_setting('app.current_org_id') で行フィルタリング
テナントスコープデータ
```

### 補助識別子（フォールバック）

JWT に `org_id` が存在しない場合、`X-Org-ID` HTTP ヘッダーを参照する（後方互換）。

---

## 3. Organization モデル設計

### DDL

```sql
CREATE TABLE organizations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(255) NOT NULL,
    slug        VARCHAR(100) UNIQUE NOT NULL,       -- URL識別子 (例: "acme-corp")
    settings    JSONB DEFAULT '{}',                 -- テナント固有設定
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- インデックス
CREATE UNIQUE INDEX idx_organizations_slug ON organizations(slug);
CREATE INDEX idx_organizations_is_active ON organizations(is_active);
```

### settings JSONB スキーマ例

```json
{
  "max_users": 100,
  "sla_multiplier": 1.0,
  "allowed_domains": ["example.com"],
  "features": {
    "ai_triage": true,
    "webhook_enabled": true
  },
  "timezone": "Asia/Tokyo",
  "locale": "ja"
}
```

### slug 命名規則

- 小文字英数字とハイフンのみ（正規表現: `^[a-z0-9-]+$`）
- 3〜100 文字
- 変更不可（URL 安定性のため）

---

## 4. 既存テーブルへの org_id 追加

### 対象テーブル

| テーブル | 追加カラム | インデックス |
|---------|-----------|------------|
| incidents | org_id UUID REFERENCES organizations(id) | idx_incidents_org_id |
| changes | org_id UUID REFERENCES organizations(id) | idx_changes_org_id |
| problems | org_id UUID REFERENCES organizations(id) | idx_problems_org_id |
| cmdb_items | org_id UUID REFERENCES organizations(id) | idx_cmdb_items_org_id |

### マイグレーション DDL

```sql
-- incidents
ALTER TABLE incidents ADD COLUMN org_id UUID REFERENCES organizations(id) ON DELETE SET NULL;
CREATE INDEX idx_incidents_org_id ON incidents(org_id);

-- changes
ALTER TABLE changes ADD COLUMN org_id UUID REFERENCES organizations(id) ON DELETE SET NULL;
CREATE INDEX idx_changes_org_id ON changes(org_id);

-- problems
ALTER TABLE problems ADD COLUMN org_id UUID REFERENCES organizations(id) ON DELETE SET NULL;
CREATE INDEX idx_problems_org_id ON problems(org_id);

-- cmdb_items
ALTER TABLE cmdb_items ADD COLUMN org_id UUID REFERENCES organizations(id) ON DELETE SET NULL;
CREATE INDEX idx_cmdb_items_org_id ON cmdb_items(org_id);
```

---

## 5. Row Level Security (RLS) ポリシー

### 設計原則

- すべてのテナントスコープテーブルに RLS を有効化
- アプリケーション側で `SET LOCAL app.current_org_id` をトランザクション開始時に実行
- スーパーユーザー・管理ロールは RLS バイパス可能

### RLS 実装

```sql
-- incidents テーブル
ALTER TABLE incidents ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON incidents
    AS PERMISSIVE
    FOR ALL
    TO servicematrix_app
    USING (org_id = current_setting('app.current_org_id', TRUE)::UUID)
    WITH CHECK (org_id = current_setting('app.current_org_id', TRUE)::UUID);

-- changes テーブル
ALTER TABLE changes ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON changes
    AS PERMISSIVE
    FOR ALL
    TO servicematrix_app
    USING (org_id = current_setting('app.current_org_id', TRUE)::UUID)
    WITH CHECK (org_id = current_setting('app.current_org_id', TRUE)::UUID);

-- problems テーブル
ALTER TABLE problems ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON problems
    AS PERMISSIVE
    FOR ALL
    TO servicematrix_app
    USING (org_id = current_setting('app.current_org_id', TRUE)::UUID)
    WITH CHECK (org_id = current_setting('app.current_org_id', TRUE)::UUID);

-- cmdb_items テーブル
ALTER TABLE cmdb_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON cmdb_items
    AS PERMISSIVE
    FOR ALL
    TO servicematrix_app
    USING (org_id = current_setting('app.current_org_id', TRUE)::UUID)
    WITH CHECK (org_id = current_setting('app.current_org_id', TRUE)::UUID);
```

### 管理者バイパス

```sql
-- システム管理者ロールは RLS を迂回
ALTER TABLE incidents FORCE ROW LEVEL SECURITY;  -- スーパーユーザーも RLS 対象
GRANT servicematrix_admin TO system_admin_users; -- 管理者は別途 RLS バイパスポリシーを付与
```

---

## 6. JWT スキーマ変更

### 現行ペイロード

```json
{
  "sub": "user-uuid",
  "type": "access",
  "exp": 1234567890
}
```

### 拡張後ペイロード

```json
{
  "sub": "user-uuid",
  "org_id": "org-uuid",
  "org_slug": "acme-corp",
  "type": "access",
  "exp": 1234567890
}
```

### security.py 変更点

`create_access_token` 呼び出し時に `org_id` を `data` dict に含める。

```python
# 変更前
token = create_access_token({"sub": str(user.user_id)})

# 変更後
token = create_access_token({
    "sub": str(user.user_id),
    "org_id": str(user.org_id),
    "org_slug": user.organization.slug,
})
```

---

## 7. FastAPI ミドルウェア設計

### TenantMiddleware

```python
class TenantMiddleware(BaseHTTPMiddleware):
    """
    JWT または X-Org-ID ヘッダーからテナント情報を抽出し、
    リクエストステートと PostgreSQL セッション変数に設定する。
    """

    async def dispatch(self, request: Request, call_next):
        org_id = await self._extract_org_id(request)
        request.state.org_id = org_id

        # DB セッションで SET LOCAL を実行するため
        # context var に保存（get_db() 内で参照）
        org_id_ctx_var.set(org_id)

        return await call_next(request)

    async def _extract_org_id(self, request: Request) -> str | None:
        # 1. Authorization ヘッダー（JWT）を優先
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            try:
                payload = decode_token(auth[7:])
                return payload.get("org_id")
            except ValueError:
                pass

        # 2. X-Org-ID ヘッダー（フォールバック）
        return request.headers.get("X-Org-ID")
```

### get_db() 拡張

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        org_id = org_id_ctx_var.get()
        if org_id:
            await session.execute(
                text("SET LOCAL app.current_org_id = :org_id"),
                {"org_id": org_id}
            )
        yield session
```

### テナントスコープ依存関数

```python
async def get_current_tenant_id(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> uuid.UUID:
    """現在のテナント org_id を返す。未設定の場合は 400 エラー。"""
    org_id = getattr(request.state, "org_id", None)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="テナント情報が取得できません。org_id が必要です。"
        )
    return uuid.UUID(org_id)
```

---

## 8. 移行戦略

### デフォルト組織の作成

既存データは「デフォルト組織」に割り当てる。

```sql
-- デフォルト組織の挿入
INSERT INTO organizations (id, name, slug, is_active)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Default Organization',
    'default',
    TRUE
);

-- 既存データへの org_id 付与
UPDATE incidents SET org_id = '00000000-0000-0000-0000-000000000001' WHERE org_id IS NULL;
UPDATE changes   SET org_id = '00000000-0000-0000-0000-000000000001' WHERE org_id IS NULL;
UPDATE problems  SET org_id = '00000000-0000-0000-0000-000000000001' WHERE org_id IS NULL;
UPDATE cmdb_items SET org_id = '00000000-0000-0000-0000-000000000001' WHERE org_id IS NULL;

-- NULL 禁止への変更（移行後）
ALTER TABLE incidents ALTER COLUMN org_id SET NOT NULL;
ALTER TABLE changes   ALTER COLUMN org_id SET NOT NULL;
ALTER TABLE problems  ALTER COLUMN org_id SET NOT NULL;
ALTER TABLE cmdb_items ALTER COLUMN org_id SET NOT NULL;
```

### ユーザー移行

既存ユーザーをデフォルト組織に関連付ける。

```sql
ALTER TABLE users ADD COLUMN org_id UUID REFERENCES organizations(id);
UPDATE users SET org_id = '00000000-0000-0000-0000-000000000001' WHERE org_id IS NULL;
ALTER TABLE users ALTER COLUMN org_id SET NOT NULL;
```

### ロールバック計画

RLS 有効化前に各フェーズでバックアップを取得。問題発生時は以下で RLS を無効化。

```sql
ALTER TABLE incidents DISABLE ROW LEVEL SECURITY;
```

---

## 9. Phase 実装計画

### Phase A: Organization モデル + マイグレーション

**目標**: Organization テーブルの作成とデータ移行

**タスク**:
1. `src/models/organization.py` 作成
2. `src/schemas/organization.py` 作成
3. Alembic マイグレーション: `002_add_organizations.py`
   - organizations テーブル作成
   - incidents/changes/problems/cmdb_items に org_id 追加
   - デフォルト組織データ挿入
   - 既存データ移行
4. `tests/test_organization_model.py` 作成

**完了基準**: マイグレーション適用成功・既存テスト全通過

---

### Phase B: JWT org_id + ミドルウェア

**目標**: 認証フローへのテナント識別統合

**タスク**:
1. `src/middleware/tenant.py` 作成（TenantMiddleware）
2. `src/core/security.py` 更新（create_access_token に org_id 追加）
3. `src/middleware/rbac.py` 更新（get_current_user で org_id 検証）
4. `src/core/database.py` 更新（get_db で SET LOCAL 実行）
5. `src/api/v1/auth.py` 更新（ログイン時に org_id を JWT に含める）
6. `tests/test_tenant_middleware.py` 作成

**完了基準**: 認証トークンに org_id が含まれること・ミドルウェアテスト通過

---

### Phase C: RLS 適用 + API フィルタリング

**目標**: 完全なテナント分離の実現

**タスク**:
1. Alembic マイグレーション: `003_enable_rls.py`
   - 各テーブルの RLS 有効化
   - tenant_isolation ポリシー作成
2. `src/api/v1/incidents.py` 更新（テナントスコープ依存追加）
3. `src/api/v1/changes.py` 更新
4. `src/api/v1/problems.py` 更新
5. `src/api/v1/cmdb.py` 更新
6. `tests/test_tenant_isolation.py` 作成（テナント間データ漏洩テスト）

**完了基準**: テナント A のデータがテナント B から参照できないこと

---

### Phase D: フロントエンド対応

**目標**: Next.js フロントエンドのマルチテナント対応

**タスク**:
1. テナント選択ページ（`/select-tenant`）
2. JWT 更新ロジック（テナント切替時）
3. テナントコンテキスト（React Context API）
4. `X-Org-ID` ヘッダーの自動付与（Axios インターセプター）

**完了基準**: フロントエンドからテナントスコープ API 呼び出し成功

---

## 10. セキュリティ考慮点

### テナント間データリーク防止

| リスク | 対策 |
|--------|------|
| SQL インジェクションによる org_id 偽装 | パラメータ化クエリ強制・SQLAlchemy ORM 使用 |
| JWT org_id 改ざん | HMAC-SHA256 署名検証（jose ライブラリ） |
| RLS バイパス攻撃 | superuser 接続禁止・アプリ専用 DB ロール使用 |
| サービス間通信でのテナント混在 | Internal API にも org_id ヘッダー伝播 |
| ログ・監査ログへの org_id 漏洩 | 監査ログに org_id を含めるが、クロステナント参照は管理者のみ |

### 最小権限原則

```sql
-- アプリ用 DB ロール（RLS が適用される）
CREATE ROLE servicematrix_app LOGIN PASSWORD '***';
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO servicematrix_app;

-- 管理者用 DB ロール（RLS バイパス可能）
CREATE ROLE servicematrix_admin LOGIN PASSWORD '***';
GRANT servicematrix_app TO servicematrix_admin;
ALTER ROLE servicematrix_admin BYPASSRLS;
```

### 監査ログの org_id 記録

既存の `AuditLog` モデルに `org_id` カラムを追加し、テナント単位での監査証跡を保証する。

```sql
ALTER TABLE audit_logs ADD COLUMN org_id UUID REFERENCES organizations(id);
```

### トークンリフレッシュ時の org_id 検証

リフレッシュトークン使用時に、`org_id` がデータベースの現在値と一致するか検証する。組織が無効化（`is_active = FALSE`）された場合は即時トークン無効化。

---

## 参考資料

- PostgreSQL RLS ドキュメント: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- python-jose JWT ライブラリ: https://python-jose.readthedocs.io/
- SQLAlchemy 2.0 Async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- ITIL 4 マルチテナント SaaS 運用ガイドライン

---

_設計書バージョン: 1.0.0_
_承認者: CTO / Architect / Security Lead_
