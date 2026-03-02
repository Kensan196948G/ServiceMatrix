# Pull Request ポリシー

ServiceMatrix Pull Request Policy

Version: 2.0
Status: Active
Classification: Internal DevOps Document

---

## 1. はじめに

本ドキュメントは ServiceMatrix における Pull Request (PR) の運用ポリシーを定義する。
PR はすべてのコード変更のゲートキーパーであり、品質・セキュリティ・統治の最終防衛線である。

---

## 2. PR の基本原則

1. **すべてのコード変更は PR を通じて main にマージする**
2. **PR は Issue と紐付ける（`Closes #NNN` 必須）**
3. **PR は CI をパスしなければマージできない**
4. **PR は最低 1 名のレビュー承認を必要とする**
5. **PR は適切なサイズに保つ（目安: 変更行数 500 行以下）**
6. **Draft PR は作業中の可視化に活用する（マージ禁止）**

---

## 3. PR タイトルフォーマット

### 3.1 Conventional Commits 準拠

PR タイトルは Conventional Commits 規約に準拠する。

```
{type}(#{issue-number}): {short-description}
```

### 3.2 タイプ一覧

| タイプ | 説明 | 例 |
|---|---|---|
| `feat` | 新機能追加 | `feat(#42): インシデントダッシュボードを追加` |
| `fix` | バグ修正 | `fix(#87): SLA タイマー計算の修正` |
| `docs` | ドキュメント変更のみ | `docs(#103): アーキテクチャ設計書を追加` |
| `refactor` | リファクタリング（機能変更なし） | `refactor(#115): イベントディスパッチャの再構築` |
| `test` | テスト追加・修正 | `test(#130): Incident Service のユニットテスト追加` |
| `ci` | CI/CD 設定変更 | `ci(#140): セキュリティスキャンジョブを追加` |
| `chore` | 依存更新・ビルド設定など | `chore(#170): 依存パッケージの更新` |
| `security` | セキュリティ修正 | `security(#155): XSS 脆弱性の修正` |
| `perf` | パフォーマンス改善 | `perf(#160): CMDB クエリの最適化` |

### 3.3 タイトルルール

- 日本語で記述する
- 50 文字以内に収める（タイプとスコープを除く）
- 動詞で始める（「追加」「修正」「削除」「更新」「改善」等）
- 末尾にピリオドを付けない

---

## 4. PR テンプレート

### 4.1 標準 PR テンプレート

`.github/PULL_REQUEST_TEMPLATE.md` に配置する。

