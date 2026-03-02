# GitHub Issueワークフロー定義（Issue Workflow Definition）

Version: 2.0
Status: Active
Classification: Internal / Operations
Owner: Service Governance Authority
Compliance: ITIL 4 / ISO/IEC 20000 / J-SOX
Last Updated: 2026-03-02

---

## 1. 目的

本文書は、ServiceMatrix プロジェクトにおける GitHub Issue の
テンプレート定義、ライフサイクル管理、ラベル体系、
AI自動トリアージ仕様、およびIssueとPR・ブランチの命名連携規則を定義する。

Issue駆動開発（Issue-Driven Development）を実現し、
すべての変更が追跡可能な形で管理されることを保証する。

---

## 2. Issueテンプレート一覧

### 2.1 テンプレート種別

| テンプレート名 | 用途 | ファイル名 |
|-------------|------|---------|
| バグ報告 | 既存機能の不具合報告 | `bug_report.md` |
| 機能要求 | 新機能・機能拡張の要求 | `feature_request.md` |
| 変更要求 | 既存設計・ポリシーの変更要求 | `change_request.md` |
| インシデント | 本番障害・SLA違反の記録 | `incident_report.md` |
| セキュリティ脆弱性 | セキュリティ問題の報告（非公開推奨） | `security_vulnerability.md` |

### 2.2 バグ報告テンプレート

```markdown
---
name: バグ報告
about: 既存機能の不具合を報告する
labels: kind/bug, status/triage
---

## 概要
<!-- バグの概要を1〜2文で説明してください -->

## 再現手順
1.
2.
3.

## 期待される動作
<!-- 正常であればどう動作するべきかを記述してください -->

## 実際の動作
<!-- 実際に発生している動作を記述してください -->

## 環境情報
- OS:
- Pythonバージョン:
- Node.jsバージョン:
- ブランチ:

## エラーログ・スクリーンショット
<!-- あれば貼り付けてください -->

## SLA影響
- [ ] SLAに影響なし
- [ ] 軽微な影響あり（P3）
- [ ] 中程度の影響あり（P2）
- [ ] 重大な影響あり（P1）
- [ ] サービス停止レベル（P0）
```

### 2.3 機能要求テンプレート

```markdown
---
name: 機能要求
about: 新機能または機能拡張を要求する
labels: kind/feature, status/triage
---

## 要求する機能の概要
<!-- 1〜2文で説明してください -->

## ユーザーストーリー
As a [役割], I want [機能], so that [目的].

## 受け入れ条件
- [ ] 条件1
- [ ] 条件2

## 影響するコンポーネント
<!-- 影響を受けるシステムコンポーネントを記述してください -->

## ビジネス優先度
- [ ] Low - あれば便利
- [ ] Medium - 業務効率化に有効
- [ ] High - 重要な業務要件
- [ ] Critical - ビジネスクリティカル

## 関連するIssue / PR
<!-- あれば記述してください -->
```

### 2.4 変更要求テンプレート

```markdown
---
name: 変更要求
about: 設計・ポリシー・インフラの変更を要求する
labels: kind/change, status/triage
---

## 変更の概要
<!-- 変更内容を1〜2文で説明してください -->

## 変更理由・必要性
<!-- なぜこの変更が必要かを記述してください -->

## 変更種別
- [ ] 設計変更
- [ ] ポリシー変更
- [ ] インフラ変更
- [ ] 依存関係更新
- [ ] 設定変更

## 影響範囲
- [ ] 影響なし（ローカルのみ）
- [ ] 軽微（単一コンポーネント）
- [ ] 中程度（複数コンポーネント）
- [ ] 大規模（システム全体）

## リスク評価
- リスクレベル: [ ] Low / [ ] Medium / [ ] High / [ ] Critical
- ロールバック可能: [ ] Yes / [ ] No
- テスト計画:

## SLA影響
<!-- SLAへの影響を記述してください -->

## 承認要件
- [ ] Service Governance Authority
- [ ] セキュリティレビュー
- [ ] アーキテクチャレビュー
```

### 2.5 インシデントテンプレート

```markdown
---
name: インシデント報告
about: 本番障害・SLA違反を記録する
labels: kind/incident, priority/P0, status/open
---

## インシデント概要

| 項目 | 内容 |
|------|------|
| 発生日時 | YYYY-MM-DD HH:MM（JST） |
| 検知日時 | YYYY-MM-DD HH:MM（JST） |
| 対応開始日時 | YYYY-MM-DD HH:MM（JST） |
| 解決日時 | YYYY-MM-DD HH:MM（JST） / 対応中 |
| 影響サービス | |
| 影響ユーザー数 | |
| インシデントレベル | P0 / P1 / P2 / P3 |

## 事象の詳細

## 影響範囲

## 初動対応

## 根本原因（判明した場合）

## 再発防止策

## タイムライン
| 日時 | イベント |
|------|--------|
| | |
```

