# Agent Teams 構成定義（Agent Teams Structure）

Version: 1.0
Status: Active
Classification: Internal / Architecture
Owner: Service Governance Authority
Last Updated: 2026-03-02

---

## 1. 目的

本文書は、ServiceMatrix における Agent Teams の構成、役割分担、
ライフサイクル、および運用規則を定義する。

Agent Teams は ClaudeCode の並列実行モデルであり、
複数の AI エージェントが協調してタスクを遂行する仕組みである。

---

## 2. Agent Teams の概念

### 2.1 基本構成

Agent Teams は **Lead + Members** の階層構造で構成される。

```
┌─────────────────────────────────────────┐
│            Agent Teams                   │
│                                          │
│  ┌──────────┐                           │
│  │   Lead   │ ← チーム統括・タスク配分   │
│  └────┬─────┘                           │
│       │                                  │
│  ┌────┴────────────────────┐            │
│  │    │    │    │          │            │
│  ▼    ▼    ▼    ▼          ▼            │
│ [M1] [M2] [M3] [M4]  ... [Mn]          │
│                                          │
│ M = Member Agent                        │
└─────────────────────────────────────────┘
```

### 2.2 Lead Agent の責務

Lead Agent は以下の責務を持つ。

1. **タスク分解**: 受領したタスクを各 Member に適切に分配する
2. **進捗管理**: TaskList を用いて全体の進捗を追跡する
3. **品質管理**: Member の成果物を統合・検証する
4. **コンフリクト防止**: ファイル競合が発生しないよう制御する
5. **ライフサイクル管理**: Member の spawn / shutdown を管理する
6. **報告**: ユーザーへの進捗報告・完了報告を行う

### 2.3 Member Agent の責務

Member Agent は以下の責務を持つ。

1. **割当タスクの実行**: Lead から割り当てられたタスクを遂行する
2. **WorkTree 内での作業**: 自身に割り当てられた WorkTree 内でのみ作業する
3. **進捗報告**: SendMessage を用いて Lead に進捗を報告する
4. **完了通知**: タスク完了時に TaskUpdate で状態を更新する
5. **統治規則遵守**: AI_GOVERNANCE_POLICY に従って行動する

---

## 3. チーム編成テンプレート

### 3.1 機能開発チーム

中〜大規模の機能追加に適用する。

| 役割 | Agent 名 | 担当領域 | WorkTree |
|------|----------|----------|----------|
| Lead | team-lead | 全体統括・統合 | feature/main |
| Backend | backend-dev | API・ロジック実装 | feature/backend |
| Frontend | frontend-dev | UI・表示層実装 | feature/frontend |
| Test | test-engineer | テスト設計・実装 | feature/test |
| Security | security-reviewer | セキュリティレビュー | feature/security |

**適用条件:**

- 複数レイヤーにまたがる変更
- API + UI の同時開発
- 新機能追加（見積もり: 中規模以上）

### 3.2 レビューチーム

多角的コードレビューに適用する。

| 役割 | Agent 名 | 担当領域 | WorkTree |
|------|----------|----------|----------|
| Lead | review-lead | レビュー統括・判定 | review/main |
| Security | security-auditor | セキュリティ脆弱性検査 | review/security |
| Performance | perf-reviewer | 性能・効率性レビュー | review/perf |
| Coverage | coverage-analyst | テスト網羅性分析 | review/coverage |
| Architecture | arch-reviewer | 構造・設計整合性レビュー | review/arch |

**適用条件:**

- Pull Request の多角的レビュー
- リリース前最終レビュー
- セキュリティ監査対応

### 3.3 デバッグチーム

複雑な障害調査に適用する。

| 役割 | Agent 名 | 担当領域 | WorkTree |
|------|----------|----------|----------|
| Lead | debug-lead | 調査統括・仮説管理 | debug/main |
| Hypothesis-A | debugger-a | 仮説 A の検証 | debug/hypo-a |
| Hypothesis-B | debugger-b | 仮説 B の検証 | debug/hypo-b |
| Log-Analyst | log-analyst | ログ解析・証跡収集 | debug/logs |

**適用条件:**

