# ServiceMatrix 用語定義集（Terminology Definitions）

Version: 1.0
Status: Active
Owner: Service Governance Authority
Classification: Foundation Reference Document
Last Updated: 2026-03-02

---

## 1. 文書の目的

本文書は、ServiceMatrix プロジェクトで使用される主要な用語を統一的に定義する。
プロジェクトに関わるすべてのステークホルダー（人間・AI エージェント含む）は、
本文書に定義された意味に基づいてコミュニケーションを行う。

用語の解釈に疑義が生じた場合は、本文書の定義が優先される。

---

## 2. 用語の分類体系

用語は以下のカテゴリに分類される。

| カテゴリ | 略称 | 説明 |
|----------|------|------|
| サービス管理 | SM | ITIL / ITSM 関連用語 |
| 統治・コンプライアンス | GV | 統治・監査・法規制関連用語 |
| AI・エージェント | AI | AI 知能層関連用語 |
| DevOps・技術 | DV | GitHub / CI/CD / 技術基盤関連用語 |
| プロジェクト固有 | PJ | ServiceMatrix 固有用語 |

---

## 3. サービス管理（SM）カテゴリ

### Incident（インシデント）

**定義**: 計画外のサービス中断、またはサービス品質の低下を引き起こす事象。

**ServiceMatrix における使用**: GitHub Issues の Incident ラベルが付与されたチケットとして管理される。優先度マトリクスに基づいて分類され、SLA に基づく対応期限が設定される。

**関連用語**: Priority Matrix, SLA, Escalation Level

---

### Change（変更）

**定義**: IT サービスまたはその構成要素に対する追加・修正・削除。

**ServiceMatrix における使用**: GitHub Issues の Change ラベルが付与され、変更タイプ（Standard / Normal / Emergency）に応じた承認フローが適用される。Pull Request を通じて実装される。

**関連用語**: RFC, CAB, Change Authority

---

### Problem（問題）

**定義**: 1つ以上のインシデントの根本原因、または潜在的なインシデント原因。

**ServiceMatrix における使用**: 繰り返し発生するインシデントのパターンから AI が自動検出し、Problem チケットとして起票される。既知エラーデータベースとの連携により管理される。

**関連用語**: Known Error, Root Cause Analysis, Workaround

---

### Request（サービス要求）

**定義**: ユーザーからの定型的なサービス提供依頼。インシデントや変更とは異なり、事前定義されたサービスの提供を求めるもの。

**ServiceMatrix における使用**: サービスカタログに定義されたサービスメニューに基づいて処理される。可能な場合は自動フルフィルメントが適用される。

**関連用語**: Service Catalog, Fulfillment

---

### Release（リリース）

**定義**: テスト・承認済みの変更を本番環境に展開するプロセスおよびその成果物。

**ServiceMatrix における使用**: GitHub のリリース機能と CI/CD パイプラインを通じて管理される。リリース計画・承認・実施・事後検証の全工程が追跡される。

**関連用語**: Deployment, CI/CD Pipeline

---

### SLA（Service Level Agreement / サービスレベル合意）

**定義**: サービス提供者とサービス利用者の間で合意された、サービス品質の目標水準を定めた合意文書。

**ServiceMatrix における使用**: SLA_DEFINITION.md で定義された指標に基づき、自動監視・逸脱検知が行われる。SLA 逸脱は自動エスカレーションの対象となる。

**主な SLA 指標**:
- 可用性目標（例: 99.9%）
- 応答時間目標（例: Priority 1 は 15分以内）
- 解決時間目標（例: Priority 1 は 4時間以内）

---

### OLA（Operational Level Agreement / 運用レベル合意）

**定義**: サービス提供に関与する内部チーム間の合意。SLA を達成するために各チームが果たすべき責任と目標水準を定める。

**ServiceMatrix における使用**: プロセス間の引き継ぎ時間や、チーム間の応答目標として設定される。

---

### KPI（Key Performance Indicator / 重要業績評価指標）

**定義**: 目標達成度を測定するための定量的指標。

**ServiceMatrix における使用**: STRATEGIC_OBJECTIVES.md で定義された各戦略目標に対して設定され、ダッシュボードでリアルタイムに可視化される。

---

### CMDB（Configuration Management Database / 構成管理データベース）

**定義**: 組織の IT インフラストラクチャを構成するすべての構成アイテム（CI）とその関係性を管理するデータベース。