### 2.6 セキュリティ脆弱性テンプレート

```markdown
---
name: セキュリティ脆弱性
about: セキュリティ上の問題を報告する（公開前に担当者に連絡推奨）
labels: kind/security, priority/P1, status/triage
---

<!-- 重大な脆弱性の場合は、このIssueを作成する前に直接担当者に連絡してください -->

## 脆弱性の概要

## CVSSスコア（分かる場合）

## 脆弱性の種別
- [ ] SQLインジェクション
- [ ] XSS
- [ ] 認証不備
- [ ] 認可不備
- [ ] 情報漏洩
- [ ] 依存パッケージの脆弱性
- [ ] その他:

## 影響するコンポーネント

## 再現可能か
- [ ] Yes（手順は非公開チャネルで共有）
- [ ] No
- [ ] 不明

## 推奨される対策
```

---

## 3. Issueライフサイクル

### 3.1 ライフサイクル全体図

```
Open（作成）
    │
    ▼
status/triage（トリアージ待ち）
    │
    ├─ AI自動トリアージ（ラベル付け・優先度判定）
    │
    ▼
status/triaged（トリアージ済み）
    │
    ▼
status/assigned（担当者アサイン済み）
    │
    ▼
status/in-progress（作業中）
    │
    ├─ ブランチ作成 → PR作成
    │
    ▼
status/in-review（レビュー中）
    │
    ├─ CIパス確認
    ├─ レビュー承認
    │
    ▼
status/done（完了・マージ済み）
    │
    ▼
Closed（クローズ）
    │
    ├─ 完了（resolution/fixed）
    ├─ 重複（resolution/duplicate）
    ├─ 対応不要（resolution/wontfix）
    └─ 情報不足（resolution/invalid）
```

### 3.2 ライフサイクル各ステータスの定義

| ステータス | 説明 | 次のアクション |
|---------|------|-------------|
| Open | Issue作成直後 | AIトリアージを待つ |
| status/triage | トリアージ待ち | AI自動ラベル付け・優先度判定 |
| status/triaged | トリアージ完了 | 担当者アサインを待つ |
| status/assigned | 担当者アサイン済み | 作業開始を待つ |
| status/in-progress | 作業中 | ブランチ・PR作成 |
| status/in-review | PRレビュー中 | CIパス・承認待ち |
| status/done | マージ完了 | クローズを待つ |

### 3.3 SLAに基づくライフサイクル時間制限

| 優先度 | トリアージ完了まで | 担当者アサインまで | 解決目標 |
|-------|----------------|----------------|---------|
| P0（Critical） | 15分 | 30分 | 4時間 |
| P1（High） | 1時間 | 4時間 | 24時間 |
| P2（Medium） | 4時間 | 1営業日 | 5営業日 |
| P3（Low） | 1営業日 | 3営業日 | 15営業日 |

---

## 4. ラベル体系

### 4.1 kind/ プレフィックス（Issue種別）

| ラベル | 説明 | 色 |
|-------|------|-----|
| `kind/bug` | バグ・不具合 | #d73a4a |
| `kind/feature` | 新機能・機能拡張 | #0075ca |
| `kind/change` | 変更要求 | #e4e669 |
| `kind/incident` | インシデント | #b60205 |
| `kind/security` | セキュリティ問題 | #e11d48 |
| `kind/docs` | ドキュメント | #0052cc |
| `kind/refactor` | リファクタリング | #cfd3d7 |
| `kind/chore` | 雑務・メンテナンス | #fef2c0 |
| `kind/ci` | CI/CD関連 | #5319e7 |

### 4.2 priority/ プレフィックス（優先度）

| ラベル | 説明 | 対応SLA |
|-------|------|--------|
| `priority/P0` | Critical - サービス停止 | 4時間以内 |
| `priority/P1` | High - 重大な機能障害 | 24時間以内 |
| `priority/P2` | Medium - 機能低下 | 5営業日以内 |
| `priority/P3` | Low - 軽微・改善要望 | 15営業日以内 |

### 4.3 status/ プレフィックス（ライフサイクルステータス）

| ラベル | 説明 |
|-------|------|
| `status/triage` | トリアージ待ち |
| `status/triaged` | トリアージ完了 |
| `status/assigned` | 担当者アサイン済み |
| `status/in-progress` | 作業中 |
| `status/blocked` | ブロック中（依存関係待ち） |
| `status/in-review` | レビュー中 |
| `status/done` | 完了 |

### 4.4 component/ プレフィックス（影響コンポーネント）

| ラベル | 説明 |
|-------|------|
| `component/api` | FastAPI バックエンド |
| `component/ui` | Next.js フロントエンド |
| `component/db` | PostgreSQL データベース |
| `component/ai` | Claude AI 連携 |
| `component/ci` | CI/CD パイプライン |
| `component/docs` | ドキュメント |
| `component/governance` | 統治・ポリシー |
| `component/security` | セキュリティ |
| `component/infra` | インフラ・デプロイ |

