# 用語集

ServiceMatrix Glossary

Version: 1.0
Status: Active
Classification: Internal Reference Document
Last Updated: 2026-03-02

---

## 1. 概要

本ドキュメントは、ServiceMatrix プロジェクトで使用される用語・略語・概念を
五十音順および英字順に整理した用語集である。
ドキュメント間で用語の解釈が統一されるよう、本用語集を参照すること。

---

## 2. 日本語用語（五十音順）

### あ行

| 用語 | 英語 | 定義 |
|------|------|------|
| 影響分析 | Impact Analysis | 変更または障害がシステム・サービス・ユーザーに与える影響の評価 |
| インシデント | Incident | サービス品質の低下または中断を引き起こすイベント（ITIL 定義）|
| インシデント管理 | Incident Management | インシデントを可能な限り迅速に解決するための ITIL プロセス |
| エスカレーション | Escalation | 対応能力・権限が不足した場合に上位担当者や組織に問題を移管すること |
| オンコール | On-Call | 業務時間外に緊急対応のため待機すること |

### か行

| 用語 | 英語 | 定義 |
|------|------|------|
| 監査証跡 | Audit Trail | 操作の記録。誰が・いつ・何を・どのように変更したかの完全な記録 |
| 監査ログ | Audit Log | 監査証跡として保存されたログデータ |
| 緊急変更 | Emergency Change | 深刻な影響を防ぐために即座に実施する必要がある変更 |
| 既知エラー | Known Error | 診断が完了し、根本原因が特定済みの問題 |
| 構成アイテム | Configuration Item (CI) | CMDB で管理される IT インフラの構成要素 |
| 構成管理データベース | Configuration Management Database (CMDB) | IT インフラの構成アイテムとその関係を管理するデータベース |

### さ行

| 用語 | 英語 | 定義 |
|------|------|------|
| サービス要求 | Service Request | ユーザーからの標準的なサービス提供依頼 |
| 職務分離 | Segregation of Duties (SoD) | 同一人物が相互チェックが必要な複数の職務を担わないようにする統制 |
| 承認フロー | Approval Flow | 変更・提案などを承認するための一連のワークフロー |
| 状態遷移 | State Transition | エンティティのステータスが変化すること。許可された遷移のみが有効 |

### た行

| 用語 | 英語 | 定義 |
|------|------|------|
| 問題管理 | Problem Management | 一つ以上のインシデントの根本原因を特定・解決する ITIL プロセス |
| 変更管理 | Change Management | 標準化された方法で変更を管理する ITIL プロセス |
| 変更諮問委員会 | Change Advisory Board (CAB) | 変更要求を評価・承認する委員会 |

### な行

| 用語 | 英語 | 定義 |
|------|------|------|
| ナレッジ管理 | Knowledge Management | 情報・知識の作成・共有・利用・管理の ITIL プロセス |

### は行

| 用語 | 英語 | 定義 |
|------|------|------|
| バックログ | Backlog | 優先度付きの未対応タスク一覧 |
| ハッシュチェーン | Hash Chain | 各レコードが前のレコードのハッシュを含む構造。改竄検知に使用 |
| 平均修復時間 | Mean Time to Repair (MTTR) | 障害発生から復旧完了までの平均時間 |
| 平均故障間隔 | Mean Time Between Failures (MTBF) | 障害から次の障害までの平均時間 |
| ポストモーテム | Postmortem | インシデント後の振り返り分析。根本原因と再発防止策を特定する |

### ら行

| 用語 | 英語 | 定義 |
|------|------|------|
| リスク評価 | Risk Assessment | 変更・イベントのリスクを評価するプロセス |
| ロールバック | Rollback | 変更を以前の状態に戻す操作 |

---

## 3. 英字用語（A-Z）

### A

| 略語/用語 | 正式名称 | 定義 |
|---------|---------|------|
| AC | Access Control | アクセス管理。J-SOX IT 全般統制の一区分 |
| ACL | Access Control List | アクセス制御リスト。リソースへのアクセス権を定義する |
| AI | Artificial Intelligence | 人工知能 |
| APM | Application Performance Monitoring | アプリケーションパフォーマンス監視 |
| API | Application Programming Interface | ソフトウェア間の通信インタフェース |

### B

| 略語/用語 | 正式名称 | 定義 |
|---------|---------|------|
| BREAKING CHANGE | - | 後方互換性を壊す変更。SemVer のメジャーバージョンアップを伴う |

### C

| 略語/用語 | 正式名称 | 定義 |
|---------|---------|------|
| CAB | Change Advisory Board | 変更諮問委員会 |
| CD | Continuous Delivery / Deployment | 継続的デリバリー / デプロイ |
| CI | Configuration Item / Continuous Integration | 構成アイテム / 継続的インテグレーション（文脈依存）|
| CMDB | Configuration Management Database | 構成管理データベース |
| CM | Change Management | 変更管理。J-SOX IT 全般統制の一区分 |

### D

| 略語/用語 | 正式名称 | 定義 |
|---------|---------|------|
| DAST | Dynamic Application Security Testing | 動的アプリケーションセキュリティテスト |
| DevOps | Development + Operations | 開発と運用の統合プラクティス |
| DR | Disaster Recovery | 災害復旧計画 |

### G

| 略語/用語 | 正式名称 | 定義 |
|---------|---------|------|
| GitOps | Git + Operations | Git をシステム状態の信頼できる情報源とした運用モデル |

