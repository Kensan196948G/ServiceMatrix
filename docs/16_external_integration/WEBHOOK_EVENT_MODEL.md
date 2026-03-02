# Webhook イベントモデル

ServiceMatrix Webhook Event Model

Version: 1.0
Status: Active
Classification: Internal Technical Document
Last Updated: 2026-03-02

---

## 1. 概要

本ドキュメントは、ServiceMatrix における Webhook イベントの設計モデル・
イベント定義・ペイロード仕様・処理フローを定義する。
ServiceMatrix は GitHub Webhook を主要な外部イベント入力として使用し、
内部イベントバスとして処理する。

---

## 2. Webhook アーキテクチャ

### 2.1 全体フロー

```
Webhook アーキテクチャ:

  GitHub
    │
    │ HTTPS POST (署名付き)
    ▼
  [Webhook Receiver API]
    │ 署名検証
    │ イベント解析
    ▼
  [Event Router]
    ├─── issues ──────────────▶ [Incident/Change Processor]
    ├─── pull_request ─────────▶ [PR Governance Processor]
    ├─── pull_request_review ──▶ [SoD Validation Processor]
    ├─── push ─────────────────▶ [Code Change Tracker]
    ├─── workflow_run ─────────▶ [CI Quality Gate Processor]
    ├─── deployment_status ────▶ [Deploy Status Tracker]
    └─── release ──────────────▶ [Version Sync Processor]
          │
          ▼
    [Event Store (PostgreSQL)]
    [Audit Log]
    [WebSocket Broadcaster]
```

### 2.2 Webhook エンドポイント

| エンドポイント | メソッド | 用途 |
|--------------|---------|------|
| `/api/webhooks/github` | POST | GitHub Webhook 受信 |
| `/api/webhooks/status` | GET | Webhook 受信ステータス確認 |
| `/api/webhooks/replay/{event_id}` | POST | イベント再処理（管理者のみ）|

---

## 3. 受信イベント定義

### 3.1 Issues イベント

GitHub Issues の変更を受信して ITSM エンティティと同期する。

| action | 用途 | 処理内容 |
|--------|------|---------|
| `opened` | Issue 作成 | ServiceMatrix エンティティ作成 |
| `closed` | Issue クローズ | エンティティステータスを Resolved に更新 |
| `reopened` | Issue 再オープン | エンティティを再オープン |
| `assigned` | アサイニー変更 | 担当者同期 |
| `labeled` | ラベル変更 | 優先度・カテゴリ同期 |
| `edited` | Issue 編集 | タイトル・本文同期 |

```json
Issues イベントペイロード（主要フィールド）:
{
  "action": "opened",
  "issue": {
    "number": 42,
    "title": "[INC-001] 本番データベース応答遅延",
    "state": "open",
    "labels": [{"name": "incident"}, {"name": "priority:p1"}],
    "assignee": {"login": "ops-engineer"},
    "created_at": "2026-03-02T10:00:00Z",
    "body": "..."
  },
  "repository": {
    "full_name": "org/servicematrix"
  },
  "sender": {
    "login": "incident-reporter"
  }
}
```

### 3.2 Pull Request イベント

| action | 用途 | 処理内容 |
|--------|------|---------|
| `opened` | PR 作成 | 変更要求との関連付け・SoD 事前チェック |
| `synchronize` | コミット追加 | CI トリガー・品質ゲート再評価 |
| `closed` (merged=true) | マージ | 変更記録・デプロイトリガー |
| `closed` (merged=false) | クローズ | 変更却下記録 |
| `ready_for_review` | レビュー依頼 | レビュアー自動アサイン |
| `review_requested` | レビュアー指定 | 通知送信 |

```json
Pull Request イベントペイロード（主要フィールド）:
{
  "action": "opened",
  "pull_request": {
    "number": 123,
    "title": "[RFC-007] 認証ミドルウェアの刷新",
    "state": "open",
    "user": {"login": "developer-a"},
    "base": {"ref": "main"},
    "head": {"ref": "feature/rfc-007-auth-middleware"},
    "requested_reviewers": [{"login": "tech-lead"}],
    "merged": false,
    "mergeable": true
  }
}
```

### 3.3 Pull Request Review イベント

| action | review.state | 用途 | 処理内容 |
|--------|-------------|------|---------|
| `submitted` | `approved` | 承認 | SoD 検証・承認記録 |
| `submitted` | `changes_requested` | 修正要求 | PR ステータス更新 |
| `submitted` | `commented` | コメント | 記録のみ |
| `dismissed` | - | 承認取消 | 承認記録の取消 |

### 3.4 Workflow Run イベント

CI/CD パイプラインの実行結果を受信して品質ゲートに連携する。

| action | conclusion | 用途 | 処理内容 |
|--------|-----------|------|---------|
| `completed` | `success` | CI 成功 | 品質ゲート通過記録 |
| `completed` | `failure` | CI 失敗 | PR ブロック・通知 |
| `completed` | `cancelled` | CI キャンセル | 記録のみ |

### 3.5 Deployment Status イベント

| state | 用途 | 処理内容 |
|-------|------|---------|
| `pending` | デプロイ開始 | デプロイ記録開始 |
| `in_progress` | デプロイ中 | ステータス更新 |
| `success` | デプロイ完了 | SLA 影響記録・通知 |
| `failure` | デプロイ失敗 | インシデント自動作成・ロールバックトリガー |
| `error` | デプロイエラー | P1 インシデント自動作成 |

---

## 4. 内部イベント定義

ServiceMatrix が内部的に発行するイベント。

### 4.1 インシデント管理イベント