```markdown
## 概要

<!-- この PR で何を変更するかを簡潔に説明してください -->

## 関連 Issue

Closes #

## 変更内容

<!-- 具体的な変更内容を箇条書きで記載してください -->

-
-
-

## 変更種別

- [ ] 新機能 (feat)
- [ ] バグ修正 (fix)
- [ ] ドキュメント (docs)
- [ ] リファクタリング (refactor)
- [ ] テスト (test)
- [ ] CI/CD (ci)
- [ ] セキュリティ (security)
- [ ] パフォーマンス (perf)
- [ ] その他 (chore)

## 影響範囲

- [ ] 影響範囲小（1〜2 ファイル）
- [ ] 影響範囲中（3〜10 ファイル）
- [ ] 影響範囲大（10 ファイル超）

## SLA 影響

- [ ] SLA 影響なし
- [ ] SLA 関連ロジックを変更した（変更内容を詳述すること）

## セキュリティ影響

- [ ] セキュリティ影響なし
- [ ] セキュリティ関連変更あり（セキュリティチームレビュー必須）

## リスク評価

- [ ] 低リスク（既存機能への影響なし）
- [ ] 中リスク（既存機能への軽微な影響あり）
- [ ] 高リスク（既存機能への重大な影響あり）

## テスト実施内容

- [ ] ユニットテストを追加 / 更新した
- [ ] 結合テストを追加 / 更新した
- [ ] 手動テストを実施した
- [ ] E2E テストで確認した

## テスト結果

<!-- テスト結果の概要を記載してください（カバレッジ % など） -->

## ロールバック計画

<!-- 問題発生時のロールバック方法を記載してください -->

## チェックリスト

- [ ] Conventional Commits に従ったタイトルを設定した
- [ ] 関連 Issue を紐付けた（`Closes #NNN`）
- [ ] 変更内容の説明を記載した
- [ ] テストを実施した
- [ ] ドキュメントを更新した（必要な場合）
- [ ] セキュリティへの影響を確認した
- [ ] SLA への影響を確認した
- [ ] CI がパスしている
```

---

## 5. レビュー必須要件

### 5.1 基本要件

| 要件 | 設定値 |
|---|---|
| 最低承認者数 | 1 名 |
| CI ステータスチェック | 全パス必須 |
| ブランチ同期 | main と最新同期必須 |
| コメント解決 | 全コメント解決必須 |
| 承認の有効期限 | 追加コミット時に失効 |

### 5.2 変更タイプ別の承認要件

| 変更タイプ | 必要承認者数 | 必須レビュー観点 | 承認者要件 |
|---|---|---|---|
| `feat`（新機能） | 1 名 | 設計・品質・テスト | チームメンバー以上 |
| `fix`（バグ修正） | 1 名 | 原因分析・回帰テスト | チームメンバー以上 |
| `docs`（ドキュメント） | 1 名 | 正確性・整合性 | チームメンバー以上 |
| `refactor`（リファクタ） | 1 名 | 動作互換性・テスト | シニアメンバー以上 |
| `security`（セキュリティ） | **2 名** | セキュリティ影響・脆弱性 | セキュリティ担当 + シニア |
| `ci`（CI/CD） | 1 名 | パイプライン整合性 | DevOps 担当 |
| 高リスク変更 | **2 名** | 全観点 | シニア + テックリード |
| 設計変更 | **2 名** | アーキテクチャ整合性 | アーキテクト + テックリード |
| リリース PR | **2 名** | 全観点 | アーキテクト + テックリード |
| Hotfix PR | **2 名** | 影響範囲・テスト | テックリード + 承認者 |

### 5.3 CODEOWNERS 設定

`.github/CODEOWNERS` に配置する。

```
# デフォルトレビュアー
*                           @servicematrix/core-team

# アーキテクチャドキュメント
docs/02_architecture/       @servicematrix/architects

# セキュリティ関連
docs/06_security*/          @servicematrix/security-team
**/security/**              @servicematrix/security-team

# CI/CD 設定
.github/workflows/          @servicematrix/devops-team
.github/actions/            @servicematrix/devops-team

# 統治ドキュメント
docs/01_governance/         @servicematrix/governance-team
CLAUDE.md                   @servicematrix/governance-team

# SLA 定義
docs/07_sla*/               @servicematrix/sla-team

# AI ガバナンス
docs/04_agents_ai/          @servicematrix/ai-governance-team
```

---

## 6. レビュー観点

### 6.1 標準レビューチェックリスト

#### 設計・アーキテクチャ

- [ ] アーキテクチャ原則に準拠している
- [ ] レイヤー構造を違反していない
- [ ] 依存関係の方向が正しい
- [ ] 過剰設計になっていない

#### コード品質

- [ ] 命名が適切で理解しやすい
- [ ] 関数・メソッドの責務が単一である
- [ ] 重複コードが存在しない
- [ ] エラーハンドリングが適切である
- [ ] ログ出力が適切である

#### セキュリティ

- [ ] 入力バリデーションが実装されている
- [ ] 認証・認可チェックが適切である
- [ ] ハードコードされたシークレットがない
- [ ] OWASP Top 10 の脆弱性がない
- [ ] SQL インジェクション対策がある

#### テスト

- [ ] テストカバレッジが維持されている（80% 以上）
- [ ] エッジケースがテストされている
- [ ] テストが独立して実行可能である
- [ ] テストが読みやすく意図が明確である

#### ドキュメント

- [ ] 公開 API にドキュメントがある
- [ ] 複雑なロジックにコメントがある
- [ ] 関連ドキュメントが更新されている

### 6.2 レビューコメントの規約

| プレフィックス | 意味 | ブロッキング |
|---|---|---|
| `[MUST]` | 必須修正（マージ前に対応必須） | **はい** |
| `[SHOULD]` | 推奨修正（強く推奨するが必須ではない） | いいえ |
| `[NIT]` | 軽微な指摘（任意対応） | いいえ |
| `[QUESTION]` | 質問・確認（回答後解決） | いいえ |
| `[SUGGESTION]` | 提案（参考として） | いいえ |
| `[SECURITY]` | セキュリティ上の問題（必須対応） | **はい** |

---

## 7. PR マージ前チェックリスト

| 確認項目 | 確認方法 |
|---|---|
| CI が全パスしている | GitHub CI ステータス確認 |
| 最低 1 名の承認がある | GitHub Reviewers 欄確認 |
| main ブランチと同期している | GitHub ブランチ同期状態確認 |
| レビューコメントが全解決されている | GitHub Conversation 欄確認 |
| コンフリクトが存在しない | GitHub コンフリクト表示確認 |
| PR の説明が十分に記載されている | PR 本文確認 |
| 関連 Issue が紐付けられている | `Closes #NNN` 記載確認 |

