# ダッシュボードデザイン仕様

**ドキュメント番号**: SM-UI-001
**バージョン**: 2.0
**分類**: UI/UX設計仕様
**作成日**: 2026-03-02
**最終更新日**: 2026-03-02
**準拠規格**: ITIL 4 / ISO/IEC 20000 / WCAG 2.1 AA / J-SOX
**ステータス**: 承認済み

---

## 1. 目的と適用範囲

### 1.1 目的

本仕様書は、ServiceMatrixにおけるすべてのダッシュボード画面の設計標準を定義する。
統一された情報表示によって、運用担当者・管理者・監査担当者・AIシステムが同一の情報基盤から意思決定を行えるよう設計する。
J-SOX対応として、全操作の監査証跡を確保した設計とする。

### 1.2 適用範囲

- 運用ダッシュボード（Operational Dashboard）
- 管理ダッシュボード（Management Dashboard）
- 監査ダッシュボード（Audit Dashboard）
- AI監視ダッシュボード（AI Monitoring Dashboard）

### 1.3 設計原則

| 原則 | 説明 |
|---|---|
| 情報密度の最適化 | 重要情報を優先し、認知負荷を最小化する |
| 一貫性 | 全ダッシュボード共通のUI言語・色彩設計を使用する |
| 即時フィードバック | データ更新状態をユーザーに常に明示する |
| 透明性 | AI生成データは必ずその旨を明示する |
| 監査可能性 | 全操作・閲覧履歴を監査ログに記録する |

---

## 2. ダッシュボード種別定義

### 2.1 運用ダッシュボード（Operational Dashboard）

**目的**: 日常運用における現在状態のリアルタイム把握

**主要利用者**: Operator、ProcessOwner

**更新頻度**: リアルタイム（WebSocket）

**パス**: `/dashboard/operational`

#### ウィジェット一覧

| ウィジェットID | 名称 | 説明 | 更新方式 | 表示優先度 |
|---|---|---|---|---|
| OP-W01 | アクティブインシデントカウンター | 未解決インシデント数（重大度別バッジ表示） | WebSocket | Critical |
| OP-W02 | SLAステータスゲージ | 現在のSLA達成率をゲージ+数値表示 | WebSocket | Critical |
| OP-W03 | インシデントタイムライン | 過去24時間のインシデント発生推移グラフ（エリアチャート） | 60秒ポーリング | High |
| OP-W04 | オープン変更リクエスト一覧 | 承認待ち・実施中の変更リクエスト一覧 | 60秒ポーリング | High |
| OP-W05 | サービス稼働状態マップ | サービスの稼働/障害/メンテナンス状態グリッド | WebSocket | Critical |
| OP-W06 | エスカレーション待ちキュー | エスカレーション対象インシデント一覧 | WebSocket | High |
| OP-W07 | MTTR/MTBFトレンド | 解決時間・障害間隔の直近30日推移グラフ | 5分ポーリング | Medium |
| OP-W08 | AIアシスト提案パネル | AI分析による対応推奨アクション（AI生成明示付き） | WebSocket | Medium |
| OP-W09 | アクティブ変更カレンダー | 当日・翌日の変更スケジュール一覧 | 5分ポーリング | Medium |
| OP-W10 | システム負荷インジケーター | CPU/メモリ/ディスク使用率サマリー | 30秒ポーリング | High |

---

### 2.2 管理ダッシュボード（Management Dashboard）

**目的**: KPI・トレンド・経営指標の把握と意思決定支援

**主要利用者**: ProcessOwner、SystemAdmin

**更新頻度**: 5分ポーリング（コスト最適化）

**パス**: `/dashboard/management`

#### ウィジェット一覧

