# 通知モデル定義

**ドキュメント番号**: SM-UI-003
**バージョン**: 2.0
**分類**: UI/UX設計仕様 / 通知設計
**作成日**: 2026-03-02
**最終更新日**: 2026-03-02
**準拠規格**: ITIL 4 / ISO/IEC 20000 / J-SOX
**ステータス**: 承認済み

---

## 1. 目的と適用範囲

### 1.1 目的

本ドキュメントは、ServiceMatrixにおけるすべての通知の設計モデルを定義する。
通知の種別・チャネル・優先度・表示方法・既読管理・ユーザーカスタマイズ設定を規定し、
特にAI生成通知の透明性確保（透明性原則）を設計の中核に置く。

### 1.2 設計原則

| 原則 | 説明 |
|---|---|
| 透明性 | AI生成通知は必ずその旨を明示する |
| 重要度の明確化 | 通知優先度は統一された基準で決定する |
| 受信者制御 | ユーザーは低優先度通知のオプトアウトが可能 |
| 監査証跡 | 全通知の配信・既読状態を記録する |
| 重複排除 | 同一イベントの重複通知を防止する |

---

## 2. 通知種別定義

### 2.1 システム通知（System Notification）

**概要**: ServiceMatrixシステム自体が生成する運用上の通知

| 通知コード | 説明 | トリガー | 優先度 |
|---|---|---|---|
| SYS-001 | インシデント新規作成 | インシデント登録時 | 優先度依存（P1=Critical、P4=Low） |
| SYS-002 | インシデントステータス変更 | ステータス遷移時 | Medium |
| SYS-003 | 変更リクエスト承認待ち | RFC承認待ち状態遷移時 | High |
| SYS-004 | 変更実施日到来 | 実施予定24時間前 | High |
| SYS-005 | 変更実施完了/失敗 | 変更完了/失敗時 | High |
| SYS-006 | 問題管理ステータス変更 | 問題ステータス遷移時 | Medium |
| SYS-007 | サービスリクエスト完了 | リクエスト完了時 | Low |
| SYS-008 | 担当者アサイン | 担当者変更時 | Medium |
| SYS-009 | コメント追加 | 新規コメント登録時 | Low |
| SYS-010 | セッション期限接近 | セッション残り15分 | Medium |

### 2.2 SLAアラート（SLA Alert）

**概要**: SLA目標値に対するリスク・違反通知

| 通知コード | 説明 | トリガー条件 | 優先度 |
|---|---|---|---|
| SLA-001 | SLA警告（60%消費） | SLA経過時間が目標の60%超過 | Medium |
| SLA-002 | SLA警告（80%消費） | SLA経過時間が目標の80%超過 | High |
| SLA-003 | SLA重大警告（95%消費） | SLA経過時間が目標の95%超過 | Critical |
| SLA-004 | SLA違反確定 | SLA目標時間を超過 | Critical |
| SLA-005 | 月次SLA未達成 | 月次SLA達成率が目標未満 | High |
| SLA-006 | P1担当者未アサイン | P1インシデント登録後15分以内に未アサイン | Critical |

### 2.3 エスカレーション通知（Escalation Notification）

**概要**: 定められたエスカレーションルールに基づく段階的通知

| 通知コード | 説明 | P1トリガー | P2トリガー | 優先度 |
|---|---|---|---|---|
| ESC-001 | Level 1エスカレーション | 発生時即時 | 発生後30分 | Critical / High |
| ESC-002 | Level 2エスカレーション | 30分経過 | 2時間経過 | Critical / High |
| ESC-003 | Level 3エスカレーション | 1時間経過 | 4時間経過 | Critical |
| ESC-004 | 経営層エスカレーション | 2時間経過 | SLA違反時 | Critical |
| ESC-005 | 変更承認タイムアウト | - | 72時間未承認 | High |
| ESC-006 | PIR未実施警告 | - | 変更後7日 | Medium |

