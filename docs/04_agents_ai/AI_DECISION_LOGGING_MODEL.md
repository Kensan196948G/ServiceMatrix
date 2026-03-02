# AI決定ログモデル（AI Decision Logging Model）

Version: 2.0
Status: Active
Classification: Internal / Audit
Owner: Service Governance Authority
Compliance: ITIL 4 / ISO/IEC 20000 / J-SOX / GDPR考慮
Last Updated: 2026-03-02

---

## 1. 目的

本文書は、ServiceMatrix における AI エージェントのすべての意思決定を
記録・保存・照会するためのログモデルを定義する。

すべての AI 判断は追跡可能でなければならない。
本モデルはその追跡可能性・証拠性・監査適合性を構造的に保証する。

---

## 2. ログ記録対象のAI決定種別

### 2.1 対象決定種別一覧

| decision_type | 説明 | 具体例 |
|--------------|------|-------|
| `priority_assessment` | 優先度判定 | Issueの優先度スコアリング・SLA影響度判定 |
| `risk_evaluation` | リスク評価 | 変更リスクスコア算出・影響範囲分析 |
| `repair_proposal` | 修復提案 | CI失敗修復案の生成・複数オプション提示 |
| `analysis_result` | 分析結果 | コード分析・セキュリティスキャン・依存関係調査 |
| `auto_repair` | 自動修復実行 | 低リスクCI失敗の自動修復実行 |
| `review_judgment` | レビュー判定 | コードレビュー・PRレビュー・品質評価 |
| `approval_request` | 承認要求 | commit/push/merge の承認要求 |
| `delegation` | タスク委任 | SubAgent・Agent Teamsへのタスク委任 |
| `escalation` | エスカレーション | 人間への問題エスカレーション判断 |
| `rollback` | ロールバック判断 | 自動修復のロールバック実行 |
| `design_proposal` | 設計提案 | アーキテクチャ提案・設計改善提案 |
| `classification` | 分類判定 | Issueラベル付け・カテゴリ分類 |

### 2.2 記録優先度

| 優先度 | 対象 | 理由 |
|-------|------|------|
| 必須 | 自動修復・承認要求・エスカレーション・ロールバック | 直接的なシステム変更を伴う |
| 必須 | リスク評価・設計提案 | 意思決定への影響が大きい |
| 推奨 | 分析結果・レビュー判定 | 監査証跡として有用 |
| 任意 | 単純分類・優先度判定（低リスク） | コスト対効果で判断 |

---

## 3. ログスキーマ定義

### 3.1 完全スキーマ

```json
{
  "decision_id": "dec-20260302-001",
  "timestamp": "2026-03-02T14:30:00+09:00",
  "agent_type": "main_session | team_lead | team_member | subagent",
  "agent_id": "main-session-001",
  "session_id": "sess-20260302-001",
  "decision_type": "priority_assessment | risk_evaluation | repair_proposal | ...",
  "autonomy_level": "L0 | L1 | L2 | L3",
  "input_context": {
    "trigger": "CI失敗・Issueイベント・ユーザー要求など",
    "source": "GitHub Actions | GitHub Issues | User Input",
    "target_resource": "対象リソースパスまたはIssue番号",
    "relevant_data": "判断に使用したデータの要約（PII除外済み）"
  },
  "decision": {
    "summary": "決定内容の1文要約",
    "details": "決定内容の詳細説明",
    "options_considered": [
      {
        "option_id": "option-1",
        "description": "選択肢1の説明",
        "pros": ["利点1"],
        "cons": ["欠点1"],
        "selected": true
      }
    ],
    "selected_option": "option-1"
  },
  "confidence": 0.92,
  "rationale": "判断の根拠・論理的説明（人間が理解できる自然言語）",
  "risk_score": 0.15,
  "risk_level": "Negligible | Low | Medium | High | Critical",
  "outcome": {
    "status": "pending | approved | rejected | executed | failed | rolled_back",
    "executed_at": "2026-03-02T14:35:00+09:00",
    "result_summary": "実行結果の要約",
    "side_effects": "副作用・想定外の影響（あれば）"
  },
  "approval": {
    "required": true,
    "requested_at": "2026-03-02T14:30:05+09:00",
    "approved_by": "user-001",
    "approved_at": "2026-03-02T14:34:00+09:00",
    "approval_channel": "GitHub Issues | Direct | Automated"
  },
  "affected_resources": [
    "src/api/auth.py",
    "tests/test_auth.py"
  ],
  "tags": ["security", "ci", "lint"],
  "parent_decision_id": null,
  "child_decision_ids": [],
  "compliance_flags": {
    "j_sox_relevant": false,
    "security_relevant": true,
    "gdpr_relevant": false,
    "data_contains_pii": false
  }
}
```