| ウィジェットID | 名称 | 説明 | 更新方式 | 表示優先度 |
|---|---|---|---|---|
| MG-W01 | KPIサマリーカード群 | SLA達成率・インシデント数・変更成功率・MTTR | 5分ポーリング | Critical |
| MG-W02 | 月次インシデントトレンド | 月次インシデント発生数の推移（棒グラフ+折れ線） | 日次更新 | High |
| MG-W03 | 変更成功率ヒートマップ | カテゴリ×週次の変更成功率ヒートマップ | 日次更新 | High |
| MG-W04 | 問題管理ステータス | 根本原因分析中・解決済み問題の状態サマリー | 5分ポーリング | High |
| MG-W05 | SLA違反傾向分析 | SLA違反の発生傾向とAIによるリスク予測 | 日次更新 | High |
| MG-W06 | リソース稼働率サマリー | チーム・エージェント稼働状況（工数可視化） | 日次更新 | Medium |
| MG-W07 | コンプライアンス達成率 | ITIL/ISO20000/J-SOX準拠指標ダッシュボード | 週次更新 | Medium |
| MG-W08 | AI介入実績 | AI自動処理・人間承認件数の比較グラフ | 日次更新 | Medium |
| MG-W09 | サービス別SLA達成率 | サービス単位のSLA達成率比較バーチャート | 5分ポーリング | High |
| MG-W10 | 週次レポートプレビュー | 次回レポート対象データのプレビューカード | 日次更新 | Low |

---

### 2.3 監査ダッシュボード（Audit Dashboard）

**目的**: J-SOX・ISO/IEC 20000準拠のための監査証跡確認

**主要利用者**: Auditor

**更新頻度**: オンデマンド（リアルタイム更新不要）

**パス**: `/dashboard/audit`

**アクセス制御**: Auditorロール専用（RBAC強制）

#### ウィジェット一覧

| ウィジェットID | 名称 | 説明 | 更新方式 | 表示優先度 |
|---|---|---|---|---|
| AU-W01 | 監査ログタイムライン | ユーザー操作・AI操作の時系列ログビューア | オンデマンド | Critical |
| AU-W02 | 権限変更履歴 | ロール付与・剥奪の操作履歴一覧 | オンデマンド | Critical |
| AU-W03 | 変更承認フロー追跡 | 変更リクエストの承認経路サンキーダイアグラム | オンデマンド | Critical |
| AU-W04 | 未承認変更検出 | 承認なく実施された変更のアラートリスト | オンデマンド | Critical |
| AU-W05 | AI判断ログビューア | AI自動処理の判断根拠・信頼スコア一覧 | オンデマンド | High |
| AU-W06 | データアクセス記録 | 機密データへのアクセス履歴（IPアドレス付き） | オンデマンド | High |
| AU-W07 | SLA違反記録 | SLA違反の詳細記録と対応履歴タイムライン | オンデマンド | High |
| AU-W08 | ハッシュ整合性チェック | 監査ログのハッシュチェーン検証結果ステータス | オンデマンド | High |
| AU-W09 | レポートエクスポート | 監査用レポート（PDF/CSV）一括ダウンロード | オンデマンド | Medium |
| AU-W10 | コンプライアンスサマリー | 内部統制評価指標サマリー（J-SOX対応） | 週次更新 | Medium |

---

### 2.4 AI監視ダッシュボード（AI Monitoring Dashboard）

**目的**: AI Agentの稼働状態・判断品質・介入実績の可視化

**主要利用者**: SystemAdmin、ProcessOwner

**更新頻度**: リアルタイム（WebSocket）

**パス**: `/dashboard/ai-monitoring`

#### ウィジェット一覧