---

## 8. PR マージ戦略

### 8.1 Squash Merge（標準）

通常の PR では Squash Merge を使用する。

```
feature/42-dashboard (複数コミット) → main (1 コミット: squash)
```

**Squash コミットメッセージ:**

```
feat(#42): インシデントダッシュボードを追加

- SLA 状況ウィジェットを実装
- インシデントトレンドグラフを実装

Closes #42
```

### 8.2 Merge Commit（リリース時）

リリースブランチのマージ時のみ Merge Commit を使用する。

```
release/v1.0.0 → main (Merge Commit + tag: v1.0.0)
```

### 8.3 Rebase Merge

使用しない（禁止）。

---

## 9. PR サイズガイドライン

### 9.1 サイズ基準

| サイズ | 変更行数 | レビュー時間目安 | 推奨度 |
|---|---|---|---|
| XS | 1〜50 行 | 約 15 分 | 最適 |
| S | 51〜200 行 | 約 30 分 | 良好 |
| M | 201〜500 行 | 約 1 時間 | 許容 |
| L | 501〜1,000 行 | 約 2 時間 | 分割検討 |
| XL | 1,000 行超 | 3 時間以上 | **分割必須** |

### 9.2 大規模 PR の分割戦略

```
大規模 PR (1000行超)
  │
  ├── レイヤー分離可能？ → 分割: Infrastructure PR → Domain PR → Application PR
  │
  ├── 機能分離可能？ → 分割: Feature A PR + Feature B PR (並列)
  │
  └── 段階分離可能？ → 分割: リファクタ PR → 実装 PR → テスト PR (順次)
```

---

## 10. PR ライフサイクル管理

### 10.1 PR ステータスフロー

```
[Draft] ──► [Open / Ready for Review]
                │
                ▼
           [In Review]
                │
          ┌─────┴──────┐
          │            │
     [Changes      [Approved]
      Requested]       │
          │            ▼
          │         [Merged] ──► Issue Auto-Close
          │
          └──► 修正後再レビュー

[Open/In Review/Changes Requested] ──► [Closed] (却下・放棄)
```

### 10.2 PR の SLA

| 操作 | 目標時間 |
|---|---|
| 初回レビュー開始 | PR 作成後 24 時間以内 |
| レビュー完了（XS/S） | レビュー開始後 4 時間以内 |
| レビュー完了（M/L） | レビュー開始後 8 時間以内 |
| 修正対応 | 変更要求後 24 時間以内 |
| マージ（承認後） | 承認後 4 時間以内 |

### 10.3 Stale PR の管理

| 経過時間 | アクション |
|---|---|
| 7 日間更新なし | リマインダー通知 |
| 14 日間更新なし | エスカレーション通知 |
| 30 日間更新なし | 自動クローズ候補（手動確認後クローズ） |

---

## 11. PR 却下パターン

以下のパターンに該当する PR は却下（Changes Requested または Close）される。