- 原因不明の障害調査
- 複数仮説の並列検証が必要な場合
- 再現困難な間欠的障害

### 3.4 ドキュメントチーム

大規模ドキュメント整備に適用する。

| 役割 | Agent 名 | 担当領域 | WorkTree |
|------|----------|----------|----------|
| Lead | docs-lead | 文書統括・整合確認 | docs/main |
| Writer-A | docs-writer-a | 指定範囲の文書作成 | docs/section-a |
| Writer-B | docs-writer-b | 指定範囲の文書作成 | docs/section-b |
| Reviewer | docs-reviewer | 文書レビュー・校正 | docs/review |

**適用条件:**

- 複数文書の同時作成
- 大規模なドキュメント改訂
- 監査対応用の文書整備

---

## 4. メンバー間コミュニケーション規則

### 4.1 通信手段

Agent Teams 内の通信は以下の手段を用いる。

| 手段 | 用途 | 方向 |
|------|------|------|
| SendMessage (type: message) | 個別通信 | 1対1 |
| SendMessage (type: broadcast) | 全体通知 | 1対全（使用制限あり） |
| TaskCreate / TaskUpdate | タスク状態管理 | 全員参照可能 |
| TaskList | 進捗確認 | 全員参照可能 |

### 4.2 コミュニケーション原則

1. **broadcast は最小限**: broadcast はコストが高いため、緊急時・全体影響時のみ使用する
2. **進捗は TaskUpdate で**: 口頭報告よりもタスク状態更新を優先する
3. **ブロッキング報告は即時**: 作業がブロックされた場合は即座に Lead に報告する
4. **完了報告は必須**: タスク完了時は必ず Lead に SendMessage で報告する
5. **質問は具体的に**: 抽象的な質問を避け、ファイル名・行番号を含めて質問する

### 4.3 禁止されるコミュニケーション

- Lead を経由しない Member 間の直接的な作業指示
- タスクシステムを経由しない非公式な作業依頼
- 承認なきファイル共有（WorkTree 境界を越える変更）

---

## 5. WorkTree との連携

### 5.1 基本原則

> 1 Agent = 1 WorkTree

各 Member Agent は専用の Git WorkTree 内でのみ作業する。
これにより以下を保証する。

- **ファイル競合の防止**: 物理的に異なるディレクトリで作業
- **変更の追跡性**: 各 Agent の変更が独立したブランチに記録
- **ロールバックの容易性**: 問題発生時に特定 Agent の変更のみ取り消し可能

### 5.2 WorkTree 命名規則

```
.claude/worktrees/{team-type}/{role-name}
```

例:

```
.claude/worktrees/feature/backend-dev
.claude/worktrees/feature/frontend-dev
.claude/worktrees/review/security-auditor
.claude/worktrees/debug/hypothesis-a
```

### 5.3 ブランチ命名規則

```
{team-type}/{role-name}/{task-description}
```

例:

```
feature/backend-dev/add-auth-api
feature/frontend-dev/implement-login-ui
review/security-auditor/audit-auth-module
debug/hypothesis-a/investigate-memory-leak
```

### 5.4 WorkTree ライフサイクル

```
Agent Spawn
  │
  ├─ WorkTree 作成（EnterWorktree）
  │   ├─ 新規ブランチ作成（HEAD ベース）
  │   └─ 作業ディレクトリ切替
  │
  ├─ 作業実行
  │   ├─ ファイル編集
  │   ├─ テスト実行
  │   └─ コミット（承認後）
  │
  ├─ 成果物統合
  │   ├─ Lead による統合レビュー
  │   └─ メインブランチへの merge（承認後）
  │
  └─ WorkTree 削除
      └─ Agent Shutdown 時に自動プロンプト
```

---

## 6. Spawn / Shutdown ライフサイクル

### 6.1 Spawn（起動）

Agent Teams の spawn は以下のフローに従う。

```
1. Lead がチーム構成を提案
   ├─ チーム構成（役割・人数）
   ├─ WorkTree 名
   ├─ ブランチ名
   ├─ 影響範囲
   └─ 予想トークンコスト

2. 人間による承認

3. Lead が各 Member を spawn
   ├─ タスク割当（TaskCreate）
   ├─ コンテキスト共有
   └─ 制約条件伝達

4. 各 Member が作業開始
   ├─ WorkTree 進入
   ├─ タスク状態更新（in_progress）
   └─ 作業実行
```