### 2.4 AI提案通知（AI Suggestion Notification）

**概要**: AI Agentが生成した提案・分析結果の通知
**特記**: 全てのAI提案通知は「AI生成」であることを明示する義務がある

| 通知コード | 説明 | 生成AI | 優先度 | 透明性要件 |
|---|---|---|---|---|
| AI-001 | AI類似インシデント検索結果 | ClaudeAPI | Low | 信頼スコア表示必須 |
| AI-002 | AI根本原因分析提案 | ClaudeAPI | Medium | 判断根拠の要約表示必須 |
| AI-003 | AI変更リスク評価 | ClaudeAPI | Medium | リスクスコアと根拠表示必須 |
| AI-004 | AI影響範囲分析結果 | ClaudeAPI | High | 影響CIリストと信頼度表示必須 |
| AI-005 | AI自動修復実施報告 | ClaudeAPI | High | 実施内容・根拠・結果の全記録 |
| AI-006 | AI自動修復失敗報告 | ClaudeAPI | Critical | 失敗原因・ロールバック状態表示 |
| AI-007 | AI統治逸脱検知 | ガバナンスエンジン | Critical | 試行操作・ブロック理由表示必須 |
| AI-008 | AI倫理制約トリガー | ガバナンスエンジン | Critical | 制約条項・判断記録表示必須 |

---

## 3. 通知チャネル

### 3.1 チャネル一覧

| チャネルID | 名称 | ステータス | 主要用途 | 技術実装 |
|---|---|---|---|---|
| CH-01 | UI内通知（インボックス） | 実装済み | 全通知の基本チャネル | WebSocket + REST API |
| CH-02 | GitHub Issue コメント | 実装済み | チケット紐付き通知・承認リンク | GitHub REST API v3 |
| CH-03 | メール（SMTP） | 実装済み | エスカレーション・公式通知 | SMTP（SendGrid/SES） |
| CH-04 | Webhook | 実装済み | 外部システム連携 | HTTPS POST + HMAC署名 |
| CH-05 | Slack | 将来対応（v2.0） | チームコミュニケーション | Slack Webhook API |
| CH-06 | Microsoft Teams | 将来対応（v2.0） | チームコミュニケーション | Adaptive Cards API |
| CH-07 | Web Push（PWA） | 将来対応（v3.0） | モバイルCritical通知 | Web Push API |

### 3.2 優先度別チャネル選択マトリクス

| 優先度 | UI内通知 | GitHub Issue | メール | Webhook | Slack（将来） |
|---|---|---|---|---|---|
| Critical | 必須（即時） | 必須 | 必須 | 必須 | 必須 |
| High | 必須（即時） | 必須 | 必須 | 任意 | 任意 |
| Medium | 必須（即時） | 任意 | 任意 | 任意 | 任意 |
| Low | 必須（バッチ） | 任意 | 不可 | 不可 | 不可 |

### 3.3 UI内通知（CH-01）詳細設計

**配信方式**: WebSocket（接続中）/ REST APIポーリング（再接続中）

**表示コンポーネント**:

```typescript
interface UINotification {
  notificationId: string;      // 通知一意ID
  notificationCode: string;    // 通知コード（SYS-001等）
  title: string;               // 通知タイトル
  message: string;             // 通知本文
  priority: NotificationPriority; // Critical / High / Medium / Low
  channel: 'ui';
  createdAt: Date;
  readAt?: Date;               // 既読日時（未読=null）
  expiresAt?: Date;            // 通知有効期限
  actionUrl?: string;          // クリック時遷移先URL
  actionLabel?: string;        // アクションボタンラベル
  isAiGenerated: boolean;      // AI生成フラグ
  aiMetadata?: {               // AI生成時のメタデータ
    agentId: string;
    confidenceScore: number;   // 0.0 - 1.0
    modelVersion: string;
    decisionSummary: string;
  };
  sourceEntityType?: string;   // incident / change / problem 等
  sourceEntityId?: string;     // INC-042 等
}
```