| 却下パターン | 理由 | 対応方法 |
|---|---|---|
| Issue なしの変更 | ガバナンス違反 | Issue を作成してから再提出 |
| テストなしの機能追加 | 品質基準未達 | テストを追加して再提出 |
| セキュリティ違反のコード | セキュリティポリシー違反 | セキュリティ担当と協議 |
| CI 未通過のまま承認要求 | CI 整合性違反 | CI を修正してから再依頼 |
| タイトルフォーマット違反 | 統治規則違反 | タイトルを修正 |
| 変更行数 1,000 行超 | レビュー不能 | 分割して再提出 |
| main への直接コミット含む | ブランチ戦略違反 | ブランチを作り直す |
| ハードコードされたシークレット | セキュリティ致命的違反 | 即時クローズ・シークレットローテーション |

---

## 12. Agent Teams PR レビューフロー

### 12.1 AI レビューフロー

```
PR 作成
  │
  ▼
PR 規模・種別判定
  │
  ├── 小規模 PR（100行以下）
  │     └── SubAgent 単独レビュー → コメント投稿
  │
  └── 中〜大規模 PR
        ├── Security Agent レビュー（並列）
        ├── Quality Agent レビュー（並列）
        └── Performance Agent レビュー（並列）
              │
              ▼
        Team Lead Agent が結果を統合
              │
              ▼
        統合レビュー結果を GitHub PR にコメント投稿
        → Approve または Request Changes
```

### 12.2 AI レビュー観点

| Agent | レビュー観点 |
|---|---|
| Security Agent | 脆弱性、認証・認可、シークレット漏洩、OWASP 準拠 |
| Quality Agent | コード品質、命名、複雑度、テストカバレッジ、アーキテクチャ準拠 |
| Performance Agent | パフォーマンス影響、N+1 クエリ、メモリリーク、リソース効率 |
| Team Lead Agent | 統合評価、全体整合性、統治原則準拠 |

### 12.3 AI レビュー結果フォーマット

```markdown
## AI Review Summary

### Security Review
- Status: PASS / WARN / FAIL
- Findings: [具体的な指摘事項]

### Quality Review
- Status: PASS / WARN / FAIL
- Findings: [具体的な指摘事項]

### Performance Review
- Status: PASS / WARN / FAIL
- Findings: [具体的な指摘事項]

### Overall Assessment
- Risk Level: Low / Medium / High
- Recommendation: Approve / Request Changes
- Summary: [総合評価コメント]
```

---

## 13. セキュリティに関する PR の特別ルール

### 13.1 セキュリティ PR の要件

- タイトルに具体的な脆弱性情報を含めない（例: 「CVE-XXXX-YYYY の修正」は可、詳細内容は不可）
- PR 本文は最小限の情報に留める
- 詳細はセキュリティチームのみアクセス可能な場所に記録
- レビュアーはセキュリティ担当者を必ず含める（CODEOWNERS で自動設定）
- マージ後速やかに関連 Issue をクローズする

### 13.2 セキュリティ PR フロー

```
脆弱性発見
  │
  ▼
セキュリティ Issue 作成（非公開 / Private）
  │
  ▼
security/* ブランチ作成
  │
  ▼
修正実装
  │
  ▼
PR 作成（最小限の説明）
  │
  ▼
セキュリティレビュー（2 名承認必須）
  │
  ▼
CI 実行
  │
  ▼
マージ
  │
  ▼
セキュリティアドバイザリ公開（必要に応じて）
```

---

## 14. 関連ドキュメント

| ドキュメント | 参照先 |
|---|---|
| ブランチ戦略 | [BRANCH_STRATEGY.md](./BRANCH_STRATEGY.md) |
| CI/CD パイプラインアーキテクチャ | [CI_CD_PIPELINE_ARCHITECTURE.md](./CI_CD_PIPELINE_ARCHITECTURE.md) |
| Issue ワークフロー | [ISSUE_WORKFLOW_DEFINITION.md](./ISSUE_WORKFLOW_DEFINITION.md) |
| リポジトリ構成ガイドライン | [REPOSITORY_STRUCTURE_GUIDELINES.md](./REPOSITORY_STRUCTURE_GUIDELINES.md) |

---

*本ドキュメントは ServiceMatrix プロジェクトの統治原則に基づき管理される。*
*変更は Change Issue → PR → CI 検証 → 承認 のフローに従うこと。*
