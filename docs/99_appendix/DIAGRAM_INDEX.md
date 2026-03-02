# 図表インデックス

ServiceMatrix Diagram Index

Version: 1.0
Status: Active
Classification: Internal Reference Document
Last Updated: 2026-03-02

---

## 1. 概要

本ドキュメントは、ServiceMatrix プロジェクトで使用されるすべての図表・
ダイアグラムのインデックスを提供する。
図表の種別・所在・説明を一元管理し、参照性を高める。

---

## 2. アーキテクチャ図

### 2.1 システム全体アーキテクチャ

| 図表名 | 所在ドキュメント | セクション | 図表種別 |
|--------|---------------|---------|---------|
| システム全体アーキテクチャ概観 | ARCHITECTURE_OVERVIEW.md | §2 | ブロック図 |
| レイヤードアーキテクチャ | ARCHITECTURE_OVERVIEW.md | §3 | レイヤー図 |
| マイクロサービス構成 | MICROSERVICES_DESIGN.md | §2 | コンポーネント図 |
| API Gateway 設計 | API_GATEWAY_DESIGN.md | §3 | フロー図 |
| データフロー概観 | ARCHITECTURE_OVERVIEW.md | §4 | データフロー図 |

### 2.2 データベースアーキテクチャ

| 図表名 | 所在ドキュメント | セクション | 図表種別 |
|--------|---------------|---------|---------|
| ERD（エンティティ関係図）| DATABASE_SCHEMA.md | §3 | ER 図 |
| CMDB 関係モデル | RELATIONSHIP_MODEL.md | §2 | グラフ図 |
| インデックス戦略 | DATABASE_SCHEMA.md | §6 | テーブル図 |

### 2.3 インフラアーキテクチャ

| 図表名 | 所在ドキュメント | セクション | 図表種別 |
|--------|---------------|---------|---------|
| Kubernetes クラスター構成 | INFRASTRUCTURE_DESIGN.md | §2 | インフラ図 |
| ネットワーク設計 | NETWORK_DESIGN.md | §3 | ネットワーク図 |
| 高可用性構成 | HA_DESIGN.md | §2 | 構成図 |
| CI/CD パイプライン | CI_CD_PIPELINE_ARCHITECTURE.md | §2 | パイプライン図 |

---

## 3. プロセス・フロー図

### 3.1 ITSM プロセスフロー

| 図表名 | 所在ドキュメント | セクション | 図表種別 |
|--------|---------------|---------|---------|
| インシデント管理フロー | INCIDENT_MANAGEMENT_PROCESS.md | §3 | フローチャート |
| インシデント状態遷移 | INCIDENT_MANAGEMENT_PROCESS.md | §4 | 状態遷移図 |
| 変更管理フロー | CHANGE_MANAGEMENT_PROCESS.md | §3 | フローチャート |
| 変更承認フロー | CHANGE_MANAGEMENT_PROCESS.md | §5 | フローチャート |
| 問題管理フロー | PROBLEM_MANAGEMENT_PROCESS.md | §3 | フローチャート |
| サービス要求フロー | REQUEST_MANAGEMENT_PROCESS.md | §3 | フローチャート |
| SLA 計測フロー | SLA_DEFINITION.md | §4 | フローチャート |

### 3.2 変更管理フロー

| 図表名 | 所在ドキュメント | セクション | 図表種別 |
|--------|---------------|---------|---------|
| Issue 駆動開発ワークフロー | ISSUE_WORKFLOW_DEFINITION.md | §2 | フローチャート |
| ブランチ戦略 | BRANCH_STRATEGY.md | §3 | ブランチ図 |
| PR ガバナンスフロー | PULL_REQUEST_POLICY.md | §4 | フローチャート |
| デプロイフロー | DEPLOYMENT_POLICY.md | §4 | フローチャート |
| ロールバックフロー | ROLLBACK_STRATEGY.md | §3 | フローチャート |

### 3.3 AI ガバナンスフロー

| 図表名 | 所在ドキュメント | セクション | 図表種別 |
|--------|---------------|---------|---------|
| AI 提案・承認フロー | AI_GOVERNANCE_POLICY.md | §4 | フローチャート |
| AI 自律レベル遷移 | AI_GOVERNANCE_POLICY.md | §3 | 状態遷移図 |
| 緊急停止フロー | AI_GOVERNANCE_POLICY.md | §7 | フローチャート |
| AI 意思決定ログ構造 | AI_DECISION_LOGGING_MODEL.md | §3 | 構造図 |

---

## 4. データモデル図

### 4.1 ドメインモデル

| 図表名 | 所在ドキュメント | セクション | 図表種別 |
|--------|---------------|---------|---------|
| インシデントドメインモデル | DATA_MODEL_OVERVIEW.md | §3 | クラス図 |
| 変更管理ドメインモデル | DATA_MODEL_OVERVIEW.md | §4 | クラス図 |
| CMDB ドメインモデル | CMDB_DATA_MODEL.md | §2 | クラス図 |
| SLA ドメインモデル | SLA_DEFINITION.md | §3 | クラス図 |

### 4.2 API データモデル

