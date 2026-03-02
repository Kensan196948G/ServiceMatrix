# 改訂履歴

ServiceMatrix Revision History

Version: 1.0
Status: Active
Classification: Internal Governance Document
Last Updated: 2026-03-02

---

## 1. 概要

本ドキュメントは、ServiceMatrix プロジェクトのドキュメント体系全体における
主要な改訂の履歴を記録する。
設計上の重要な決定・変更の変遷を追跡し、ガバナンスの透明性を確保する。

---

## 2. ドキュメント全体の改訂履歴

### 2.1 フェーズ別改訂記録

| バージョン | 日付 | フェーズ | 主要変更内容 | 承認者 |
|----------|------|---------|------------|--------|
| 1.0.0 | 2026-03-02 | Phase 0 | ServiceMatrix 初版ドキュメント体系確立 | プロジェクトリード |

---

## 3. Phase 0: 初期化フェーズ（2026-03-02）

### 3.1 作成ドキュメント一覧

#### 00_foundation（基盤・統治）

| ドキュメント | バージョン | 変更種別 | 説明 |
|------------|---------|---------|------|
| SERVICEMATRIX_CHARTER.md | 1.0 | 新規作成 | プロジェクト憲章 |
| GOVERNANCE_MODEL.md | 1.0 | 新規作成 | ガバナンスモデル |
| RACI_MATRIX.md | 1.0 | 新規作成 | RACI マトリクス |
| TERMINOLOGY_DEFINITIONS.md | 1.0 | 新規作成 | 用語定義 |
| DECISION_FRAMEWORK.md | 1.0 | 新規作成 | 意思決定フレームワーク |

#### 01_governance（統制・承認）

| ドキュメント | バージョン | 変更種別 | 説明 |
|------------|---------|---------|------|
| APPROVAL_CONTROL_MODEL.md | 1.0 | 新規作成 | 承認制御モデル |
| ROLE_PERMISSION_MATRIX.md | 1.0 | 新規作成 | ロール権限マトリクス |
| ESCALATION_POLICY.md | 1.0 | 新規作成 | エスカレーションポリシー |

#### 02_architecture（アーキテクチャ）

| ドキュメント | バージョン | 変更種別 | 説明 |
|------------|---------|---------|------|
| ARCHITECTURE_OVERVIEW.md | 1.0 | 新規作成 | アーキテクチャ概観 |
| DATABASE_SCHEMA.md | 1.0 | 新規作成 | データベーススキーマ |
| API_DESIGN_PRINCIPLES.md | 1.0 | 新規作成 | API 設計原則 |

#### 03_itsm_processes（ITSM プロセス）

| ドキュメント | バージョン | 変更種別 | 説明 |
|------------|---------|---------|------|
| INCIDENT_MANAGEMENT_PROCESS.md | 1.0 | 新規作成 | インシデント管理プロセス |
| CHANGE_MANAGEMENT_PROCESS.md | 1.0 | 新規作成 | 変更管理プロセス |
| PROBLEM_MANAGEMENT_PROCESS.md | 1.0 | 新規作成 | 問題管理プロセス |
| REQUEST_MANAGEMENT_PROCESS.md | 1.0 | 新規作成 | サービス要求管理プロセス |

#### 04_agents_ai（AI エージェント）

| ドキュメント | バージョン | 変更種別 | 説明 |
|------------|---------|---------|------|
| AI_GOVERNANCE_POLICY.md | 1.0 | 新規作成 | AI ガバナンスポリシー |
| AGENT_DESIGN_MODEL.md | 1.0 | 新規作成 | エージェント設計モデル |
| AI_DECISION_LOGGING_MODEL.md | 2.0 | 新規作成（拡張版） | AI 意思決定ログモデル |
| HUMAN_APPROVAL_GATE_SPEC.md | 1.0 | 新規作成 | 人間承認ゲート仕様 |

#### 05_devops（DevOps）

| ドキュメント | バージョン | 変更種別 | 説明 |
|------------|---------|---------|------|
| ISSUE_WORKFLOW_DEFINITION.md | 1.0 | 新規作成 | Issue ワークフロー定義 |
| BRANCH_STRATEGY.md | 1.0 | 新規作成 | ブランチ戦略 |
| PULL_REQUEST_POLICY.md | 1.0 | 新規作成 | PR ポリシー |
| CI_CD_PIPELINE_ARCHITECTURE.md | 1.0 | 新規作成 | CI/CD パイプラインアーキテクチャ |