| ウィジェットID | 名称 | 説明 | 更新方式 | 表示優先度 |
|---|---|---|---|---|
| AI-W01 | Agentステータス一覧 | 各AI Agentの稼働状態・現在タスク・消費トークン | WebSocket | Critical |
| AI-W02 | AI介入件数カウンター | 当日の自動処理・提案件数（種別内訳付き） | WebSocket | High |
| AI-W03 | 信頼スコア分布 | AI判断の信頼スコア分布ヒストグラム（直近100件） | 5分ポーリング | High |
| AI-W04 | 人間オーバーライド率 | AI提案を人間が覆した割合の週次推移グラフ | 日次更新 | High |
| AI-W05 | AIエラーログ | API呼び出し失敗・タイムアウト・レート制限記録 | WebSocket | High |
| AI-W06 | コスト消費メーター | Claude API トークン消費量と月次予算残高ゲージ | 5分ポーリング | Medium |
| AI-W07 | 意思決定フローグラフ | AI判断のフロー可視化（リアルタイムDAG） | WebSocket | Medium |
| AI-W08 | モデル応答時間分布 | API応答時間のパーセンタイル分布（p50/p95/p99） | 5分ポーリング | Medium |
| AI-W09 | 自動修復成功率 | AI自動修復の成功率トレンド（7日間） | 日次更新 | High |
| AI-W10 | 倫理制約トリガー記録 | AIが倫理ガードレールで停止した記録（要注意） | WebSocket | Critical |

---

## 3. リアルタイム更新要件

### 3.1 WebSocket接続設計

```
接続エンドポイント: wss://{host}/api/v1/ws/dashboard/{dashboard_type}
認証方式: Bearer Token（WebSocket接続時ヘッダー送信）
再接続戦略: Exponential Backoff（初回1秒、最大60秒、最大試行10回）
ハートビート: 30秒間隔 ping/pong
接続タイムアウト: 5秒
メッセージ圧縮: permessage-deflate（有効化）
```

**WebSocket対象ダッシュボード**:

| ダッシュボード | WebSocket利用 | 更新トリガー |
|---|---|---|
| 運用ダッシュボード | YES | インシデント状態変化、SLA変化、新規アラート |
| 管理ダッシュボード | NO（ポーリング） | - |
| 監査ダッシュボード | NO（オンデマンド） | - |
| AI監視ダッシュボード | YES | Agentイベント、判断実行、エラー検知 |

**WebSocketメッセージフォーマット**:

```json
{
  "type": "widget_update",
  "widget_id": "OP-W01",
  "event": "incident.created | incident.updated | sla.breached",
  "data": {},
  "timestamp": "2026-03-02T10:32:00Z",
  "source": "servicematrix-backend"
}
```

### 3.2 ポーリング設計

**対象**: 管理ダッシュボード、一部運用ウィジェット

```
通常更新間隔: 5分（300秒）
実装方式: React Query refetchInterval + SWR
バックオフ: エラー時に更新間隔を2倍に延長（最大30分）
バックグラウンド時: 更新停止（visibilitychange API利用）
フォアグラウンド復帰時: 即時再取得
```

### 3.3 更新優先度制御

| 優先度 | トリガー条件 | 更新間隔 |
|---|---|---|
| Priority 1 (即時) | SLA違反確定、Critical障害発生 | WebSocket即時プッシュ |
| Priority 2 (10秒) | アクティブインシデント状態変化、エスカレーション | WebSocket / 10秒ポーリング |
| Priority 3 (60秒) | 一般的な指標更新、変更リクエスト更新 | 60秒ポーリング |
| Priority 4 (5分) | 統計・集計データ、トレンドグラフ | 5分ポーリング |
| Priority 5 (日次) | 月次・週次レポートデータ | 日次バッチ更新 |

### 3.4 更新状態の可視化

```
接続状態インジケーター（画面右下）:
  - 緑点滅: WebSocket接続中・正常
  - 黄点灯: ポーリングモード（WebSocket再接続中）
  - 赤点灯: 接続断（データが古い可能性あり）

最終更新時刻: 各ウィジェット右上に表示
  - 表示形式: "XX秒前" / "XX分前" に自動更新
```

---

## 4. KPIカード設計

### 4.1 SLA達成率カード

**コンポーネント名**: `KpiSlaRateCard`

```
表示値: XX.X%（小数第1位まで）
カラーコーディング:
  - 緑（#22C55E）: >= 99.0%
  - 黄（#F59E0B）: 95.0% - 98.9%
  - 赤（#EF4444）: < 95.0%
トレンド: 前月比較（上昇▲/維持→/下降▼）
クリックアクション: SLA詳細画面へ遷移
サブ情報: 対象サービス数、測定期間
```