| 図表名 | 所在ドキュメント | セクション | 図表種別 |
|--------|---------------|---------|---------|
| インシデント API スキーマ | INCIDENT_API_SPEC.md | §3 | スキーマ図 |
| 変更要求 API スキーマ | CHANGE_API_SPEC.md | §3 | スキーマ図 |
| CMDB API スキーマ | CMDB_API_SPEC.md | §3 | スキーマ図 |

---

## 5. セキュリティ図

| 図表名 | 所在ドキュメント | セクション | 図表種別 |
|--------|---------------|---------|---------|
| 認証・認可フロー | AUTH_DESIGN.md | §3 | フローチャート |
| RBAC ロール階層 | ROLE_PERMISSION_MATRIX.md | §2 | 階層図 |
| 脅威モデル（STRIDE）| THREAT_MODEL.md | §3 | 脅威分析図 |
| セキュリティレイヤー | SECURITY_POLICY.md | §2 | レイヤー図 |
| ゼロトラストアーキテクチャ | SECURITY_POLICY.md | §4 | アーキテクチャ図 |

---

## 6. テスト・品質図

| 図表名 | 所在ドキュメント | セクション | 図表種別 |
|--------|---------------|---------|---------|
| テストピラミッド | TEST_STRATEGY.md | §3 | ピラミッド図 |
| テスト環境構成 | INTEGRATION_TEST_MODEL.md | §3 | 構成図 |
| CI/CD 品質ゲート | QUALITY_GATE_DEFINITION.md | §2 | パイプライン図 |
| カバレッジマップ | UNIT_TEST_POLICY.md | §4 | ヒートマップ |

---

## 7. 監査・コンプライアンス図

| 図表名 | 所在ドキュメント | セクション | 図表種別 |
|--------|---------------|---------|---------|
| J-SOX 統制マッピング | AUDIT_EVIDENCE_MAPPING.md | §3 | マッピング図 |
| 証跡収集フロー | EVIDENCE_COLLECTION_PROCEDURE.md | §3 | フローチャート |
| トレーサビリティマトリクス | TRACEABILITY_MATRIX.md | §3 | マトリクス図 |
| ハッシュチェーン構造 | AUDIT_EVIDENCE_MAPPING.md | §5 | 構造図 |

---

## 8. 統合図

| 図表名 | 所在ドキュメント | セクション | 図表種別 |
|--------|---------------|---------|---------|
| Webhook アーキテクチャ | WEBHOOK_EVENT_MODEL.md | §2 | アーキテクチャ図 |
| GitHub 統合フロー | GITHUB_API_INTEGRATION.md | §3 | フロー図 |
| 通知配信フロー | GITHUB_API_INTEGRATION.md | §5 | シーケンス図 |
| 統合ロードマップ | FUTURE_INTEGRATION_ROADMAP.md | §2 | タイムライン図 |

---

## 9. UI/UX 図

| 図表名 | 所在ドキュメント | セクション | 図表種別 |
|--------|---------------|---------|---------|
| ダッシュボードレイアウト | DASHBOARD_DESIGN.md | §2 | ワイヤーフレーム |
| ロールベースビューマトリクス | ROLE_BASED_VIEW_MATRIX.md | §2 | マトリクス図 |
| ナビゲーション構造 | NAVIGATION_DESIGN.md | §3 | サイトマップ |
| コンポーネント設計 | COMPONENT_DESIGN.md | §2 | コンポーネント図 |

---

## 10. 図表作成ガイドライン

### 10.1 図表ツール標準

| 図表種別 | 推奨ツール | 形式 |
|---------|----------|------|
| アーキテクチャ図 | draw.io / Mermaid | PNG + 編集可能ソース |
| フローチャート | Mermaid（Markdown 内）| テキスト形式 |
| ER 図 | dbdiagram.io / Mermaid | PNG + DDL |
| ネットワーク図 | draw.io | PNG + XML |
| シーケンス図 | Mermaid（Markdown 内）| テキスト形式 |

### 10.2 図表命名規則

```
命名規則:
  {カテゴリ}_{ドキュメント名}_{連番}.{拡張子}

例:
  arch_system_overview_001.png
  flow_incident_state_transition_001.mmd
  erd_cmdb_relationships_001.png
```

### 10.3 図表更新管理

| ルール | 内容 |
|--------|------|
| バージョン管理 | 図表ソースファイルを Git で管理 |
| 更新時の対応 | 図表更新時は本インデックスも同時更新 |
| レビュー | 図表変更も PR レビューの対象 |
| 整合性確認 | ドキュメント更新時は関連図表との整合性を確認 |

---

## 11. 関連ドキュメント

| ドキュメント | 参照先 |
|---|---|
| 用語集 | [GLOSSARY.md](./GLOSSARY.md) |
| 改訂履歴 | [REVISION_HISTORY.md](./REVISION_HISTORY.md) |
| ServiceMatrix 憲章 | [SERVICEMATRIX_CHARTER.md](../00_foundation/SERVICEMATRIX_CHARTER.md) |

---

*本ドキュメントは ServiceMatrix プロジェクトの統治原則に基づき管理される。*
*変更は Change Issue → PR → CI検証 → 承認 のフローに従うこと。*
