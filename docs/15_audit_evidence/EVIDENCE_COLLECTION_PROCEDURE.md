# 証跡収集手順

ServiceMatrix Evidence Collection Procedure

Version: 1.0
Status: Active
Classification: Confidential - Audit Document
Last Updated: 2026-03-02

---

## 1. 概要

本ドキュメントは、ServiceMatrix プロジェクトにおける監査証跡の収集・保管・提出手順を定義する。
J-SOX監査・ISO 20000認証審査・内部監査において必要な証跡を、
効率的かつ完全に収集するための標準手順を規定する。

---

## 2. 証跡収集の基本方針

### 2.1 自動収集優先

| 原則 | 説明 |
|------|------|
| 自動収集優先 | 証跡はシステムが自動的に記録・収集する |
| リアルタイム記録 | 操作発生と同時に証跡を記録する |
| 改竄防止 | 収集した証跡は変更・削除不可とする |
| 完全性確保 | すべての対象操作を漏れなく記録する |
| 検索可能性 | 収集した証跡はキーワード・期間で検索可能とする |

### 2.2 証跡収集フロー

```
[システム操作発生]
  |
  v
[自動ログ記録]
  +-- 監査ログAPI呼び出し
  +-- タイムスタンプ付与（UTC）
  +-- 操作者情報記録
  +-- 操作内容のシリアライズ
  |
  v
[DB保存（audit_logs テーブル）]
  |
  v
[ハッシュチェーン付与]
  |
  v
[バックアップレプリカ同期]
  |
  v
[インデックス更新（検索用）]
```

---

## 3. 証跡収集対象と収集方法

### 3.1 アクセス管理証跡の収集

| 操作 | 自動収集 | 収集データ |
|------|---------|-----------|
| ログイン（成功） | Yes | user_id, ip_address, timestamp, session_id |
| ログイン（失敗） | Yes | attempted_user, ip_address, timestamp, failure_reason |
| ログアウト | Yes | user_id, session_id, timestamp |
| パスワード変更 | Yes | user_id, timestamp, changed_by |
| ロール付与 | Yes | user_id, role, granted_by, timestamp |
| ロール剥奪 | Yes | user_id, role, revoked_by, timestamp |
| セッションタイムアウト | Yes | user_id, session_id, timestamp |

### 3.2 変更管理証跡の収集

| 操作 | 自動収集 | 収集データ |
|------|---------|-----------|
| RFC作成 | Yes | rfc_id, requester, created_at, risk_level, change_type |
| RFC承認 | Yes | rfc_id, approver, approved_at, approval_note |
| RFC却下 | Yes | rfc_id, rejector, rejected_at, rejection_reason |
| デプロイ実行 | Yes | deploy_id, rfc_id, deployer, started_at, completed_at, version |
| ロールバック実行 | Yes | rollback_id, rfc_id, executor, started_at, reason |
| PR作成 | Yes | pr_id, author, rfc_id, created_at |
| PRマージ | Yes | pr_id, merger, merged_at, approvers |

### 3.3 データ操作証跡の収集

| 操作 | 自動収集 | 収集データ |
|------|---------|-----------|
| レコード作成（全エンティティ） | Yes | entity_type, entity_id, actor, created_at, data_snapshot |
| レコード更新（全エンティティ） | Yes | entity_type, entity_id, actor, updated_at, before_snapshot, after_snapshot |
| レコード削除（全エンティティ） | Yes | entity_type, entity_id, actor, deleted_at, data_snapshot |
| 一括操作 | Yes | operation_type, affected_count, actor, timestamp, batch_id |

### 3.4 AI操作証跡の収集

| 操作 | 自動収集 | 収集データ |
|------|---------|-----------|
| AI提案生成 | Yes | decision_id, model, input_context, output_suggestion, confidence, timestamp |
| 人間承認 | Yes | decision_id, approver, approved_at, approval_note |
| 人間却下 | Yes | decision_id, rejector, rejected_at, rejection_reason |
| AI自律実行 | Yes | decision_id, action_type, result, timestamp |
| AIキルスイッチ | Yes | executor, reason, stopped_at, affected_scope |

---

## 4. 監査証跡のデータ構造

### 4.1 標準監査ログフォーマット

```
{
  "log_id": "UUID",
  "timestamp": "2026-03-02T07:00:00.000Z",  // UTC ISO 8601
  "sequence_number": 1234567,                 // 連番（改竄検出用）
  "event_type": "ACCESS_GRANTED",            // イベント種別
  "actor": {
    "user_id": "UUID",
    "username": "user@example.com",
    "ip_address": "xxx.xxx.xxx.xxx",
    "session_id": "UUID",
    "role": ["ChangeManager"]
  },
  "resource": {
    "type": "ChangeRequest",
    "id": "RFC-2026-001",
    "name": "インフラアップグレード"
  },
  "action": {
    "type": "APPROVE",
    "description": "変更要求を承認した",
    "result": "SUCCESS"
  },
  "context": {
    "request_id": "UUID",
    "api_endpoint": "/api/v1/change-requests/{id}/approve",
    "http_method": "POST"
  },
  "metadata": {
    "previous_hash": "SHA256ハッシュ値",
    "current_hash": "SHA256ハッシュ値"
  }
}
```