**ServiceMatrix における使用**: サービス間の依存関係、構成アイテムの変更履歴、影響分析の基盤として使用される。

---

### CI / Configuration Item（構成アイテム）

**定義**: サービス管理の文脈において管理対象となる IT コンポーネント。ハードウェア、ソフトウェア、ドキュメント、サービス等を含む。

**注意**: CI/CD の CI（Continuous Integration）とは異なる概念である。文脈により区別すること。

**ServiceMatrix における使用**: CMDB に登録され、変更管理・影響分析・インシデント管理の基盤となる。

---

### RFC（Request for Change / 変更要求）

**定義**: IT サービスまたはインフラストラクチャに対する変更を正式に要求する文書。

**ServiceMatrix における使用**: GitHub Issues として起票され、Change ラベルと変更タイプ（Standard / Normal / Emergency）が付与される。Pull Request とリンクされ、承認フローが適用される。

---

### CAB（Change Advisory Board / 変更諮問委員会）

**定義**: 変更の評価・優先順位付け・承認を行う委員会。技術・ビジネス双方の視点から変更のリスクと影響を審査する。

**ServiceMatrix における使用**: Normal Change および影響度の高い変更に対して CAB レビューが実施される。GitHub の PR レビュー機能と組み合わせて運用される。

**構成メンバー（標準）**:
- 変更管理者（議長）
- 技術リード
- サービスオーナー
- セキュリティ担当
- 必要に応じた SME（Subject Matter Expert）

---

### MTTR（Mean Time to Restore / 平均復旧時間）

**定義**: サービス障害の検知から復旧までの平均時間。

**ServiceMatrix における使用**: インシデント管理の主要 KPI として測定される。AI による対応支援を通じて削減を目指す。

---

### MTBF（Mean Time Between Failures / 平均故障間隔）

**定義**: サービスの連続稼働の平均時間。信頼性の指標。

**ServiceMatrix における使用**: サービスの信頼性評価指標として使用される。

---

### Known Error（既知エラー）

**定義**: 根本原因が特定され、回避策が文書化された問題。

**ServiceMatrix における使用**: 問題管理プロセスの出力として管理され、インシデント対応時の参照情報として活用される。

---

### Workaround（回避策）

**定義**: インシデントまたは問題の影響を軽減するための暫定的な対処方法。根本的な解決ではない。

**ServiceMatrix における使用**: 既知エラーレコードに記録され、恒久対策が完了するまでのインシデント対応に使用される。

---

### Service Catalog（サービスカタログ）

**定義**: ユーザーが利用可能なサービスの一覧とその詳細（説明、SLA、手順等）を記載した文書。

**ServiceMatrix における使用**: サービス要求管理の基盤として使用される。

---

### Escalation Level（エスカレーションレベル）

**定義**: インシデントや問題の対応を上位の権限者・専門家に引き上げる段階。

**ServiceMatrix における使用**: Priority Matrix と SLA に基づいて自動エスカレーションが設定される。

| レベル | 対象 | トリガー |
|--------|------|----------|
| L1 | サービスデスク | 初期受付 |
| L2 | 技術チーム | L1 で解決不可 |
| L3 | スペシャリスト | L2 で解決不可 |
| 管理者 | マネジメント | SLA 逸脱リスク |

---

### Priority Matrix（優先度マトリクス）

**定義**: インシデントの影響度（Impact）と緊急度（Urgency）から優先度（Priority）を決定するマトリクス。

**ServiceMatrix における使用**:

| | 緊急度: 高 | 緊急度: 中 | 緊急度: 低 |
|---|-----------|-----------|-----------|
| **影響度: 高** | P1 (Critical) | P2 (High) | P3 (Medium) |
| **影響度: 中** | P2 (High) | P3 (Medium) | P4 (Low) |
| **影響度: 低** | P3 (Medium) | P4 (Low) | P5 (Planning) |

---

### KRI（Key Risk Indicator / 重要リスク指標）

**定義**: リスクが許容範囲を超えつつあることを早期警戒する定量的指標。KPI が目標達成を測定するのに対し、KRI は潜在リスクの顕在化を予告する。

**ServiceMatrix における使用**: SLA 逸脱リスク、インシデント頻度増加、変更失敗率上昇などを KRI として定義し、閾値超過時に自動エスカレーションを行う。

**関連用語**: KPI, SLA, Risk Score, Escalation Level

---

## 4. 統治・コンプライアンス（GV）カテゴリ