### 4.5 sla-impact/ プレフィックス（SLA影響）

| ラベル | 説明 |
|-------|------|
| `sla-impact/availability` | 可用性SLAに影響 |
| `sla-impact/performance` | パフォーマンスSLAに影響 |
| `sla-impact/security` | セキュリティSLAに影響 |
| `sla-impact/none` | SLA影響なし |

---

## 5. マイルストーン管理方針

### 5.1 マイルストーン命名規則

```
v{major}.{minor}.{patch} - {YYYY-MM-DD}
```

例: `v1.0.0 - 2026-06-30`

### 5.2 マイルストーン種別

| 種別 | 命名例 | 用途 |
|------|-------|------|
| リリースマイルストーン | `v1.0.0 - 2026-06-30` | 本番リリース |
| スプリントマイルストーン | `Sprint-2026-03` | 月次スプリント |
| 緊急対応 | `Hotfix-2026-03-02` | 緊急修正 |

### 5.3 マイルストーン管理ルール

- Issueは1つのアクティブなマイルストーンにのみ紐付ける
- マイルストーン期日は現実的なスコープに基づいて設定する
- スコープ変更はChange Issueとして管理する
- 完了したマイルストーンは30日以内にクローズする

---

## 6. AI自動トリアージ

### 6.1 ClaudeCodeによる自動ラベル付け

Issueが作成されると、ClaudeCode（CI経由）が以下を自動的に実施する。

| 処理 | 説明 | 自律度レベル |
|------|------|------------|
| kind/ ラベル付け | Issue内容からkind種別を判定 | L2 |
| priority/ ラベル付け | 緊急度・影響度から優先度を判定 | L2 |
| component/ ラベル付け | 影響コンポーネントを特定 | L2 |
| sla-impact/ ラベル付け | SLA影響度を判定 | L2 |
| status/triaged への更新 | トリアージ完了をマーク | L2 |

### 6.2 担当者推薦ロジック

ClaudeCodeは以下の基準で担当者を推薦する（実際のアサインは人間が承認する）。

| 基準 | 説明 |
|------|------|
| コンポーネント親和性 | 過去のPRからコンポーネント担当者を特定 |
| 現在の作業負荷 | アサイン中のIssue数が少ない担当者を優先 |
| 専門スキル | セキュリティ・AI等の専門知識が必要な場合は専門担当者を推薦 |

### 6.3 AIトリアージコメント形式

```markdown
## AI Triage Result

- **Kind**: kind/bug（信頼度: 0.94）
- **Priority**: priority/P2（信頼度: 0.87）
- **Component**: component/api（信頼度: 0.91）
- **SLA Impact**: sla-impact/availability（信頼度: 0.78）

### 推奨担当者
@{user} - APIコンポーネント過去PR実績あり

### 判断根拠
Issue内容に「APIエンドポイント」「500エラー」が含まれており、
過去の類似Issueパターンからcomponent/apiと判定しました。

---
_この判断はAIによる提案です。最終決定は人間が行ってください。_
```

---

## 7. IssueとPR・ブランチの命名連携規則

### 7.1 ブランチ命名規則

Issue番号をブランチ名に含めることで、IssueとPR・ブランチを追跡可能にする。

```
{kind}/{issue-number}-{kebab-case-description}
```

| Issue種別 | ブランチ命名例 |
|---------|-------------|
| バグ修正 | `fix/123-auth-token-expiry-error` |
| 新機能 | `feature/124-incident-dashboard` |
| ドキュメント | `docs/125-update-api-spec` |
| リファクタリング | `refactor/126-service-layer-cleanup` |
| セキュリティ | `security/127-sql-injection-fix` |
| CI/CD | `ci/128-add-bandit-scan` |
| ホットフィックス | `hotfix/129-critical-data-loss-fix` |

### 7.2 PRタイトル命名規則

```
{type}: {説明} (#{issue-number})
```

例: `fix: 認証トークンの有効期限エラーを修正 (#123)`

### 7.3 コミットメッセージ命名規則

```
{type}(#{issue-number}): {説明}
```

例: `fix(#123): JWTトークン検証ロジックのタイムゾーン処理を修正`

### 7.4 自動クローズキーワード

PRマージ時にIssueを自動クローズするため、PRの説明文に以下を含める。

```
Closes #123
```

---

## 8. 関連文書

- `PULL_REQUEST_POLICY.md` - プルリクエストポリシー
- `BRANCH_STRATEGY.md` - ブランチ戦略定義
- `SLA_DEFINITION.md` - SLA定義
- `AI_AUTONOMY_LEVEL_MATRIX.md` - AI自律度レベルマトリックス
- `GOVERNANCE_MODEL.md` - 統治モデル

---

以上