**レイアウト**:

```
+----------------------------+
| SLA達成率        ▲ +0.3%  |
|                            |
|       99.2%                |
|   [██████████░░] 99.2%    |
| 今月  対象: 8サービス       |
| 最終更新: 30秒前            |
+----------------------------+
```

### 4.2 インシデント数カード

**コンポーネント名**: `KpiIncidentCountCard`

```
表示値: 未解決件数（重大度別バッジ付き）
  - Critical（P1）: 赤バッジ
  - High（P2）: オレンジバッジ
  - Medium（P3）: 黄バッジ
  - Low（P4）: グレーバッジ
更新頻度: WebSocket（リアルタイム）
クリックアクション: インシデント一覧へ遷移（フィルター適用）
アニメーション: 件数増加時に数字のフリップアニメーション
```

### 4.3 変更成功率カード

**コンポーネント名**: `KpiChangeSuccessCard`

```
表示値: 当月変更成功率（%）
計算式: 成功変更数 / 総変更数 × 100
カラーコーディング:
  - 緑: >= 95%
  - 黄: 85% - 94%
  - 赤: < 85%
表示期間: 直近30日間
サブ情報: 総変更数、成功数、失敗数の内訳
```

### 4.4 MTTR（平均復旧時間）カード

**コンポーネント名**: `KpiMttrCard`

```
表示値: 直近30日MTTR（時間:分形式）
比較基準: SLA目標MTTRと比較表示
  - 目標以内: 緑
  - 目標の110%以内: 黄
  - 目標超過: 赤
分類別表示: P1/P2/P3別内訳をサブ表示
```

### 4.5 KPIカード共通TypeScript型定義

```typescript
interface KpiCardProps {
  title: string;                     // カード名称
  value: string | number;            // 主要表示値
  unit?: string;                     // 単位（%、件、時間など）
  trend?: 'up' | 'down' | 'stable'; // トレンド方向
  trendValue?: string;               // トレンド数値（例: "+0.3%"）
  trendLabel?: string;               // トレンド比較基準（例: "前月比"）
  severity?: 'success' | 'warning' | 'error' | 'info';
  subInfo?: { label: string; value: string }[]; // サブ情報
  onClick?: () => void;              // 詳細遷移
  isLoading?: boolean;               // ローディング状態
  isStale?: boolean;                 // データが古い状態
  lastUpdated?: Date;                // 最終更新日時
  aiGenerated?: boolean;             // AI生成データフラグ
}
```

---

## 5. アラート表示設計

### 5.1 アラート種別と表示方法

| アラート種別 | 表示方法 | 継続時間 | ユーザー操作 |
|---|---|---|---|
| Critical障害（P1）発生 | 画面上部固定バナー（赤）+ サイレン音（設定可） | 手動確認まで | 確認ボタン必須 |
| SLA違反確定 | 固定バナー（赤）+ ベル通知 | 手動確認まで | 確認ボタン必須 |
| SLA警告（80%閾値） | トースト通知（黄）+ サイドパネル残留 | 10秒 + 残留 | ワンクリック確認 |
| 変更承認待ち | ベル通知バッジ + インボックス | 確認まで | インボックスで確認 |
| AI倫理制約トリガー | 固定バナー（オレンジ）+ 管理者通知 | 手動確認まで | 確認ボタン必須 |
| AI提案 | サイドパネル通知（青） | 確認まで | 承認/却下 |
| 情報通知 | トースト通知（青） | 3秒 | 自動消去 |

### 5.2 アラートバナー TypeScript型定義

```typescript
interface AlertBannerProps {
  alertId: string;
  severity: 'critical' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: Date;
  actionLabel?: string;
  onAction?: () => void;
  onDismiss?: () => void;
  isDismissible: boolean;    // CriticalはfalsEに強制
  requiresAcknowledge: boolean; // 確認ボタン表示フラグ
  acknowledgedBy?: string;   // 確認者ユーザーID
  acknowledgedAt?: Date;     // 確認日時（監査証跡）
}
```

### 5.3 アラートスタック制御