### Governance Matrix（統治マトリクス）

**定義**: ServiceMatrix の4軸（Process × Intelligence × DevOps × Governance）の交差により構成される統治構造。各軸の交差点が統治制御ポイントとなる。

---

### Risk Score（リスクスコア）

**定義**: 変更・インシデント・問題等のリスクを定量的に評価した数値。影響度、発生確率、検出可能性等の要素から算出される。

**ServiceMatrix における使用**: AI が自動算出し、承認フローの判断材料として使用される。

| スコア範囲 | リスクレベル | 必要な承認 |
|-----------|-------------|-----------|
| 0-20 | 低 | 自動承認可 |
| 21-50 | 中 | マネージャー承認 |
| 51-80 | 高 | CAB 承認 |
| 81-100 | 極高 | 経営層承認 |

---

### Segregation of Duties / SoD（職務分掌）

**定義**: 不正やエラーを防止するために、単一の個人が対立する職務を同時に遂行することを禁止する統制原則。

**ServiceMatrix における使用**: GitHub の権限設定と承認フローにより技術的に強制される。

**主な分掌要件**:
- 変更の申請者 ≠ 承認者
- 開発者 ≠ 本番環境デプロイ者
- テスト実施者 ≠ テスト承認者

---

### Audit Trail（監査証跡）

**定義**: すべての操作・判断・変更の時系列記録。監査時に活動の正当性を証明するために使用される。

**ServiceMatrix における使用**: Git の履歴、GitHub Issues/PR の履歴、AI 判断ログとして自動的に蓄積される。

---

### J-SOX（日本版 SOX 法 / 金融商品取引法）

**定義**: 上場企業に対して内部統制の整備・評価・報告を求める日本の法規制。IT 全般統制はその重要な構成要素。

**ServiceMatrix における使用**: IT 全般統制の要件（アクセス管理、変更管理、運用管理）を設計に組み込む。

---

### RBAC（Role-Based Access Control / ロールベースアクセス制御）

**定義**: ユーザーの職務ロールに基づいてシステムリソースへのアクセス権限を付与・制限するアクセス制御モデル。

**ServiceMatrix における使用**: GitHub の Teams / CODEOWNERS と組み合わせ、リポジトリへのアクセス・保護ブランチへのプッシュ・PRの承認権限をロールに基づいて管理する。システム管理者・変更管理者・プロセスオーナー・エンドユーザー等のロール別に権限を定義する。

**関連用語**: Segregation of Duties, Least Privilege, CODEOWNERS

---

### 最小権限原則（Least Privilege Principle）

**定義**: ユーザー・プロセス・AI エージェントが業務を遂行するために必要な最小限の権限のみを付与するセキュリティ原則。

**ServiceMatrix における使用**: GitHub の権限設定において各ロールに必要最小限のアクセス権のみを付与する。AI エージェントも同様に、実行に必要な権限のみを持ち、過剰な権限昇格を禁止する。

**関連用語**: RBAC, Segregation of Duties, AI Governance

---

### ITIL 4（IT Infrastructure Library 第4版）

**定義**: Axelos が策定した IT サービスマネジメントのグローバルベストプラクティスフレームワーク。サービスバリューシステム（SVS）を中心に、4次元モデルと34のプラクティスで構成される。

**ServiceMatrix における使用**: インシデント管理、変更管理（Change Enablement）、問題管理、サービス要求管理の各プロセスを ITIL 4 プラクティスに準拠して設計する。ITIL 4 の「シフトレフト」アプローチに基づき、AI による早期予防を実装する。

**主要コンセプト**: サービスバリューチェーン、グアランティー（保証）、ユーティリティ（効用）、コンティニュアルインプルーブメント

---

### ISO/IEC 20000（IT サービスマネジメントシステム規格）

**定義**: IT サービスマネジメントシステム（SMS）の要求事項を定めた国際規格。ITIL との整合性が高く、SMS の認証取得の基準として使用される。

**ServiceMatrix における使用**: SMS の設計・運用において ISO/IEC 20000 の要求事項（計画・実施・チェック・改善のサイクル）を内在化する。特にサービスレベル管理、変更管理、インシデント管理、問題管理の各プロセスが ISO/IEC 20000 の要求事項を充足するよう設計される。

**関連条項**: ISO/IEC 20000-1:2018 第8章（サービスシステム運用）

---

### Compliance（コンプライアンス）

**定義**: 法規制、業界標準、社内ポリシーへの準拠。