### 3.2 フィールド詳細定義

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|-----|------|
| `decision_id` | string | 必須 | グローバル一意識別子 `dec-{YYYYMMDD}-{seq}` |
| `timestamp` | ISO 8601 | 必須 | 判断が行われた日時（タイムゾーン付き） |
| `agent_type` | enum | 必須 | エージェント種別 |
| `agent_id` | string | 必須 | エージェント識別子 `{context}-{role}-{instance}` |
| `session_id` | string | 必須 | セッション識別子 `sess-{YYYYMMDD}-{seq}` |
| `decision_type` | enum | 必須 | 決定種別（3.1参照） |
| `autonomy_level` | enum | 必須 | 判断時の自律度レベル（L0-L3） |
| `input_context` | object | 必須 | 判断に使用したコンテキスト情報 |
| `decision` | object | 必須 | 判断内容の詳細 |
| `confidence` | float 0.0-1.0 | 必須 | AIの判断確信度 |
| `rationale` | string | 必須 | 判断根拠の自然言語説明 |
| `risk_score` | float 0.0-1.0 | 条件付き | リスク評価を伴う判断で必須 |
| `risk_level` | enum | 条件付き | リスク評価を伴う判断で必須 |
| `outcome` | object | 必須 | 判断の実行結果 |
| `approval` | object | 条件付き | 承認が必要な判断で必須 |
| `affected_resources` | array | 必須 | 影響を受けるリソースのパス一覧 |
| `tags` | array | 推奨 | 分類・検索用タグ |
| `parent_decision_id` | string | 推奨 | 連鎖判断の場合の親ID |
| `compliance_flags` | object | 必須 | J-SOX・GDPR等の適用フラグ |

---

## 4. 証拠保全要件

### 4.1 改ざん防止要件

| 要件 | 実装方法 |
|------|---------|
| 追記のみ許可 | ログファイルへの上書き・削除を禁止する |
| ハッシュ検証 | 日次でSHA-256ハッシュを計算し別ファイルに保存する |
| Gitコミット記録 | ログファイルをGitリポジトリで管理し変更履歴を保持する |
| タイムスタンプ整合性 | 全ログエントリのタイムスタンプはシステム時刻に基づく |
| 証拠チェーン | 連鎖判断は `parent_decision_id` で追跡可能にする |

### 4.2 保存期間

| ログ種別 | 保持期間 | 根拠 | 保持後の処理 |
|---------|---------|------|------------|
| 通常判断ログ | 90日 | 運用監視要件 | gzip圧縮アーカイブ |
| 自動修復ログ | 1年 | ITIL変更管理要件 | gzip圧縮アーカイブ |
| 承認記録 | 永続 | J-SOX監査証跡要件 | 保持継続 |
| 設計判断ログ | 永続 | 設計決定の追跡 | 保持継続 |
| セキュリティ判断 | 5年 | セキュリティ監査要件 | gzip圧縮アーカイブ |
| ロールバック記録 | 1年 | インシデント追跡要件 | gzip圧縮アーカイブ |
| エスカレーション記録 | 1年 | 問題管理要件 | gzip圧縮アーカイブ |

### 4.3 証拠保全手順（監査時）

```
Step 1: 対象期間・対象ログの特定
  ├─ 監査依頼書から対象期間を確認する
  └─ 該当するログファイルを一覧化する

Step 2: ログファイルのハッシュ値算出
  ├─ sha256sum .claude/logs/decisions/*.jsonl > evidence_hash.txt
  └─ ハッシュ値の正当性を保存済みハッシュと照合する

Step 3: 証拠ファイルのコピー
  ├─ 対象ログファイルを docs/15_audit_evidence/YYYY-MM/ にコピーする
  └─ ハッシュ値ファイルも同ディレクトリにコピーする

Step 4: 証拠保全記録の作成
  ├─ 保全日時・保全者・対象ファイル一覧を記録する
  └─ 保全記録ファイルを docs/15_audit_evidence/ に保存する
```

---

## 5. 監査用クエリパターン

### 5.1 基本クエリ

```bash
# 特定日の全決定ログを取得
cat .claude/logs/decisions/ai_decisions_2026-03-02.jsonl | jq '.'

# 高リスク判断の抽出（riskスコア0.6以上）
cat .claude/logs/decisions/ai_decisions_2026-03-02.jsonl \
  | jq 'select(.risk_score >= 0.6)'

# 特定エージェントの判断履歴
cat .claude/logs/decisions/ai_decisions_2026-03-02.jsonl \
  | jq 'select(.agent_id == "team-lead-001")'

# 承認が必要だった判断の一覧
cat .claude/logs/decisions/ai_decisions_2026-03-02.jsonl \
  | jq 'select(.approval.required == true)'

# 自動修復の判断一覧
cat .claude/logs/decisions/ai_decisions_2026-03-02.jsonl \
  | jq 'select(.decision_type == "auto_repair")'

# 特定ファイルに関連する判断
cat .claude/logs/decisions/ai_decisions_2026-03-02.jsonl \
  | jq 'select(.affected_resources[] | contains("src/auth.py"))'

# J-SOX関連判断の抽出
cat .claude/logs/decisions/ai_decisions_2026-03-02.jsonl \
  | jq 'select(.compliance_flags.j_sox_relevant == true)'
```