### 3.4 GitHub Issue チャネル（CH-02）詳細設計

```
対象: チケット（インシデント・変更・問題）に紐付く通知
フォーマット: Markdown（AI生成バッジ付き）
メンション: @username による担当者メンション
ラベル自動付与: 通知種別に応じたラベル（sla-warning、escalation等）
承認リンク: 変更承認通知には直接承認URLを含める
AI通知表示: "🤖 AI Generated | Confidence: XX%" のバッジ表示
```

### 3.5 メールチャネル（CH-03）詳細設計

```
送信元: notifications@servicematrix.example.com
配信制限: 同一受信者・同一トリガーは15分間隔（Critical除く）
ダイジェスト: Low優先度通知は1時間ごとにダイジェスト配信
フォーマット: HTML + プレーンテキスト（マルチパート）
配信失敗: 3回リトライ後に代替アドレスへ転送 + 監査ログ記録
退会（オプトアウト）: Low/Medium通知は退会リンク付与（Criticalは退会不可）
```

### 3.6 Webhook チャネル（CH-04）詳細設計

```
プロトコル: HTTPS POST
ペイロード形式: JSON
認証: HMAC-SHA256署名（X-ServiceMatrix-Signature ヘッダー）
リトライ: 3回（Exponential Backoff: 10秒、30秒、90秒）
タイムアウト: 10秒
ペイロード最大サイズ: 1MB
```

---

## 4. 通知優先度と表示方法

### 4.1 優先度定義

| 優先度 | コード | 説明 | 代表的ケース |
|---|---|---|---|
| Critical | `critical` | 即時対応必須・業務停止リスク | P1障害、SLA違反、AI統治逸脱 |
| High | `high` | 早急対応推奨・SLA影響あり | P2障害、SLA80%警告、変更承認待ち |
| Medium | `medium` | 通常業務フロー内での対応 | P3障害、ステータス変更、PIR通知 |
| Low | `low` | 情報提供・完了報告 | コメント追加、サービスリクエスト完了 |

### 4.2 優先度別UI表示仕様

**Critical**:
```
表示位置: 画面上部固定バナー（全画面共通）
背景色: #FEF2F2（赤系）/ ボーダー: #DC2626
アイコン: 警告アイコン（赤）
効果: 高輝度・パルスアニメーション
操作: 「確認」ボタン必須（確認者・確認日時を記録）
継続: 確認操作まで消えない
音声: 設定可能（デフォルト: あり）
```

**High**:
```
表示位置: 画面右下スライドインパネル + 通知バッジ
背景色: #FFFBEB（黄系）/ ボーダー: #F59E0B
継続: 10秒後に通知インボックスへ移動
アイコン: インフォアイコン（黄）
音声: なし
```

**Medium**:
```
表示位置: 画面右下スライドインパネル（小）
背景色: #EFF6FF（青系）/ ボーダー: #3B82F6
継続: 5秒後に自動消去 + 通知インボックスへ移動
アイコン: インフォアイコン（青）
```

**Low**:
```
表示位置: 通知インボックスのみ（スライドイン表示なし）
バッジのみ: ヘッダーの通知ベルアイコンにバッジカウント加算
```

---

## 5. 通知の既読管理

### 5.1 既読管理データモデル