| イベント名 | トリガー | 購読者 |
|-----------|--------|--------|
| `incident.created` | インシデント作成 | SLA エンジン・通知サービス |
| `incident.updated` | インシデント更新 | 監査ログ・通知サービス |
| `incident.resolved` | インシデント解決 | SLA エンジン・レポートサービス |
| `incident.sla_breach_warning` | SLA 違反警告 | 通知サービス・エスカレーション |
| `incident.sla_breached` | SLA 違反発生 | 監査ログ・経営報告 |

### 4.2 変更管理イベント

| イベント名 | トリガー | 購読者 |
|-----------|--------|--------|
| `change.requested` | 変更要求作成 | 承認フロー・GitHub Issue 作成 |
| `change.approved` | 変更承認 | デプロイパイプライン・通知 |
| `change.rejected` | 変更却下 | 申請者通知・監査ログ |
| `change.deployed` | 変更デプロイ完了 | CMDB 更新・監査ログ |
| `change.rolled_back` | ロールバック実行 | インシデント作成・監査ログ |

### 4.3 AI エージェントイベント

| イベント名 | トリガー | 購読者 |
|-----------|--------|--------|
| `ai.suggestion_created` | AI 提案生成 | 承認キュー・通知サービス |
| `ai.suggestion_approved` | AI 提案承認 | 実行エンジン・監査ログ |
| `ai.suggestion_rejected` | AI 提案却下 | AI フィードバックシステム |
| `ai.emergency_stop` | 緊急停止発動 | AI エンジン停止・アラート |

---

## 5. イベントペイロード標準フォーマット

### 5.1 内部イベントの標準構造

```json
{
  "event_id": "evt-{uuid}",
  "event_type": "incident.created",
  "version": "1.0",
  "timestamp": "2026-03-02T10:00:00.000Z",
  "source": "incident-manager",
  "correlation_id": "req-{uuid}",
  "actor": {
    "user_id": "usr-{uuid}",
    "user_name": "operator",
    "role": "operator"
  },
  "data": {
    "incident_id": "inc-{uuid}",
    "title": "...",
    "priority": "P1"
  },
  "metadata": {
    "schema_version": "1.0",
    "environment": "production"
  }
}
```

### 5.2 フィールド定義

| フィールド | 型 | 必須 | 説明 |
|----------|-----|------|------|
| event_id | string (UUID) | Yes | イベント一意識別子 |
| event_type | string | Yes | イベント種別（{domain}.{action}形式）|
| version | string | Yes | イベントスキーマバージョン |
| timestamp | ISO 8601 | Yes | イベント発生日時（UTC）|
| source | string | Yes | イベント発生元サービス名 |
| correlation_id | string | No | リクエスト追跡 ID |
| actor | object | Yes | 操作者情報 |
| data | object | Yes | イベント固有データ |
| metadata | object | No | 付加メタデータ |

---

## 6. エラーハンドリングと再試行

### 6.1 Webhook 処理失敗時の対応

| 失敗種別 | 対応 | 再試行 |
|---------|------|--------|
| 署名検証失敗 | 400 返却・セキュリティアラート | なし |
| イベント解析エラー | 422 返却・デッドレターキュー保存 | なし |
| 処理タイムアウト | 504・再試行キュー保存 | 最大 5 回 |
| 内部エラー | 500・再試行キュー保存 | 最大 3 回（指数バックオフ）|

### 6.2 再試行キュー設計

| パラメータ | 値 |
|----------|-----|
| 最大再試行回数 | 5 回 |
| 初回待機時間 | 30 秒 |
| バックオフ係数 | 2 倍 |
| 最大待機時間 | 30 分 |
| デッドレター保持期間 | 30 日 |

---

## 7. 監査とモニタリング

### 7.1 イベント記録仕様

すべての受信 Webhook と内部イベントは `webhook_events` テーブルに記録する。

| カラム | 型 | 説明 |
|--------|-----|------|
| id | UUID | イベント ID |
| event_type | VARCHAR | イベント種別 |
| source | VARCHAR | 送信元（github / internal）|
| payload | JSONB | イベントペイロード |
| status | VARCHAR | pending / processed / failed |
| received_at | TIMESTAMPTZ | 受信日時 |
| processed_at | TIMESTAMPTZ | 処理完了日時 |
| retry_count | INTEGER | 再試行回数 |
| error_message | TEXT | エラーメッセージ（失敗時）|

### 7.2 監視メトリクス

| メトリクス | 説明 | アラート閾値 |
|----------|------|------------|
| webhook_received_total | 受信総数 | - |
| webhook_processing_errors | 処理エラー数 | 5件/分 超過で Warning |
| webhook_processing_latency | 処理時間 | P95 > 5秒で Warning |
| webhook_queue_depth | 再試行キュー深度 | 100件超で Warning |
| dead_letter_queue_size | デッドレター数 | 10件超で Critical |

---

## 8. 関連ドキュメント

| ドキュメント | 参照先 |
|---|---|
| GitHub API 統合仕様 | [GITHUB_API_INTEGRATION.md](./GITHUB_API_INTEGRATION.md) |
| サードパーティ統合ポリシー | [THIRD_PARTY_INTEGRATION_POLICY.md](./THIRD_PARTY_INTEGRATION_POLICY.md) |
| 統合テストモデル | [INTEGRATION_TEST_MODEL.md](../13_testing_quality/INTEGRATION_TEST_MODEL.md) |
| 監査証跡マッピング | [AUDIT_EVIDENCE_MAPPING.md](../15_audit_evidence/AUDIT_EVIDENCE_MAPPING.md) |
| ServiceMatrix 憲章 | [SERVICEMATRIX_CHARTER.md](../00_foundation/SERVICEMATRIX_CHARTER.md) |

---

*本ドキュメントは ServiceMatrix プロジェクトの統治原則に基づき管理される。*
*変更は Change Issue → PR → CI検証 → 承認 のフローに従うこと。*
