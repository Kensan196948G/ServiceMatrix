# ブランチ戦略

ServiceMatrix Branch Strategy

Version: 2.0
Status: Active
Classification: Internal DevOps Document

---

## 1. はじめに

本ドキュメントは ServiceMatrix における Git ブランチ戦略を定義する。
ブランチ命名規則、保護ルール、WorkTree 連携、マージ戦略を明確にし、
並列開発における衝突ゼロと CI 整合性 100% を目指す。

---

## 2. ブランチ戦略の原則

1. **main ブランチは常にデプロイ可能な状態を維持する**
2. **すべての変更は機能ブランチで行い、PR を通じて main にマージする**
3. **main への直接 push は禁止する**
4. **ブランチ命名規則に従い、目的を明確にする**
5. **1 ブランチ = 1 Issue の対応関係を維持する**
6. **不要になったブランチは速やかに削除する**
7. **1 Agent = 1 ブランチ = 1 WorkTree（Agent Teams 時）**

---

## 3. ブランチモデル

ServiceMatrix は **GitHub Flow + リリースブランチ** を採用する。

```
main ──────────────────────────────────────────────────────► (常時デプロイ可能)
  │          │              │            │
  ├─ feature/42-dashboard   │            │
  │          │              │            │
  │          ├─ fix/87-sla  │            │
  │          │              │            │
  │          │              ├─ release/v1.0.0
  │          │              │            │
  │          │              │            ├─ hotfix/critical-auth
```

### 3.1 モデルの特徴

| 要素 | 説明 |
|---|---|
| トランク | `main` ブランチ（常時デプロイ可能） |
| 開発フロー | `feature/*` → PR → `main` |
| リリース管理 | `release/vX.Y.Z` ブランチで最終調整 |
| 緊急対応 | `hotfix/*` ブランチで即時修正 |
| セキュリティ対応 | `security/*` ブランチで非公開修正 |

---

## 4. ブランチ種別と命名規則

### 4.1 ブランチ種別一覧

| プレフィックス | 用途 | 派生元 | マージ先 | 直接 push |
|---|---|---|---|---|
| `main` | 本番相当・常時デプロイ可能状態 | - | - | **禁止** |
| `feature/` | 新機能開発 | `main` | `main` | 禁止（PR必須） |
| `fix/` | バグ修正 | `main` | `main` | 禁止（PR必須） |
| `docs/` | ドキュメント更新 | `main` | `main` | 禁止（PR必須） |
| `refactor/` | リファクタリング | `main` | `main` | 禁止（PR必須） |
| `ci/` | CI/CD 設定変更 | `main` | `main` | 禁止（PR必須） |
| `test/` | テスト追加・修正 | `main` | `main` | 禁止（PR必須） |
| `security/` | セキュリティ修正 | `main` | `main` | 禁止（PR必須） |
| `hotfix/` | 緊急修正（本番障害） | `main` | `main` | 禁止（PR必須） |
| `release/` | リリース準備 | `main` | `main` | 禁止（PR必須） |
| `chore/` | 依存更新・雑務 | `main` | `main` | 禁止（PR必須） |

### 4.2 命名フォーマット

```
{prefix}/{issue-number}-{short-description}
```

- `{prefix}`: ブランチ種別プレフィックス
- `{issue-number}`: 関連 GitHub Issue 番号
- `{short-description}`: kebab-case で 30 文字以内の説明

### 4.3 命名例

| 種別 | 例 |
|---|---|
| `main` | `main` |
| `feature/` | `feature/42-incident-dashboard` |
| `fix/` | `fix/87-sla-timer-off-by-one` |
| `docs/` | `docs/103-architecture-overview` |
| `refactor/` | `refactor/115-event-dispatcher` |
| `ci/` | `ci/120-add-security-scan` |
| `test/` | `test/130-incident-service-unit` |
| `security/` | `security/155-xss-prevention` |
| `hotfix/` | `hotfix/200-critical-auth-bypass` |
| `release/` | `release/v1.2.0` |
| `chore/` | `chore/170-update-dependencies` |

### 4.4 命名ルール

- 英小文字とハイフンのみ使用（`a-z`, `0-9`, `-`）
- アンダースコア、大文字、日本語は使用しない
- 説明部分は 30 文字以内
- Issue 番号は省略可能だが強く推奨

---

## 5. ブランチ構造図

### 5.1 GitHub Flow + リリースブランチ フロー

```
main ─────●─────────────────────────────●────────────●──►
          │                             │            │
          ├──► feature/42-dashboard     │            │
          │         │                  │            │
          │    commit, commit ──────────┤ PR #43     │
          │                            │            │
          ├──► fix/87-sla-timer        │            │
          │         │                  │            │
          │    commit ─────────────────┤ PR #88     │
          │                            │            │
          │                            └──► release/v1.0.0
          │                                    │
          │                               commit (version bump)
          │                               commit (CHANGELOG)
          │                                    │ PR release
          │                                    ▼
main ─────────────────────────────────────────●──► tag: v1.0.0
```