**ServiceMatrix における使用**: ポリシーの技術的強制と自動チェックにより、設計段階からコンプライアンスを内在化する。

---

### Change Authority（変更権限者）

**定義**: 変更の承認権限を持つ個人または委員会。変更タイプとリスクレベルに応じて権限者が異なる。

**ServiceMatrix における使用**: CHANGE_AUTHORITY_STRUCTURE.md で定義された権限構造に基づき、GitHub PR の承認者として設定される。

---

## 5. AI・エージェント（AI）カテゴリ

### Agent Teams（エージェントチーム）

**定義**: 複数の AI エージェントが役割分担し、並列で作業を遂行するチーム構成。ServiceMatrix における AI 知能層の主要な実行形態。

**ServiceMatrix における使用**: 機能開発（Backend / Frontend / Test / Security）やレビュー（Security / Performance / Coverage / Architecture）に使用される。各エージェントは個別の WorkTree で作業し、衝突を回避する。

---

### SubAgent（サブエージェント）

**定義**: Agent Teams とは異なり、同一コンテキスト内で軽量なタスクを実行する単一 AI エージェント。

**ServiceMatrix における使用**: Lint 修正、単一ファイル改善、単一ロジック修正、軽量レビューなどの小規模タスクに使用される。WorkTree 分離は不要。

---

### AI Governance（AI 統治）

**定義**: AI エージェントの行動範囲、権限、制約、監視、記録に関する統治フレームワーク。

**ServiceMatrix における使用**: AI_GOVERNANCE_POLICY.md で定義された原則に基づき、AI の自律レベル（L1/L2/L3）が管理される。

---

### Risk Scoring Engine（リスクスコアリングエンジン）

**定義**: 変更・インシデントのリスクを複数の要素から自動的に数値化するエンジン。

**評価要素**:
- 影響範囲（影響を受けるサービス/ユーザー数）
- 変更の複雑度
- 過去の類似変更の成功/失敗率
- 関連する既知のリスク
- ロールバック可能性

---

### Auto-Remediation Loop（自動修復ループ）

**定義**: ポリシーで定義された条件に合致するインシデントや異常を、人間の介入なく自動的に修復するメカニズム。

**ServiceMatrix における使用**: 低リスクかつ定型的な修復に限定して適用される。すべての自動修復は記録され、事後レビューの対象となる。

---

## 6. DevOps・技術（DV）カテゴリ

### DevOps（デブオプス）

**定義**: 開発（Development）と運用（Operations）の統合を目指す文化・哲学・実践の総称。継続的デリバリー、インフラのコード化、自動化、測定、共有を中核概念とする。

**ServiceMatrix における使用**: GitHub ネイティブな統治設計を通じて、開発プロセスと IT サービス運用プロセスを一体化する。CI/CD パイプラインが変更管理の統治ゲートとして機能し、自動化が監査証跡を生成する。

**関連用語**: CI/CD Pipeline, GitOps, GitHub Actions

---

### GitOps（ギットオプス）

**定義**: Git リポジトリを「唯一の信頼できる情報源（Single Source of Truth）」として、インフラ・アプリケーションの望ましい状態を宣言的に定義し、Git の変更駆動で自動デプロイを実現する運用モデル。

**ServiceMatrix における使用**: すべての設定変更・ポリシー変更・ドキュメント変更を Git 経由で管理し、レビュー・CI 通過・承認を経てのみ反映を許可する。変更履歴が自動的に監査証跡となる。

**関連用語**: CI/CD Pipeline, Branch Protection, Pull Request

---

### WorkTree（ワークツリー）

**定義**: Git の Working Tree 機能を用いて、同一リポジトリの複数ブランチを同時にチェックアウトする仕組み。

**ServiceMatrix における使用**: Agent Teams の各エージェントが個別の WorkTree で作業することで、同一ファイルの同時編集による衝突を防止する。

---

### CI/CD Pipeline（CI/CD パイプライン）

**定義**: Continuous Integration（継続的統合）/ Continuous Delivery（継続的デリバリー）のための自動化パイプライン。

**ServiceMatrix における使用**: GitHub Actions を基盤として構築される。コード品質チェック、テスト、統治ポリシーチェック、デプロイが自動化される。

---

### Branch Protection（ブランチ保護）

**定義**: GitHub のブランチ保護ルールにより、特定ブランチへの直接プッシュを制限し、PR とレビューを強制する仕組み。

