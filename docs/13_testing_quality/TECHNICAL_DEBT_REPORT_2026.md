# 技術負債レポート 2026

## ServiceMatrix テスト品質・CI 改善レポート

**作成日**: 2026-03-11
**作成者**: ClaudeOS 設計改善ループ（6時間周期）
**対象ブランチ**: develop / main
**カバレッジ測定日**: 2026-03-10〜11

---

## 1. エグゼクティブサマリー

| 指標 | 現状 | 目標 | 評価 |
|------|------|------|------|
| 全体カバレッジ | 75.51% | 75% | ⚠️ 閾値ギリギリ |
| テスト行数 | 10,184 行 | — | ✅ 充実 |
| テスト/コード比率 | 3:1 | 2:1 以上 | ✅ 良好 |
| 危険域モジュール数 | 7 モジュール | 0 | ❌ 要対応 |
| CI 依存関係手動管理 | 手動リスト | pyproject.toml 統合 | ❌ 技術負債 |
| ハードコードシークレット | 0 件 | 0 件 | ✅ クリア |
| type: ignore 使用箇所 | 5 箇所 | 可能な限り削減 | 🟡 許容範囲 |

**総評**: 閾値 75% をかろうじてクリアしているが、API 層の複数モジュールが 50% 未満であり、J-SOX コンプライアンス観点から audit.py・compliance.py の改善が急務。

---

## 2. モジュール別カバレッジ（降順）

### 2.1 高カバレッジ（80%以上）✅

| モジュール | カバレッジ | 備考 |
|-----------|-----------|------|
| `src/services/sla_monitor_service.py` | 99% | APScheduler 統合 |
| `src/api/v1/auth.py` | 100% | JWT 認証 |
| `src/api/v1/health.py` | 100% | ヘルスチェック |
| `src/api/v1/changes.py` | 100% | 変更管理 |
| `src/api/v1/problems.py` | 100% | 問題管理 |
| `src/api/v1/service_requests.py` | 100% | SR管理 |
| `src/services/incident_service.py` | ~85% | SLA計算 |
| `src/services/change_service.py` | ~80% | リスクスコア |

### 2.2 中カバレッジ（50〜79%）🟡

| モジュール | カバレッジ | 改善優先度 |
|-----------|-----------|-----------|
| `src/api/v1/sla.py` | 68% | 低 |
| `src/api/v1/webhooks.py` | 62% | 低 |
| `src/api/v1/ai.py` | 55% | 中 |
| `src/middleware/audit.py` | 58% | 中 |

### 2.3 危険域（50%未満）❌ — 優先対応必須

| モジュール | カバレッジ | ビジネス影響 | 優先度 |
|-----------|-----------|------------|--------|
| `src/api/v1/compliance.py` | **35%** | J-SOX 準拠 | 🔴 最高 |
| `src/api/v1/websocket.py` | **36%** | リアルタイム通知 | 🟠 高 |
| `src/api/v1/audit.py` | **42%** | J-SOX 監査ログ | 🔴 最高 |
| `src/api/v1/cmdb.py` | **44%** | CMDB 整合性 | 🟠 高 |
| `src/core/database.py` | **47%** | DB 接続・セッション | 🟠 高 |
| `src/api/v1/incidents.py` | **48%** | コア ITIL 機能 | 🟠 高 |
| `src/api/v1/reports.py` | **49%** | 経営レポーティング | 🟡 中 |

---

## 3. 技術負債分析

### 3.1 CI 依存関係管理（優先度: 高）

**問題**:
```yaml
# 現状: .github/workflows/ci.yml の手動リスト管理
pip install fastapi "uvicorn[standard]" "sqlalchemy[asyncio]" alembic \
  pydantic "pydantic-settings" \
  "python-jose[cryptography]" "passlib[bcrypt]" "bcrypt>=3.2,<4.0" \
  httpx redis structlog apscheduler slowapi \
  pytest pytest-asyncio pytest-cov anyio "anyio[trio]" \
  aiosqlite python-multipart
```

**発生した問題**: `slowapi` が `pyproject.toml` に定義済みにも関わらず CI リストから漏れ、6日間 main ブランチが FAILURE 状態だった（2026-03-04〜10）。

**推奨対応**:
```yaml
# 改善案: pyproject.toml ベースのインストール
- name: Install dependencies
  run: |
    pip install -e ".[dev]"
```

**効果**: 依存関係の Single Source of Truth（pyproject.toml のみ）を実現し、同様の漏れを構造的に防止。

### 3.2 型チェック抑制（優先度: 低〜中）

**現状**: `# type: ignore` が 5 箇所使用

| ファイル | 箇所 | 理由 |
|---------|------|------|
| `src/api/v1/notifications.py` | 複数 | FastAPI 型推論の限界 |
| `src/main.py` | 1 箇所 | SlowAPI の型定義不完全 |

**推奨対応**: mypy の stubs が整備されれば順次削除。現時点では許容範囲。

### 3.3 E2E テスト安定性（優先度: 中）

**問題**:
- E2E テストは `continue-on-error: true` で CI ブロッカーではない
- バックエンド起動に `sleep 5` / フロントエンドに `sleep 8` の固定待機
- playwright-report が存在しない場合のアーティファクトエラー