#### 06_operations（運用管理）

| ドキュメント | バージョン | 変更種別 | 説明 |
|------------|---------|---------|------|
| RUNBOOK_TEMPLATE.md | 1.0 | 新規作成 | ランブックテンプレート |
| MONITORING_ALERT_MODEL.md | 1.0 | 新規作成 | 監視・アラートモデル |
| ON_CALL_POLICY.md | 1.0 | 新規作成 | オンコールポリシー |

#### 07_sla_metrics（SLA・メトリクス）

| ドキュメント | バージョン | 変更種別 | 説明 |
|------------|---------|---------|------|
| SLA_DEFINITION.md | 1.0 | 新規作成 | SLA 定義 |
| KPI_METRICS_MODEL.md | 1.0 | 新規作成 | KPI メトリクスモデル |

#### 08_data_model（データモデル）

| ドキュメント | バージョン | 変更種別 | 説明 |
|------------|---------|---------|------|
| DATA_MODEL_OVERVIEW.md | 1.0 | 新規作成 | データモデル概観 |
| ENTITY_RELATIONSHIP_SPEC.md | 1.0 | 新規作成 | エンティティ関係仕様 |
| DATA_MIGRATION_POLICY.md | 1.0 | 新規作成 | データ移行ポリシー |

#### 09_ui_ux（UI/UX）

| ドキュメント | バージョン | 変更種別 | 説明 |
|------------|---------|---------|------|
| DASHBOARD_DESIGN.md | 1.0 | 新規作成 | ダッシュボード設計 |
| ROLE_BASED_VIEW_MATRIX.md | 1.0 | 新規作成 | ロールベースビューマトリクス |

#### 10_cmdb（CMDB）

| ドキュメント | バージョン | 変更種別 | 説明 |
|------------|---------|---------|------|
| CMDB_DATA_MODEL.md | 1.0 | 新規作成 | CMDB データモデル |
| RELATIONSHIP_MODEL.md | 1.0 | 新規作成 | CI 関係モデル |
| CI_TYPE_DEFINITION.md | 1.0 | 新規作成 | CI 種別定義 |

#### 11_security_compliance（セキュリティ・コンプライアンス）

| ドキュメント | バージョン | 変更種別 | 説明 |
|------------|---------|---------|------|
| SECURITY_POLICY.md | 1.0 | 新規作成 | セキュリティポリシー |
| COMPLIANCE_FRAMEWORK.md | 1.0 | 新規作成 | コンプライアンスフレームワーク |
| JSOX_CONTROL_MAPPING.md | 1.0 | 新規作成 | J-SOX 統制マッピング |

#### 12_risk_management（リスク管理）

| ドキュメント | バージョン | 変更種別 | 説明 |
|------------|---------|---------|------|
| RISK_ASSESSMENT_MODEL.md | 1.0 | 新規作成 | リスク評価モデル |
| RISK_SCORING_LOGIC.md | 1.0 | 新規作成 | リスクスコアリングロジック |
| CHANGE_RISK_MATRIX.md | 1.0 | 新規作成 | 変更リスクマトリクス |
| THREAT_MODEL.md | 1.0 | 新規作成 | 脅威モデル |

#### 13_testing_quality（テスト・品質）

| ドキュメント | バージョン | 変更種別 | 説明 |
|------------|---------|---------|------|
| TEST_STRATEGY.md | 1.0 | 新規作成 | テスト戦略 |
| UNIT_TEST_POLICY.md | 1.0 | 新規作成 | ユニットテストポリシー |
| INTEGRATION_TEST_MODEL.md | 1.0 | 新規作成 | 統合テストモデル |
| SECURITY_TEST_POLICY.md | 1.0 | 新規作成 | セキュリティテストポリシー |
| PERFORMANCE_TEST_MODEL.md | 1.0 | 新規作成 | パフォーマンステストモデル |
| QUALITY_GATE_DEFINITION.md | 1.0 | 新規作成 | 品質ゲート定義 |

#### 14_release_management（リリース管理）