```sql
-- 通知テーブル（後述のDATA_SCHEMA_DEFINITIONと整合）
CREATE TABLE notifications (
    notification_id    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID        NOT NULL REFERENCES users(user_id),
    notification_code  VARCHAR(20) NOT NULL,
    title              VARCHAR(255) NOT NULL,
    message            TEXT        NOT NULL,
    priority           VARCHAR(20) NOT NULL,
    is_ai_generated    BOOLEAN     NOT NULL DEFAULT FALSE,
    ai_metadata        JSONB,
    source_entity_type VARCHAR(50),
    source_entity_id   VARCHAR(50),
    action_url         VARCHAR(500),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    read_at            TIMESTAMPTZ,
    acknowledged_at    TIMESTAMPTZ,
    acknowledged_by    UUID        REFERENCES users(user_id),
    expires_at         TIMESTAMPTZ,
    is_deleted         BOOLEAN     NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_notifications_user_unread
    ON notifications(user_id, read_at)
    WHERE read_at IS NULL AND is_deleted = FALSE;

CREATE INDEX idx_notifications_priority_created
    ON notifications(priority, created_at DESC);
```

### 5.2 既読操作仕様

| 操作 | API | 副作用 |
|---|---|---|
| 個別既読 | `PATCH /api/v1/notifications/{id}/read` | read_at に現在時刻を記録 |
| 全既読 | `POST /api/v1/notifications/read-all` | フィルタ条件に一致する全通知を既読化 |
| Critical確認 | `POST /api/v1/notifications/{id}/acknowledge` | acknowledged_at + acknowledged_by を記録（監査証跡） |
| 通知削除 | `DELETE /api/v1/notifications/{id}` | is_deleted = true（論理削除、30日後物理削除） |

### 5.3 未読バッジの計算ロジック

```
ヘッダーバッジ表示数:
  = Critical未確認数 × 10 + High未読数 × 2 + Medium/Low未読数
  ※Critical確認（acknowledge）未完了分を最大10件として換算
  ※表示上限: 99（100件以上は "99+"）

Critical専用バッジ（赤）:
  = Critical未確認数
  ※これが0以外の場合はベルアイコンを赤色で強調表示
```

---

## 6. 通知設定のユーザーカスタマイズ機能

### 6.1 個人通知設定項目

| 設定項目 | デフォルト | カスタマイズ可否 | 制約 |
|---|---|---|---|
| UI内通知 | ON | 不可（常時ON） | Critical通知は無効化不可 |
| メール通知（High以上） | ON | 可 | - |
| メール通知（Medium） | ON | 可 | - |
| メール通知（Low） | OFF | 可 | - |
| メールダイジェスト設定 | 個別送信 | 可（即時/1時間/日次） | Critical/Highは即時固定 |
| Slack通知（将来） | OFF | 可 | - |
| 効果音（Critical） | ON | 可 | - |
| 担当チケット通知のみ | OFF | 可 | SLA通知は対象外 |
| 通知時間帯制限 | なし | 可（時間帯設定）| Critical通知は制限不可 |
| 1日最大通知数上限 | 無制限 | 可（最低10件） | Critical通知は上限適用外 |

### 6.2 通知設定API

```
GET  /api/v1/users/{userId}/notification-settings
PUT  /api/v1/users/{userId}/notification-settings
```

```json
{
  "emailEnabled": true,
  "emailDigestInterval": "immediate",
  "emailMinPriority": "medium",
  "slackEnabled": false,
  "soundEnabled": true,
  "assignedTicketsOnly": false,
  "quietHours": {
    "enabled": true,
    "start": "22:00",
    "end": "08:00",
    "timezone": "Asia/Tokyo",
    "exceptCritical": true
  },
  "dailyLimit": null
}
```

### 6.3 システム全体通知設定（SystemAdminのみ）

| 設定項目 | デフォルト | 説明 |
|---|---|---|
| メール送信間隔制限 | 15分 | 同一受信者・同一イベントの最小間隔 |
| 1日あたり最大通知数/ユーザー | 100件 | 上限超過分はダイジェストに統合 |
| Criticalの制限解除 | ON | Critical通知は全制限を無効化 |
| Webhookリトライ回数 | 3回 | 配信失敗時のリトライ設定 |
| Webhookタイムアウト | 10秒 | Webhook応答タイムアウト |
| 通知ログ保持期間 | 1年 | 通知ログのデータ保持期間 |
| AI通知の確認要求 | OFF | AI生成通知に人間確認を必須化するか |