### 5.2 緊急 Hotfix フロー

```
main ─────●──────────────────────────●──►
          │                          │
          └──► hotfix/200-critical ──┘
                    │
               commit (fix)
                    │ PR (2名承認必須)
```

---

## 6. ブランチ保護ルール

### 6.1 main ブランチ保護設定

| 設定項目 | 値 | 理由 |
|---|---|---|
| Require pull request before merging | **有効** | PR レビュー必須 |
| Required number of approvals | **1 名** | 最低 1 名の承認 |
| Dismiss stale pull request approvals | **有効** | 追加コミット後は再承認必要 |
| Require status checks to pass | **有効** | CI 必須通過 |
| Required status checks | `markdown-lint`, `docs-validation`, `security-scan`, `unit-test` | 全チェック通過必須 |
| Require branches to be up to date before merging | **有効** | main との同期必須 |
| Require conversation resolution | **有効** | レビューコメント解決必須 |
| Restrict who can push to matching branches | **有効** | 管理者のみ直接 push（緊急時限定） |
| Allow force pushes | **無効** | Force push 完全禁止 |
| Allow deletions | **無効** | main ブランチ削除禁止 |

### 6.2 保護ルール適用フロー

```
PR作成
  │
  ▼
CI チェック実行 ──── 失敗 ──── 修正 → 再 push → CI 再実行
  │
  │ 成功
  ▼
レビュー ──── 変更要求 ──── 修正対応 → CI 再実行 → レビュー
  │
  │ 承認
  ▼
main と同期確認 ──── 未同期 ──── リベース → CI 再実行
  │
  │ 同期済
  ▼
全コメント解決確認 ──── 未解決 ──── 解決対応
  │
  │ 全解決
  ▼
マージ実行（Squash Merge）
```

### 6.3 セキュリティ・Hotfix ブランチの特別ルール

| ブランチ種別 | 必要承認数 | 追加要件 |
|---|---|---|
| `security/*` | 2 名 | セキュリティ担当必須 |
| `hotfix/*` | 2 名 | テックリード承認必須 |
| `release/*` | 2 名 | アーキテクト + テックリード |

---

## 7. WorkTree 活用方針

### 7.1 WorkTree の原則

- **1 機能 = 1 WorkTree**: 機能開発は独立した WorkTree で実施
- **1 Agent = 1 WorkTree**: 各 Agent は独立した WorkTree で作業
- **同一ファイル同時編集禁止**: 異なる WorkTree で同一ファイルを編集しない
- **main 直編集禁止**: WorkTree は必ず機能ブランチに紐付ける

### 7.2 WorkTree 配置構造

```
.claude/
└── worktrees/
    ├── wt-feat-42/      → feature/42-incident-dashboard
    ├── wt-fix-87/       → fix/87-sla-timer-off-by-one
    ├── wt-docs-103/     → docs/103-architecture-overview
    └── wt-release-1/    → release/v1.0.0
```

詳細は [WORKTREE_STRATEGY.md](./WORKTREE_STRATEGY.md) を参照。

---

## 8. Agent Teams 用ブランチ管理

### 8.1 Agent Teams ブランチ割当ルール

Agent Teams 起動時、Team Lead は以下を実施する：

1. 親 Issue を確認し、作業範囲を分割する
2. 各 Agent に個別のブランチを割り当てる
3. 各 Agent は割り当てられたブランチに対応する WorkTree を使用する
4. Agent 間の依存関係を事前に明確にする

### 8.2 Agent Teams ブランチ構成例

```
Issue #42: インシデント管理機能の実装
├── feature/42-backend-api    → Backend Agent 担当
├── feature/42-frontend-ui    → Frontend Agent 担当
├── feature/42-test-coverage  → Test Agent 担当
└── feature/42-security-review → Security Agent 担当（レビューのみ）
```

### 8.3 Agent Teams ブランチ統合フロー

```
feature/42-backend-api  ──── PR #43 ──── main
feature/42-frontend-ui  ──── PR #44 ──── main  (PR #43 マージ後)
feature/42-test-coverage ─── PR #45 ──── main  (PR #43, #44 マージ後)
```

統合順序は依存関係に基づき Team Lead が決定する。

---

## 9. マージ戦略

### 9.1 Squash Merge（標準）

ServiceMatrix では **Squash Merge** を標準マージ戦略として採用する。

**理由:**
- main ブランチの履歴がクリーンに保たれる
- 1 PR = 1 コミットで追跡が容易
- WIP コミットや試行錯誤の履歴が main に混入しない
- Issue 番号との対応が明確

**Squash コミットメッセージフォーマット:**

```
{type}(#{issue-number}): {short-description}

{detailed-description}

Closes #{issue-number}
```

**例:**

```
feat(#42): インシデントダッシュボードを追加

- SLA 状況ウィジェットを実装
- インシデントトレンドグラフを実装
- 優先度別フィルタリングを実装

Closes #42
```