| ドキュメント | バージョン | 変更種別 | 説明 |
|------------|---------|---------|------|
| RELEASE_STRATEGY.md | 1.0 | 新規作成 | リリース戦略 |
| VERSIONING_MODEL.md | 1.0 | 新規作成 | バージョニングモデル |
| DEPLOYMENT_POLICY.md | 1.0 | 新規作成 | デプロイポリシー |
| ROLLBACK_STRATEGY.md | 1.0 | 新規作成 | ロールバック戦略 |

#### 15_audit_evidence（監査証跡）

| ドキュメント | バージョン | 変更種別 | 説明 |
|------------|---------|---------|------|
| AUDIT_EVIDENCE_MAPPING.md | 1.0 | 新規作成 | 監査証跡マッピング |
| COMPLIANCE_CHECKLIST.md | 1.0 | 新規作成 | コンプライアンスチェックリスト |
| EVIDENCE_COLLECTION_PROCEDURE.md | 1.0 | 新規作成 | 証跡収集手順 |
| TRACEABILITY_MATRIX.md | 1.0 | 新規作成 | トレーサビリティマトリクス |

#### 16_external_integration（外部連携）

| ドキュメント | バージョン | 変更種別 | 説明 |
|------------|---------|---------|------|
| GITHUB_API_INTEGRATION.md | 1.0 | 新規作成 | GitHub API 統合仕様 |
| THIRD_PARTY_INTEGRATION_POLICY.md | 1.0 | 新規作成 | サードパーティ統合ポリシー |
| WEBHOOK_EVENT_MODEL.md | 1.0 | 新規作成 | Webhook イベントモデル |
| FUTURE_INTEGRATION_ROADMAP.md | 1.0 | 新規作成 | 将来統合ロードマップ |

#### 99_appendix（付録）

| ドキュメント | バージョン | 変更種別 | 説明 |
|------------|---------|---------|------|
| GLOSSARY.md | 1.0 | 新規作成 | 用語集 |
| DIAGRAM_INDEX.md | 1.0 | 新規作成 | 図表インデックス |
| REVISION_HISTORY.md | 1.0 | 新規作成 | 改訂履歴（本ドキュメント）|
| DECISION_LOG.md | 1.0 | 新規作成 | 決定事項ログ |
| OPEN_QUESTIONS.md | 1.0 | 新規作成 | オープン課題一覧 |

---

## 4. 改訂管理規則

### 4.1 バージョニング規則

| 変更種別 | バージョン変更 | 例 |
|---------|-------------|-----|
| 内容の大幅な変更・構造変更 | MAJOR (+1.0.0) | 1.0 → 2.0 |
| 新セクション追加・重要内容追記 | MINOR (+0.1.0) | 1.0 → 1.1 |
| 誤字脱字修正・軽微な表現変更 | PATCH (+0.0.1) | 1.0 → 1.0.1 |

### 4.2 改訂記録の必須事項

ドキュメントを改訂する際、以下の情報を必ず記録する。

| 項目 | 説明 |
|------|------|
| 改訂日 | ISO 8601 形式（YYYY-MM-DD）|
| 改訂者 | GitHub ログイン名 |
| 変更内容 | 変更の概要（1-3 行）|
| 関連 Issue/PR | GitHub Issue/PR 番号 |
| 承認者 | レビュー承認者の GitHub ログイン名 |

### 4.3 改訂フロー

```
改訂フロー:
  1. Change Issue 作成（変更内容・理由を記載）
  2. feature ブランチ作成
  3. ドキュメント変更 + ヘッダーの Last Updated 更新
  4. REVISION_HISTORY.md への記録
  5. PR 作成・レビュー依頼
  6. CI チェック通過
  7. 承認後マージ
```

---

## 5. 関連ドキュメント

| ドキュメント | 参照先 |
|---|---|
| 決定事項ログ | [DECISION_LOG.md](./DECISION_LOG.md) |
| オープン課題 | [OPEN_QUESTIONS.md](./OPEN_QUESTIONS.md) |
| 用語集 | [GLOSSARY.md](./GLOSSARY.md) |
| ServiceMatrix 憲章 | [SERVICEMATRIX_CHARTER.md](../00_foundation/SERVICEMATRIX_CHARTER.md) |

---

*本ドキュメントは ServiceMatrix プロジェクトの統治原則に基づき管理される。*
*変更は Change Issue → PR → CI検証 → 承認 のフローに従うこと。*