### I

| 略語/用語 | 正式名称 | 定義 |
|---------|---------|------|
| IdP | Identity Provider | アイデンティティプロバイダ。認証情報を管理・提供するサービス |
| ITIL | IT Infrastructure Library | IT サービス管理のベストプラクティス集 |
| ITSM | IT Service Management | IT サービス管理 |

### J

| 略語/用語 | 正式名称 | 定義 |
|---------|---------|------|
| J-SOX | 日本版 Sarbanes-Oxley Act | 金融商品取引法に基づく内部統制報告制度（IT 全般統制を含む）|
| JWT | JSON Web Token | JSON ベースのアクセストークン標準 |

### L

| 略語/用語 | 正式名称 | 定義 |
|---------|---------|------|
| LLM | Large Language Model | 大規模言語モデル。Claude 等の AI モデル |
| LCP | Largest Contentful Paint | Web Vitals 指標。最大コンテンツの表示時間 |

### M

| 略語/用語 | 正式名称 | 定義 |
|---------|---------|------|
| MTTR | Mean Time to Repair | 平均修復時間 |
| MTBF | Mean Time Between Failures | 平均故障間隔 |
| MSW | Mock Service Worker | HTTP リクエストインターセプトライブラリ |

### O

| 略語/用語 | 正式名称 | 定義 |
|---------|---------|------|
| OIDC | OpenID Connect | OAuth 2.0 ベースの認証プロトコル |
| OP | Operations | 運用管理。J-SOX IT 全般統制の一区分 |
| OWASP | Open Web Application Security Project | Web アプリケーションセキュリティの標準化団体 |

### P

| 略語/用語 | 正式名称 | 定義 |
|---------|---------|------|
| PAT | Personal Access Token | GitHub の個人アクセストークン |
| PII | Personally Identifiable Information | 個人識別情報（個人情報）|
| PR | Pull Request | コードレビューと変更管理のための GitHub 機能 |

### R

| 略語/用語 | 正式名称 | 定義 |
|---------|---------|------|
| RBAC | Role-Based Access Control | ロールベースアクセス制御 |
| RCA | Root Cause Analysis | 根本原因分析 |
| RFC | Request for Change | 変更要求。変更管理プロセスの正式申請 |
| RPO | Recovery Point Objective | 目標復旧時点。許容できる最大データ損失期間 |
| RTO | Recovery Time Objective | 目標復旧時間。障害からシステム復旧までの目標時間 |

### S

| 略語/用語 | 正式名称 | 定義 |
|---------|---------|------|
| SAML | Security Assertion Markup Language | XML ベースの認証・認可標準 |
| SAST | Static Application Security Testing | 静的アプリケーションセキュリティテスト |
| SCA | Software Composition Analysis | ソフトウェア構成分析。依存ライブラリの脆弱性検出 |
| SemVer | Semantic Versioning | セマンティックバージョニング（MAJOR.MINOR.PATCH）|
| SLA | Service Level Agreement | サービスレベル合意。サービス品質目標を定めた契約 |
| SLO | Service Level Objective | サービスレベル目標。SLA の内部目標値 |
| SoD | Segregation of Duties | 職務分離 |
| SOP | Standard Operating Procedure | 標準作業手順書 |
| SRE | Site Reliability Engineering | サイト信頼性エンジニアリング |
| SSO | Single Sign-On | シングルサインオン |
| STRIDE | Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege | 脅威モデリング手法 |

### T

| 略語/用語 | 正式名称 | 定義 |
|---------|---------|------|
| TLS | Transport Layer Security | トランスポート層セキュリティ。通信の暗号化プロトコル |
| TTL | Time to Live | キャッシュ・レコードの有効期限 |

### W

| 略語/用語 | 正式名称 | 定義 |
|---------|---------|------|
| WAF | Web Application Firewall | Web アプリケーションファイアウォール |

---

## 4. ServiceMatrix 固有用語

| 用語 | 定義 |
|------|------|
| Agent Coordinator | AI エージェントの実行を調整・制御するコンポーネント |
| Audit Trail | ServiceMatrix における監査証跡の実装。ハッシュチェーンで改竄を防止 |
| Emergency Stop | AI エージェントの全自律動作を即座に停止する機能（キルスイッチ）|
| Human Approval Gate | AI が提案した操作を人間が承認するまで実行しない制御点 |
| PR Governance | Pull Request を通じた変更管理・SoD 検証の仕組み |
| Quality Gate | CI/CD パイプラインにおける品質チェックポイント（QG-1 ～ QG-6）|
| SLA Engine | SLA の計測・違反検出・エスカレーションを行うサービス |

---

## 5. 関連ドキュメント

| ドキュメント | 参照先 |
|---|---|
| ServiceMatrix 憲章 | [SERVICEMATRIX_CHARTER.md](../00_foundation/SERVICEMATRIX_CHARTER.md) |
| 用語定義（基盤） | [TERMINOLOGY_DEFINITIONS.md](../00_foundation/TERMINOLOGY_DEFINITIONS.md) |
| 改訂履歴 | [REVISION_HISTORY.md](./REVISION_HISTORY.md) |

---

*本ドキュメントは ServiceMatrix プロジェクトの統治原則に基づき管理される。*
*変更は Change Issue → PR → CI検証 → 承認 のフローに従うこと。*