```
同時表示最大数: 5件
超過時: 「他N件のアラートがあります」折りたたみ表示
優先度順: Critical > Warning > Info
同優先度内: 新しいものを上に表示
バナーと通知の分離:
  - Critical/SLA違反 → 固定バナー領域
  - 一般通知 → 通知パネル（右下スライドイン）
```

### 5.4 通知インボックス

```
アクセス: ヘッダーベルアイコン（未読バッジ付き）
表示件数: 最新50件
保持期間: 30日
既読管理: 個別既読 / 全既読
フィルタ: 種別・優先度・日付範囲
エクスポート: CSV（監査用）
```

---

## 6. モバイル対応方針

### 6.1 対応ブレークポイント

```css
/* Tailwind CSS ブレークポイント */
sm: 640px   /* スマートフォン横向き / 小型タブレット */
md: 768px   /* タブレット縦向き */
lg: 1024px  /* タブレット横向き / 小型デスクトップ */
xl: 1280px  /* デスクトップ */
2xl: 1536px /* ワイドスクリーン */
```

### 6.2 モバイル表示優先ウィジェット

モバイル（< 640px）では以下のウィジェットのみ表示:

| ダッシュボード | モバイル表示ウィジェット（優先順） |
|---|---|
| 運用 | OP-W01（インシデントカウンター）、OP-W02（SLAゲージ）、OP-W05（稼働状態） |
| 管理 | MG-W01（KPIサマリー）、MG-W09（サービス別SLA） |
| 監査 | AU-W01（監査ログ）、AU-W04（未承認変更） |
| AI監視 | AI-W01（Agentステータス）、AI-W02（介入件数） |

### 6.3 モバイルUX要件

```
タッチターゲット最小サイズ: 44 × 44px（iOS HIG準拠）
スワイプ操作: ウィジェット間スワイプナビゲーション対応
フォント最小サイズ: 14px（可読性確保）
PWA対応: Service Workerによるオフラインキャッシュ
プッシュ通知: Web Push API（Critical通知のみ）
ジェスチャー: プルトゥリフレッシュ対応
```

---

## 7. Next.js実装方針

### 7.1 ディレクトリ構成

```
app/
├── (auth)/
│   └── login/page.tsx
├── dashboard/
│   ├── layout.tsx               # 共通レイアウト（ナビ・ヘッダー）
│   ├── operational/
│   │   └── page.tsx             # 運用ダッシュボード（Client Component）
│   ├── management/
│   │   └── page.tsx             # 管理ダッシュボード（Server Component + SSR）
│   ├── audit/
│   │   └── page.tsx             # 監査ダッシュボード（Server Component + SSR）
│   └── ai-monitoring/
│       └── page.tsx             # AI監視ダッシュボード（Client Component）
├── components/
│   ├── dashboard/
│   │   ├── KpiCard.tsx
│   │   ├── AlertBanner.tsx
│   │   ├── NotificationInbox.tsx
│   │   ├── WidgetContainer.tsx
│   │   ├── ConnectionIndicator.tsx
│   │   └── widgets/
│   │       ├── IncidentCountWidget.tsx
│   │       ├── SlaGaugeWidget.tsx
│   │       ├── ServiceStatusMapWidget.tsx
│   │       ├── AiAgentStatusWidget.tsx
│   │       └── ...
│   └── shared/
│       ├── LoadingSkeleton.tsx
│       ├── ErrorBoundary.tsx
│       └── AiGeneratedBadge.tsx  # AI生成データ明示コンポーネント
├── hooks/
│   ├── useDashboardWebSocket.ts
│   ├── useDashboardPolling.ts
│   ├── useAlerts.ts
│   └── useNotifications.ts
└── stores/
    └── dashboardStore.ts         # Zustand ストア
```

### 7.2 状態管理（Zustand）

