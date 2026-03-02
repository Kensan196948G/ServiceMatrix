# トレーサビリティマトリクス

ServiceMatrix Traceability Matrix

Version: 1.0
Status: Active
Classification: Confidential - Audit Document
Last Updated: 2026-03-02

---

## 1. 概要

本ドキュメントは、ServiceMatrix プロジェクトにおける要件・設計・実装・テスト・証跡のトレーサビリティを定義する。
J-SOX IT全般統制の各要件から、実装箇所・テスト証跡・監査証跡までの完全な追跡可能性を提供する。

---

## 2. トレーサビリティの目的

| 目的 | 説明 |
|------|------|
| 規制準拠の証明 | J-SOX・ISO 20000の要件が実装されていることを証明する |
| 影響分析 | 要件変更時の影響範囲を迅速に特定する |
| テスト網羅性確認 | すべての要件がテストされていることを確認する |
| 監査効率化 | 監査人が要件〜証跡を効率的に追跡できるようにする |

---

## 3. 要件〜実装〜テスト〜証跡 トレーサビリティマトリクス

### 3.1 アクセス管理（J-SOX AC統制）

| 統制ID | 要件 | 実装箇所 | テストケース | 証跡テーブル |
|--------|------|---------|------------|------------|
| AC-001 | ユーザーアカウントの適切な管理 | `src/services/auth/user.service.ts` | `tests/unit/auth/user.service.test.ts` | `audit_logs` |
| AC-002 | 権限付与・変更の承認記録 | `src/services/auth/rbac.service.ts` | `tests/unit/auth/rbac.service.test.ts` | `audit_logs` |
| AC-003 | 特権アカウント使用の記録 | `src/middleware/auth.middleware.ts` | `tests/integration/auth/middleware.test.ts` | `audit_logs` |
| AC-004 | ログイン認証の記録 | `src/services/auth/session.service.ts` | `tests/unit/auth/session.service.test.ts` | `auth_logs` |
| AC-005 | セッション管理の制御 | `src/services/auth/session.service.ts` | `tests/integration/auth/session.test.ts` | `session_logs` |
| AC-006 | 職務分離（SoD）の実施 | `src/services/sod/sod.service.ts` | `tests/unit/sod/sod.service.test.ts` | `sod_violations` |
| AC-007 | 定期アクセス権限レビュー | GitHub Issue テンプレート（四半期） | 手動確認 | GitHub Issue |

### 3.2 変更管理（J-SOX CM統制）

| 統制ID | 要件 | 実装箇所 | テストケース | 証跡テーブル |
|--------|------|---------|------------|------------|
| CM-001 | 変更要求の承認プロセス | `src/services/change/change-request.service.ts` | `tests/unit/change/change-request.service.test.ts` | `change_requests` |
| CM-002 | 変更の承認者記録 | `src/services/change/approval.service.ts` | `tests/unit/change/approval.service.test.ts` | `change_approvals` |
| CM-003 | 変更実施の記録 | GitHub Actions CI/CD | CI テストログ | `deployments` |
| CM-004 | 緊急変更の管理 | `src/services/change/emergency-change.service.ts` | `tests/unit/change/emergency-change.service.test.ts` | `emergency_changes` |
| CM-005 | テスト実施の記録 | GitHub Actions CI/CD | GitHub Actions アーティファクト | GitHub |
| CM-006 | ロールバック管理 | `src/services/change/rollback.service.ts` | `tests/unit/change/rollback.service.test.ts` | `rollback_records` |

### 3.3 運用管理（J-SOX OP統制）

| 統制ID | 要件 | 実装箇所 | テストケース | 証跡テーブル |
|--------|------|---------|------------|------------|
| OP-001 | インシデント管理プロセス | `src/services/incident/incident.service.ts` | `tests/unit/incident/incident.service.test.ts` | `incidents` |
| OP-002 | SLA監視 | `src/services/sla/sla-engine.service.ts` | `tests/unit/sla/sla-engine.service.test.ts` | `sla_measurements` |
| OP-003 | バックアップ管理 | バックアップスクリプト | 手動確認 + ログ | バックアップログ |
| OP-004 | キャパシティ管理 | Prometheus / Grafana 監視設定 | 監視設定テスト | Prometheus |