### 5.2 集計クエリ

```bash
# 日次判断件数の集計
cat .claude/logs/decisions/ai_decisions_2026-03-02.jsonl \
  | jq -s 'length'

# decision_type別の件数
cat .claude/logs/decisions/ai_decisions_2026-03-02.jsonl \
  | jq -s 'group_by(.decision_type) | map({type: .[0].decision_type, count: length})'

# 平均確信度
cat .claude/logs/decisions/ai_decisions_2026-03-02.jsonl \
  | jq -s '[.[].confidence] | add / length'

# 承認率（承認が必要だった判断のうち承認された割合）
cat .claude/logs/decisions/ai_decisions_2026-03-02.jsonl \
  | jq -s '[.[] | select(.approval.required == true)] | {total: length, approved: [.[] | select(.approval.approved_by != null)] | length}'
```

### 5.3 監査レポート生成

```bash
# 週次監査レポート（特定週の判断サマリー）
for f in .claude/logs/decisions/ai_decisions_2026-03-0*.jsonl; do
  cat "$f"
done | jq -s '
  {
    total_decisions: length,
    by_type: (group_by(.decision_type) | map({key: .[0].decision_type, value: length}) | from_entries),
    high_risk: [.[] | select(.risk_score >= 0.6)] | length,
    approvals_required: [.[] | select(.approval.required == true)] | length,
    auto_repairs: [.[] | select(.decision_type == "auto_repair")] | length,
    avg_confidence: ([.[].confidence] | add / length)
  }
'
```

---

## 6. AIバイアス検出のためのログ分析方針

### 6.1 バイアス検出対象

| バイアス種別 | 検出方法 | 対応 |
|------------|---------|------|
| 確信度過信バイアス | 高確信度判断の事後正確率追跡 | 確信度キャリブレーション見直し |
| 特定エージェント偏重 | エージェント別判断頻度の偏り分析 | 委任ロジックの見直し |
| リスク過小評価傾向 | 「Low」評価後のインシデント発生率 | リスクスコア算出ロジック見直し |
| 反復パターンバイアス | 同種判断の単調な繰り返し検出 | 多様な判断アプローチ導入 |
| ラベル付けバイアス | 特定ラベルへの集中傾向 | ラベル分布の均衡性確認 |

### 6.2 分析実施スケジュール

| 分析項目 | 頻度 | 担当 |
|---------|------|------|
| 確信度 vs 正確率の相関 | 月次 | Service Governance Authority |
| リスク評価後のインシデント追跡 | 月次 | サービスオーナー |
| エージェント別パフォーマンス比較 | 四半期 | Service Governance Authority |
| バイアスパターン総合レビュー | 半期 | 監査担当 |

---

## 7. GDPR・プライバシー考慮事項

### 7.1 個人情報の取り扱い

ServiceMatrixのAI決定ログには、以下のプライバシー保護を適用する。

| 項目 | 方針 |
|------|------|
| PII（個人識別情報）の記録 | `input_context.relevant_data` にPIIを含めない |
| ユーザーID記録 | 承認者等のIDは記録するが最小限に留める |
| データ最小化原則 | 判断に必要なコンテキストのみ記録する |
| GDPRフラグ | `compliance_flags.gdpr_relevant` で管理する |
| 削除要求への対応 | PIIを含むログは個人特定不能な形に変換後保持 |
| 国外転送制限 | ログデータは国内ストレージにのみ保存する |

### 7.2 データ最小化チェックリスト

ログ記録前に以下を確認する。

- [ ] `input_context` にメールアドレス・氏名・電話番号が含まれていないか
- [ ] `rationale` に個人を特定できる情報が含まれていないか
- [ ] `decision.details` にユーザーの個人情報が含まれていないか
- [ ] `affected_resources` のパスが個人情報ファイルを指していないか

---

## 8. ログ保存ディレクトリ構造

```
.claude/
└── logs/
    ├── decisions/
    │   ├── ai_decisions_2026-03-01.jsonl
    │   ├── ai_decisions_2026-03-02.jsonl
    │   └── hashes/
    │       ├── ai_decisions_2026-03-01.sha256
    │       └── ai_decisions_2026-03-02.sha256
    ├── repairs/
    │   └── repair_log_2026-03-02.jsonl
    ├── approvals/
    │   └── approval_log_2026-03-02.jsonl
    ├── rollbacks/
    │   └── rollback_log_2026-03-02.jsonl
    └── escalations/
        └── escalation_log_2026-03-02.jsonl
```

---

## 9. 関連文書

- `AI_GOVERNANCE_POLICY.md` - AI統治ポリシー
- `AGENT_TEAMS_STRUCTURE.md` - Agent Teams構成定義
- `AUTO_REPAIR_CONTROL_MODEL.md` - 自動修復制御モデル
- `AI_AUTONOMY_LEVEL_MATRIX.md` - AI自律度レベルマトリックス
- `docs/15_audit_evidence/` - 監査証跡保存ディレクトリ

---

以上