```typescript
interface DashboardStore {
  // 状態
  alerts: Alert[];
  notifications: Notification[];
  kpiData: KpiData;
  widgetLayouts: Record<DashboardType, WidgetLayout[]>;
  connectionStatus: 'connected' | 'polling' | 'disconnected';
  lastUpdated: Record<string, Date>;

  // Actions
  addAlert: (alert: Alert) => void;
  acknowledgeAlert: (alertId: string, userId: string) => void;
  dismissNotification: (notificationId: string) => void;
  markAllRead: () => void;
  updateKpi: (kpi: Partial<KpiData>) => void;
  updateWidgetLayout: (
    dashboardType: DashboardType,
    layout: WidgetLayout[]
  ) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
}
```

### 7.3 レンダリング戦略

| データ種別 | レンダリング戦略 | キャッシュ戦略 | 理由 |
|---|---|---|---|
| 初期KPIデータ | Server Component（SSR） | no-cache | 常に最新データ表示 |
| リアルタイム更新 | Client Component（WebSocket） | - | インタラクティブ性 |
| 静的設定・マスターデータ | Static Generation（SSG） | 1時間 | キャッシュ効率 |
| 監査ログ一覧 | Server Component（SSR） | no-cache | セキュリティ・鮮度 |
| グラフ・トレンドデータ | Client Component（ポーリング） | stale-while-revalidate | UX最適化 |

### 7.4 パフォーマンス要件

| 指標 | 目標値 | 測定ツール |
|---|---|---|
| LCP（Largest Contentful Paint） | < 2.5秒 | Lighthouse / CrUX |
| FID（First Input Delay） | < 100ms | Lighthouse / CrUX |
| CLS（Cumulative Layout Shift） | < 0.1 | Lighthouse / CrUX |
| ウィジェット初期表示 | < 1秒 | カスタムメトリクス |
| WebSocket接続確立 | < 500ms | カスタムメトリクス |
| ポーリング初回データ取得 | < 1.5秒 | カスタムメトリクス |

### 7.5 エラーバウンダリ設計

```typescript
// 各ウィジェットをErrorBoundaryでラップ
// ウィジェット単位でエラー分離（1つのウィジェット障害が全体に影響しない）
<ErrorBoundary
  fallback={<WidgetErrorFallback widgetId={widgetId} />}
  onError={(error, info) => logWidgetError(error, info, widgetId)}
>
  <WidgetComponent />
</ErrorBoundary>
```

---

## 8. アクセシビリティ要件（WCAG 2.1 AA）

| 要件 | 実装方法 |
|---|---|
| キーボードナビゲーション | Tab順序の論理的設定、フォーカストラップ管理 |
| スクリーンリーダー対応 | aria-label、aria-live regions（polite/assertive） |
| カラーコントラスト | テキスト最小4.5:1、大文字テキスト最小3:1 |
| アニメーション | prefers-reduced-motion メディアクエリ対応 |
| アラート通知 | role="alert" + aria-live="assertive"（Criticalのみ） |
| チャート・グラフ | aria-label + テーブル形式の代替テキスト提供 |
| タイムアウト | セッションタイムアウト前60秒の事前警告 |

---

## 9. セキュリティ要件

```
CSP（Content Security Policy）: 全ダッシュボードで厳格なCSPヘッダー設定
XSS防止: Reactの自動エスケープ + DOMPurify（Markdown表示時）
CORS: 同一オリジンのみ許可（APIは明示的な許可ドメインのみ）
WebSocket認証: Bearer Token + 定期的なトークン更新
監査ログ: ダッシュボード閲覧もアクセスログとして記録
センシティブデータ: 監査ダッシュボードはHTTPS必須・ログイン必須
```

---

## 10. 改訂履歴

| バージョン | 日付 | 変更概要 | 変更者 |
|---|---|---|---|
| 1.0 | 2026-03-02 | 初版作成（基本ダッシュボード設計） | - |
| 2.0 | 2026-03-02 | 4種別ダッシュボード全体再設計、リアルタイム更新要件詳細化、モバイル対応追加 | - |

---

*本ドキュメントはServiceMatrixプロジェクトの統治原則に基づき管理される。*
*変更はChange Issue → PR → CI検証 → 承認のフローに従うこと。*