### 3.4 AI統治（SM AI統制）

| 統制ID | 要件 | 実装箇所 | テストケース | 証跡テーブル |
|--------|------|---------|------------|------------|
| AI-001 | AI判断の記録 | `src/services/ai/ai-decision-logger.service.ts` | `tests/unit/ai/ai-decision-logger.service.test.ts` | `ai_decision_logs` |
| AI-002 | 人間承認ゲート | `src/services/ai/approval-gate.service.ts` | `tests/unit/ai/approval-gate.service.test.ts` | `ai_approval_logs` |
| AI-003 | 自律レベル制御 | `src/services/ai/autonomy-controller.service.ts` | `tests/unit/ai/autonomy-controller.service.test.ts` | `ai_config_logs` |
| AI-004 | AIキルスイッチ | `src/services/ai/kill-switch.service.ts` | `tests/unit/ai/kill-switch.service.test.ts` | `ai_emergency_stops` |

---

## 4. テスト種別 × 要件 カバレッジマトリクス

| 要件カテゴリ | ユニットテスト | 統合テスト | E2Eテスト | セキュリティテスト |
|------------|-------------|-----------|---------|----------------|
| アクセス管理（AC） | Yes | Yes | Yes（P1フロー） | Yes |
| 変更管理（CM） | Yes | Yes | Yes（P1フロー） | Yes（SoD検証） |
| 運用管理（OP） | Yes | Yes | 部分的 | 部分的 |
| AI統治（AI） | Yes | Yes | Yes（P1フロー） | Yes |
| 監査ログ（AL） | Yes | Yes | 部分的 | 部分的 |
| SLA管理（SLA） | Yes | Yes | 部分的 | No |

---

## 5. 変更追跡

### 5.1 要件変更トレーサビリティ

要件が変更された場合、以下の全要素への影響を追跡する。

```
要件変更
  |
  v
影響する実装ファイルの特定
  |
  v
影響するテストケースの特定
  |
  v
影響する証跡の特定
  |
  v
Change Issue 作成（影響範囲を明記）
  |
  v
実装・テスト更新
  |
  v
本マトリクスの更新
```

### 5.2 トレーサビリティの維持

| 維持活動 | 頻度 | 担当 |
|---------|------|------|
| マトリクスのレビュー・更新 | リリース毎 | テックリード + QAエンジニア |
| 証跡の完全性確認 | 月次 | 内部監査担当 |
| J-SOX要件との整合確認 | 四半期 | コンプライアンス担当 |
| 新規要件の追加 | 都度 | 要件追加時に担当者 |

---

## 6. 関連ドキュメント

| ドキュメント | 参照先 |
|---|---|
| 監査証跡マッピング | [AUDIT_EVIDENCE_MAPPING.md](./AUDIT_EVIDENCE_MAPPING.md) |
| 証跡収集手順 | [EVIDENCE_COLLECTION_PROCEDURE.md](./EVIDENCE_COLLECTION_PROCEDURE.md) |
| コンプライアンスチェックリスト | [COMPLIANCE_CHECKLIST.md](./COMPLIANCE_CHECKLIST.md) |
| テスト戦略 | [TEST_STRATEGY.md](../13_testing_quality/TEST_STRATEGY.md) |
| 承認制御モデル | [APPROVAL_CONTROL_MODEL.md](../01_governance/APPROVAL_CONTROL_MODEL.md) |

---

*本ドキュメントは ServiceMatrix プロジェクトの統治原則に基づき管理される。*
*変更は Change Issue → PR → CI検証 → 承認 のフローに従うこと。*