### 9.2 マージ戦略の使い分け

| マージ方式 | 使用場面 | 設定 |
|---|---|---|
| Squash Merge | 通常の機能開発・バグ修正・ドキュメント | デフォルト |
| Merge Commit | リリースブランチのマージ | 手動選択（タグ付与時） |
| Rebase Merge | 使用しない | 無効 |

---

## 10. リリースブランチ戦略

### 10.1 リリースフロー

```
main ─────●──────●──────●─────────────────────●──► tag: v1.0.0
          (Feature A) (Feature B) (Fix C)      │
                                               │
                              release/v1.0.0 ──┘
                                  │
                             commit: version bump
                             commit: CHANGELOG
                             commit: final validation
```

### 10.2 バージョニング（SemVer）

ServiceMatrix は Semantic Versioning を採用する。

```
MAJOR.MINOR.PATCH
```

| バージョン要素 | 変更タイミング | 例 |
|---|---|---|
| MAJOR | 後方互換性のない変更 | `1.0.0 → 2.0.0` |
| MINOR | 後方互換性のある機能追加 | `1.0.0 → 1.1.0` |
| PATCH | バグ修正のみ | `1.0.0 → 1.0.1` |

### 10.3 リリース手順

1. `release/vX.Y.Z` ブランチを `main` から作成
2. バージョン番号を更新（`package.json` / `pyproject.toml`）
3. `CHANGELOG.md` を更新
4. 最終検証を実施
5. PR を作成し、2 名のレビュー・承認を受ける
6. `main` に Merge Commit でマージ
7. タグ `vX.Y.Z` を作成
8. GitHub Release を作成
9. リリースブランチを削除

---

## 11. ブランチの寿命管理

| ブランチ種別 | 推奨寿命 | 最大寿命 | 超過時アクション |
|---|---|---|---|
| `feature/*` | 1〜5 日 | 2 週間 | リベース促進 / 分割検討 |
| `fix/*` | 数時間〜1 日 | 3 日 | 優先対応 |
| `docs/*` | 1〜3 日 | 1 週間 | 早期マージ |
| `refactor/*` | 1〜5 日 | 2 週間 | 分割検討 |
| `ci/*` | 数時間〜1 日 | 3 日 | 早期マージ |
| `security/*` | 数時間 | 1 日 | 最優先対応 |
| `hotfix/*` | 数時間 | 1 日 | 最優先対応 |
| `release/*` | 1〜3 日 | 1 週間 | リリース実行 |

---

## 12. ブランチクリーンアップ

### 12.1 自動クリーンアップルール

| 条件 | アクション |
|---|---|
| PR マージ後 | ソースブランチ自動削除（GitHub 設定） |
| 30 日間更新なし | 自動通知 → 手動削除判断 |
| 90 日間更新なし | 自動アーカイブ警告 |

### 12.2 クリーンアップ手順

```bash
# マージ済みブランチの一覧表示
git branch --merged main | grep -v "^\* main$"

# マージ済みブランチの削除（ローカル）
git branch --merged main | grep -v "^\* main$" | xargs git branch -d

# リモートのブランチ削除
git push origin --delete {branch-name}

# WorkTree のクリーンアップ
git worktree list
git worktree remove .claude/worktrees/{worktree-name}
git worktree prune
```

---

## 13. コンフリクト防止策

### 13.1 予防措置

1. **細粒度ブランチ**: ブランチの変更範囲を最小限にする
2. **頻繁な同期**: main の変更を定期的にブランチに取り込む（`git rebase main`）
3. **担当領域分離**: Agent Teams では担当ファイルを事前に分離する
4. **早期マージ**: ブランチの寿命を短く保つ
5. **事前調整**: 同一ファイルへの変更が必要な場合は事前に調整する

### 13.2 コンフリクト発生時の対応

```
コンフリクト検出
  │
  ├── 軽微なコンフリクト ──── 手動解決 ──── テスト実行 ──── CI確認
  │
  ├── 中程度 ──── チームリードに相談 ──── 合意形成 ──── 解決
  │
  └── 重大なコンフリクト ──── 関係者会議 ──── 設計見直し ──── 解決
```

---

## 14. 関連ドキュメント

| ドキュメント | 参照先 |
|---|---|
| Pull Request ポリシー | [PULL_REQUEST_POLICY.md](./PULL_REQUEST_POLICY.md) |
| WorkTree 戦略 | [WORKTREE_STRATEGY.md](./WORKTREE_STRATEGY.md) |
| CI/CD パイプラインアーキテクチャ | [CI_CD_PIPELINE_ARCHITECTURE.md](./CI_CD_PIPELINE_ARCHITECTURE.md) |
| Issue ワークフロー | [ISSUE_WORKFLOW_DEFINITION.md](./ISSUE_WORKFLOW_DEFINITION.md) |

---

*本ドキュメントは ServiceMatrix プロジェクトの統治原則に基づき管理される。*
*変更は Change Issue → PR → CI 検証 → 承認 のフローに従うこと。*