---

## 7. AI生成通知の透明性確保

### 7.1 透明性確保の原則

ServiceMatrixにおけるAI生成通知は、以下の透明性要件を全て満たす必要がある。

1. **明示的表示**: AI生成通知には "AI生成" バッジを必須表示する
2. **信頼スコア表示**: 判断の信頼度（0-100%）を表示する
3. **根拠の提示**: AI判断の根拠サマリーを利用者が確認できる
4. **モデル情報の記録**: 使用したAIモデルのバージョンを監査ログに記録する
5. **人間による上書き**: AI提案は必ず人間が承認/却下できる

### 7.2 AI生成通知のUI表示標準

```
通知カードのヘッダー部分に必須表示:
  [🤖 AI生成] [信頼度: 87%] [詳細を見る]

「詳細を見る」クリック時の展開内容:
  - 判断モデル: Claude claude-sonnet-4-6
  - 判断日時: 2026-03-02 10:32:00 JST
  - 根拠サマリー: "過去30日間の類似インシデント分析に基づき..."
  - 信頼度: 87% / 根拠データ数: 23件
  - 「この判断をフィードバック」リンク
```

### 7.3 AI通知の信頼スコア表示色

| 信頼スコア | 表示色 | 説明 |
|---|---|---|
| 90% 以上 | 緑 | 高信頼度・参考価値が高い |
| 70-89% | 黄 | 中信頼度・内容を確認して判断 |
| 50-69% | オレンジ | 低信頼度・慎重に検討が必要 |
| 50% 未満 | 赤 | 参考程度・人間判断を優先 |

### 7.4 AI生成通知の監査証跡

AI生成通知は、通常の通知ログに加えて以下を監査ログに記録する:

```sql
-- AI通知監査フィールド（audit_logs拡張）
-- agent_id: AI AgentのID
-- model_id: 使用したClaudeモデルID
-- confidence_score: 信頼スコア
-- decision_context: 判断コンテキストのJSON
-- input_token_count: 入力トークン数
-- output_token_count: 出力トークン数
-- human_override: 人間が提案を却下/修正したか
-- human_override_at: 人間による上書き日時
-- human_override_by: 上書きしたユーザーID
```

---

## 8. 通知配信の障害対応

### 8.1 配信失敗時の処理フロー

```
1. 配信失敗検知
     ↓
2. 指数バックオフでリトライ（3回）
   - 1回目: 10秒後
   - 2回目: 30秒後
   - 3回目: 90秒後
     ↓（全リトライ失敗時）
3. 代替チャネルで配信試行
   - メール失敗 → UI内通知に変更
   - Webhook失敗 → メールに変更
     ↓（代替チャネルも失敗時）
4. SystemAdminに緊急通知
5. 監査ログに障害記録
6. 月次障害レポートに集計
```

### 8.2 配信監査ログ

```sql
CREATE TABLE notification_delivery_logs (
    delivery_log_id  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_id  UUID        REFERENCES notifications(notification_id),
    channel          VARCHAR(20) NOT NULL,
    status           VARCHAR(20) NOT NULL, -- sent / failed / retrying
    attempt_count    INTEGER     NOT NULL DEFAULT 1,
    error_message    TEXT,
    sent_at          TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## 9. 改訂履歴

| バージョン | 日付 | 変更概要 | 変更者 |
|---|---|---|---|
| 1.0 | 2026-03-02 | 初版作成 | - |
| 2.0 | 2026-03-02 | 通知種別を4カテゴリに再整理、AI透明性確保要件追加、既読管理DDL追加、カスタマイズ仕様詳細化 | - |

---

*本ドキュメントはServiceMatrixプロジェクトの統治原則に基づき管理される。*
*変更はChange Issue → PR → CI検証 → 承認のフローに従うこと。*