---

## 5. 証跡抽出手順

### 5.1 定期証跡レポート（自動）

| レポート | 頻度 | 内容 | 配信先 |
|---------|------|------|--------|
| アクセスログレポート | 月次 | アカウント変更・権限変更一覧 | 内部監査担当 |
| 変更管理レポート | 月次 | RFC・承認・デプロイ一覧 | Change Manager |
| セキュリティイベントレポート | 週次 | 異常ログイン・権限昇格試行 | セキュリティチーム |
| AI活動レポート | 月次 | AI提案・承認・実行一覧 | AI Governance 担当 |
| SLA準拠レポート | 月次 | SLA達成率・違反一覧 | Service Manager |

### 5.2 J-SOX監査時の証跡提出手順

```
[ステップ1] 監査対象期間の確定
  内容: 監査人と対象期間（開始日〜終了日）を確認

[ステップ2] 証跡収集コマンドの実行
  対象システム: ServiceMatrix 管理画面 / 監査API
  実行者: システム管理者（Auditorロール）
  コマンド例:
    GET /api/v1/audit/export?from=2026-01-01&to=2026-03-31&type=all
    → JSON / CSV形式でダウンロード

[ステップ3] 証跡の完全性検証
  実行: ハッシュチェーンの整合性チェック
  コマンド:
    GET /api/v1/audit/verify?from=2026-01-01&to=2026-03-31
  結果: 検証レポートをダウンロード

[ステップ4] 証跡ファイルの整形
  形式: CSV / PDF / Excel（監査人の指定に従う）
  暗号化: AES-256 で暗号化してパスワードを別経路で送付

[ステップ5] 証跡の提出
  方法: セキュアなファイル転送（SFTP / 暗号化メール）
  記録: 提出日時・提出先・ファイルハッシュを記録

[ステップ6] 提出記録の保管
  保管場所: DB: evidence_submissions テーブル
  保管期間: 7年
```

### 5.3 Ad-hoc 証跡抽出（内部調査時）

内部調査・インシデント対応等でAd-hocな証跡抽出が必要な場合。

| 手順 | 内容 |
|------|------|
| 申請 | Admin または Auditor が抽出目的・対象・期間を申請 |
| 承認 | Admin が承認（Auditorの場合は相互承認） |
| 実行 | 承認記録とともに抽出を実行 |
| 記録 | 抽出操作自体も監査ログに記録 |
| 保管 | 抽出ファイルと申請・承認記録を紐付けて保管 |

---

## 6. 証跡保全手順

### 6.1 バックアップ

| 項目 | 内容 |
|------|------|
| バックアップ頻度 | 日次（増分） + 週次（フル） |
| 保存場所 | プライマリ + 別リージョンのセカンダリ |
| 暗号化 | AES-256 |
| 保持期間 | 7年 |
| 復元テスト | 四半期に1回、復元テストを実施 |

### 6.2 完全性検証

| 検証種別 | 頻度 | 方法 |
|---------|------|------|
| ハッシュチェーン検証 | 日次（自動） | 全レコードのハッシュチェーン整合性確認 |
| レコード件数検証 | 日次（自動） | 前日比でのレコード件数の増分確認 |
| バックアップ整合性検証 | 週次（自動） | バックアップファイルのハッシュ確認 |
| 復元テスト | 四半期（手動） | バックアップからの実際の復元確認 |

---

## 7. 関連ドキュメント

| ドキュメント | 参照先 |
|---|---|
| 監査証跡マッピング | [AUDIT_EVIDENCE_MAPPING.md](./AUDIT_EVIDENCE_MAPPING.md) |
| トレーサビリティマトリクス | [TRACEABILITY_MATRIX.md](./TRACEABILITY_MATRIX.md) |
| コンプライアンスチェックリスト | [COMPLIANCE_CHECKLIST.md](./COMPLIANCE_CHECKLIST.md) |
| AI意思決定ログモデル | [AI_DECISION_LOGGING_MODEL.md](../04_agents_ai/AI_DECISION_LOGGING_MODEL.md) |

---

*本ドキュメントは ServiceMatrix プロジェクトの統治原則に基づき管理される。*
*変更は Change Issue → PR → CI検証 → 承認 のフローに従うこと。*