**ServiceMatrix における使用**: main ブランチは保護され、CI の通過とレビュー承認なしにはマージできない。

---

### Pull Request / PR（プルリクエスト）

**定義**: ブランチの変更をレビュー・承認を経てマージするための GitHub の仕組み。

**ServiceMatrix における使用**: すべての変更は PR を通じて提出され、変更タイプに応じた承認フローが適用される。ServiceMatrix の変更承認ゲートとして機能する。

---

### GitHub Actions（GitHub アクションズ）

**定義**: GitHub のネイティブ CI/CD サービス。ワークフローを YAML で定義し、イベント駆動で自動実行する。

**ServiceMatrix における使用**: 統治ポリシーチェック、テスト自動実行、デプロイ、監査証跡生成などに使用される。

---

### Labels（ラベル）

**定義**: GitHub Issues / PR に付与する分類タグ。

**ServiceMatrix における使用**: プロセスタイプ（Incident / Change / Problem / Request）、優先度、状態、カテゴリなどの分類に使用される。

---

## 7. プロジェクト固有（PJ）カテゴリ

### ServiceMatrix 4軸モデル

**定義**: ServiceMatrix のアーキテクチャを構成する4つの統治軸の交差構造。

| 軸 | 英名 | 役割 |
|----|------|------|
| プロセス軸 | Process | サービス管理プロセスの実行 |
| インテリジェンス軸 | Intelligence | AI による知的支援 |
| DevOps 軸 | DevOps | GitHub 連携と自動化 |
| 統治軸 | Governance | コンプライアンスと監査 |

---

### Matrix Intersection（マトリクス交差点）

**定義**: 4軸モデルにおいて、2つ以上の軸が交差する制御ポイント。統治ロジックが適用される箇所。

**例**: Process × Governance = 承認フロー、Process × Intelligence = AI 分類、DevOps × Governance = CI 統治チェック

---

### Governance Gate（統治ゲート）

**定義**: プロセスの進行を制御する承認・検証ポイント。統治ゲートを通過するには、定められた条件を満たす必要がある。

**ServiceMatrix における使用**: PR 承認、CI 通過、SLA チェック、リスク評価承認などが統治ゲートとして機能する。

---

### Service Governance Authority

**定義**: ServiceMatrix プロジェクトの最高統治権限。戦略的方針・ポリシーの最終承認権限を持つ。

---

### Non-Negotiables（不可侵原則）

**定義**: いかなる理由があっても違反が許容されない絶対的原則。SERVICEMATRIX_CHARTER.md の第11章で定義される。

---

## 8. 略語一覧

| 略語 | 正式名称 | 日本語名 |
|------|---------|---------|
| CAB | Change Advisory Board | 変更諮問委員会 |
| CI | Configuration Item | 構成アイテム |
| CI/CD | Continuous Integration / Continuous Delivery | 継続的統合 / 継続的デリバリー |
| CMDB | Configuration Management Database | 構成管理データベース |
| CMMI | Capability Maturity Model Integration | 能力成熟度モデル統合 |
| ITIL | Information Technology Infrastructure Library | IT インフラストラクチャライブラリ |
| ITSM | IT Service Management | IT サービスマネジメント |
| J-SOX | Japanese Sarbanes-Oxley Act | 日本版 SOX 法 |
| KGI | Key Goal Indicator | 重要目標達成指標 |
| KPI | Key Performance Indicator | 重要業績評価指標 |
| MTBF | Mean Time Between Failures | 平均故障間隔 |
| MTTR | Mean Time to Restore | 平均復旧時間 |
| OLA | Operational Level Agreement | 運用レベル合意 |
| PR | Pull Request | プルリクエスト |
| RACI | Responsible, Accountable, Consulted, Informed | 責任分担マトリクス |
| RFC | Request for Change | 変更要求 |
| SLA | Service Level Agreement | サービスレベル合意 |
| SME | Subject Matter Expert | 分野専門家 |
| SMS | Service Management System | サービスマネジメントシステム |
| SoD | Segregation of Duties | 職務分掌 |

---

## 9. 用語の改定手順

新規用語の追加・既存用語の修正は、以下の手順に従う。

1. 用語変更の提案（Issue 起票）
2. 影響範囲の確認（他文書への波及）
3. レビューと承認
4. 本文書の更新（PR 経由）
5. 関連文書の整合性確認

用語の改定は、プロジェクト全体のコミュニケーションに影響するため、
慎重に管理されなければならない。