**推奨対応**:
```yaml
- name: Wait for backend
  run: |
    for i in {1..30}; do
      curl -sf http://localhost:8000/api/v1/health && break
      sleep 2
    done
```

### 3.4 pytest-xdist 並列テスト（優先度: 低）

**現状**: 645 テストが逐次実行（約 45〜60 秒）
**推奨**: `pytest-xdist` 導入で並列実行（推定 40% 短縮）
**注意**: SQLite in-memory は並列共有不可 → 各ワーカーに独立 DB が必要

---

## 4. 改善ロードマップ

### Phase A（即時対応 — 2週間以内）

| # | タスク | 担当 | 工数 |
|---|--------|------|------|
| A1 | `compliance.py` テスト追加（35% → 70%以上） | Tester | 中 |
| A2 | `audit.py` テスト追加（42% → 70%以上） | Tester | 中 |
| A3 | CI を `pip install -e ".[dev]"` に移行 | Ops | 小 |

### Phase B（短期 — 1ヶ月以内）

| # | タスク | 担当 | 工数 |
|---|--------|------|------|
| B1 | `incidents.py` テスト追加（48% → 70%以上） | Tester | 中 |
| B2 | `cmdb.py` テスト追加（44% → 70%以上） | Tester | 中 |
| B3 | E2E ヘルスチェック wait ループ導入 | Ops | 小 |
| B4 | websocket テスト追加（36% → 60%以上） | DevAPI | 大 |

### Phase C（中期 — 3ヶ月以内）

| # | タスク | 担当 | 工数 |
|---|--------|------|------|
| C1 | pytest-xdist 並列化 | Ops | 中 |
| C2 | カバレッジ閾値を 80% に引き上げ | QA | 小 |
| C3 | mypy strict モード有効化 | Architect | 大 |

---

## 5. CI パイプライン現状分析

### 5.1 ジョブ構成

```
CI Pipeline (ci.yml)
├── lint-markdown          ← markdownlint（|| true で警告扱い）
├── validate-docs-structure ← 必須ドキュメント存在確認
├── validate-config-files  ← YAML 構文確認
├── security-scan          ← TruffleHog（continue-on-error）
├── python-lint            ← ruff（|| true で警告扱い）
├── python-test            ← pytest 645テスト 75.51%カバレッジ ← CIゲート
├── frontend-build         ← Next.js build + type-check
├── docker-lint            ← hadolint（continue-on-error）
├── lint                   ← ruff check + format（厳格）
├── type-check             ← mypy（continue-on-error）
├── security               ← bandit（|| true で警告扱い）
├── e2e-test               ← Playwright（continue-on-error）
└── ci-summary             ← 全ジョブ集約レポート
```

### 5.2 実質的な CI ブロッカー

以下のジョブのみが CI を FAIL させる（他は `continue-on-error` または `|| true`）:
1. `validate-docs-structure` — 必須ドキュメント欠如
2. `python-test` — テスト失敗 / カバレッジ 75% 未満
3. `frontend-build` — ビルドエラー / 型エラー
4. `lint` — ruff エラー（format チェック含む）

---

## 6. セキュリティ観点

### 6.1 シークレット管理 ✅
- ハードコードシークレット: **0 件**（TruffleHog・手動確認で確認）
- `config.py` の `secret_key` デフォルト値は `noqa: S105` 付き（.env で上書き必須）
- 本番環境: AWS SSM Parameter Store（Terraform Step44 実装済み）

### 6.2 bandit スキャン ✅
- `bandit -r src/ -ll --skip B101` で実行
- `-ll` = 中程度以上の重大度のみ検出（B101: assert除外）
- 現時点で既知の重大脆弱性なし

---

## 7. 推奨アクション（最優先）

### 今すぐ対応すべき項目

```
1. [A1] compliance.py テスト作成
   ファイル: tests/test_compliance.py
   目標: 35% → 70%
   理由: J-SOX コンプライアンス機能のテスト皆無は監査リスク

2. [A2] audit.py テスト作成
   ファイル: tests/test_audit_api.py
   目標: 42% → 70%
   理由: SHA-256 ハッシュチェーン・監査ログ完全性の検証が必要

3. [A3] CI 依存関係を pyproject.toml ベースに移行
   ファイル: .github/workflows/ci.yml
   変更: pip install リスト → pip install -e ".[dev]"
   理由: 再発防止（slowapi 漏れ問題の根本解決）
```

---

## 8. 参照ドキュメント

| ドキュメント | パス |
|------------|------|
| 品質ゲート定義 | `docs/13_testing_quality/QUALITY_GATE_DEFINITION.md` |
| テスト戦略 | `docs/13_testing_quality/TEST_STRATEGY.md` |
| ユニットテストポリシー | `docs/13_testing_quality/UNIT_TEST_POLICY.md` |
| セキュリティテストポリシー | `docs/13_testing_quality/SECURITY_TEST_POLICY.md` |
| J-SOX 監査ログスキーマ | `docs/11_data_model/AUDIT_LOG_SCHEMA.md` |
| アクセス制御モデル | `docs/06_security_compliance/ACCESS_CONTROL_MODEL.md` |

---

_このレポートは ClaudeOS 設計改善ループ（6時間周期）により自動生成されました。_
_次回更新: 2026-03-11 06:00 UTC 以降の設計改善ループ実行時_