### 6.2 Shutdown（停止）

Shutdown は **Lead Agent のみ** が実行できる。

```
1. Lead がタスク完了を確認
   ├─ TaskList で全タスク完了を確認
   └─ 成果物の統合完了を確認

2. Lead が各 Member に shutdown_request を送信
   ├─ Member が approve → プロセス終了
   └─ Member が reject → 理由確認後再調整

3. Lead が最終報告を作成
   ├─ 完了タスク一覧
   ├─ 成果物一覧
   └─ 残課題（あれば）

4. Lead が自身を shutdown
```

### 6.3 異常終了時の対応

Member Agent が異常終了した場合:

1. Lead が状態を確認する
2. 未完了タスクを特定する
3. 別の Member に再割当するか、新規 Member を spawn する
4. WorkTree の状態を確認し、必要に応じてクリーンアップする

---

## 7. トークンコスト管理指針

### 7.1 コスト見積もり

Agent Teams spawn 前に以下を見積もる。

| 項目 | 見積もり基準 |
|------|-------------|
| Member 数 | タスクの並列度に応じて最小限にする |
| タスク複雑度 | 各 Member の予想ターン数 |
| コンテキスト量 | 各 Member に渡す情報量 |

### 7.2 コスト最適化原則

1. **最小チーム原則**: 必要最小限の Member 数で構成する
2. **SubAgent 優先**: 単純タスクは Agent Teams ではなく SubAgent を使用する
3. **コンテキスト最小化**: 各 Member には必要な情報のみ共有する
4. **早期終了**: タスク完了次第、Member を速やかに shutdown する
5. **再利用回避**: 完了した Member の再利用より新規 spawn を優先する（コンテキスト肥大化防止）

### 7.3 コスト判断基準

| タスク規模 | 推奨実行方式 | 理由 |
|-----------|-------------|------|
| 単一ファイル修正 | SubAgent | コンテキスト共有で十分 |
| 2-3 ファイル修正 | SubAgent or 単独 Agent | WorkTree 分離不要 |
| 複数レイヤー変更 | Agent Teams（3-4 名） | 並列効率・競合防止 |
| 大規模リファクタ | Agent Teams（4-6 名） | 分割統治が必要 |

---

## 8. 同一ファイル同時編集の禁止

### 8.1 原則

> 同一ファイルを複数の Agent が同時に編集してはならない。

### 8.2 競合防止メカニズム

1. **WorkTree による物理分離**: 各 Agent は独立した作業ディレクトリを持つ
2. **タスク設計による論理分離**: Lead がタスクを設計する際にファイル境界を明確にする
3. **依存関係管理**: TaskUpdate の addBlockedBy / addBlocks でタスク間依存を明示する

### 8.3 競合発生時の対応

万が一、マージ時にファイル競合が発生した場合:

1. Lead が競合を検知する
2. 関連する Member の変更意図を確認する
3. 手動マージ案を策定する
4. 人間に承認を求める
5. 承認後にマージを実行する

---

## 9. main ブランチ保護

### 9.1 原則

> main ブランチへの直接変更は禁止する。

### 9.2 main への反映フロー

```
Member WorkTree Branch
  │
  └─ PR → Feature Branch（Lead が統合）
              │
              └─ PR → main（人間承認必須）
```

すべての main への変更は Pull Request を経由し、CI 検証と人間承認を通過しなければならない。

---

## 10. 関連文書

- `AI_GOVERNANCE_POLICY.md` - AI 統治ポリシー
- `SUBAGENT_ROLE_DEFINITION.md` - SubAgent 役割定義
- `AUTO_REPAIR_CONTROL_MODEL.md` - 自動修復統制モデル
- `AI_DECISION_LOGGING_MODEL.md` - AI 意思決定ログモデル
- `AI_AUTONOMY_LEVEL_MATRIX.md` - AI 自律レベルマトリクス

---

以上
