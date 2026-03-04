# 🗺️ ServiceMatrix 開発ロードマップ

> **プロジェクト**: ServiceMatrix - Multi-Dimensional Service Governance Platform
> **最終更新**: 2026-03-15
> **現在フェーズ**: Phase 3-7完了・Phase 8進行中（本番化・コンプライアンス対応中）

---

## 📊 全体フェーズ概要

```
Phase 0 ████████████████████ 100% ✅ 完了   基盤構築・ドキュメント整備
Phase 1 ████████████████████ 100% ✅ 完了   データモデル・スキーマ設計
Phase 2 ████████████████████ 100% ✅ 完了   コアプロセスエンジン実装
Phase 3 ████████████████████ 100% ✅ 完了   AI/Agent統合レイヤー
Phase 4 ████████████████████ 100% ✅ 完了   API レイヤー構築
Phase 5 ████████████████████ 100% ✅ 完了   UI/ダッシュボード実装
Phase 6 ████████████████████ 100% ✅ 完了   SLA自動監視エンジン
Phase 7 ████████████████████ 100% ✅ 完了   テスト・品質保証
Phase 8 ████████████████░░░░  80% 🔄 進行中 本番対応・コンプライアンス
```

---

## 📊 現在の技術状態サマリー（Step 36 時点）

| 項目 | 状態 |
|------|------|
| テスト | 404テスト通過 ✅ |
| カバレッジ | 87.15%（閾値75%達成）✅ |
| コード品質 | Ruff設定移行済み・lint警告0 ✅ |
| 実装済みAPI | Incident / Change / Problem / ServiceRequest / CMDB / SLA / Webhook / Auth / AI |
| AI機能 | AIトリアージ・RCA・類似インシデント検索・変更影響分析・AI決定ログ・WebSocket通知 |
| フロントエンド | Next.js 14・全ページ実装完了（Incident/Change/Problem/CMDB/SLA/AI/監査ログ） |

---

## ✅ Phase 0: 基盤構築・ドキュメント整備（完了）

**目標**: Git/GitHub基盤確立、全設計ドキュメント作成、CI/CD整備

**期間**: 2026-03-02 完了

### 完了済みタスク
- [x] SERVICEMATRIX_CHARTER.md 作成
- [x] CLAUDE.md（統治規則）策定
- [x] README.md 作成
- [x] GitHub リポジトリ作成
- [x] git init + remote 接続
- [x] .gitignore 設定
- [x] .github/workflows/ci.yml 設定
- [x] .github/workflows/pr-governance.yml 設定
- [x] docs/ フォルダ構造作成（70+ドキュメント）
- [x] docs/00_foundation/ ～ docs/99_appendix/ 全フォルダ作成・文書化完了
- [x] PR テンプレート整備完了
- [x] 初回 git commit + push

### Phase 0 完了基準（達成済み）
- [x] 全 docs/ ドキュメント（70+ファイル）作成完了
- [x] GitHub Actions CI が main ブランチで通過
- [x] PR テンプレート整備完了

---

## ✅ Phase 1: データモデル・スキーマ設計（完了）

**目標**: システム全体のデータ構造を確定し、実装の土台を固める

**依存**: Phase 0 完了 ✅

### 完了済みタスク
- [x] **データベース選定**: PostgreSQL 16
- [x] **ORM/スキーマ定義**: SQLAlchemy 2.0 + Alembic
- [x] **Incident テーブル設計・実装**
  ```sql
  incidents(id, title, description, priority, status, category,
            reporter_id, assignee_id, ci_id, sla_deadline,
            created_at, updated_at, resolved_at, closed_at)
  ```
- [x] **Change テーブル設計・実装**
  ```sql
  changes(id, title, type, risk_score, status, requested_by,
          approved_by, cab_required, scheduled_date,
          created_at, updated_at, implemented_at)
  ```
- [x] **Problem テーブル設計・実装**
  ```sql
  problems(id, title, root_cause, workaround, status,
           related_incidents[], created_at, resolved_at)
  ```
- [x] **ServiceRequest テーブル設計・実装**
- [x] **CMDB テーブル設計・実装**（CI, Relationships）
- [x] **SLA テーブル設計・実装**（definitions, measurements, breaches）
- [x] **AuditLog テーブル設計・実装**（SHA-256ハッシュチェーン）
- [x] **User/Team テーブル設計・実装**
- [x] Alembicマイグレーションファイル作成（月次パーティション・JSONB対応）
- [x] テストデータシード作成

### 技術スタック（確定済み）
- **言語**: Python 3.12+
- **フレームワーク**: FastAPI
- **DB**: PostgreSQL 16
- **ORM**: SQLAlchemy 2.0 + Alembic
- **バリデーション**: Pydantic v2

---

## 🔄 Phase 2: コアプロセスエンジン実装（80% 進行中）

**目標**: Incident / Change / Problem / Request 管理の中核ロジック実装

**依存**: Phase 1 完了 ✅

### 完了済みタスク
- [x] **Incident Management**
  - [x] Incident 作成・更新・クローズ CRUD
  - [x] 優先度自動判定ロジック
  - [x] SLA タイマー開始・計算
  - [x] ステータス遷移エンジン
  - [ ] GitHub Issues 自動作成連携
  - [ ] エスカレーション自動発火ロジック
- [x] **Change Management**
  - [x] RFC 作成・審査フロー CRUD
  - [x] CAB 承認ロジック
  - [x] リスクスコア自動算出
  - [ ] 変更カレンダー管理
- [x] **Problem Management**
  - [x] Problem CRUD
  - [x] Incident → Problem 連携
  - [x] KEDB（Known Error DB）登録・検索
  - [ ] RCA テンプレート生成
- [x] **Request Management（基本CRUD実装済み）**
  - [x] ServiceRequest モデル・基本操作
  - [ ] サービスカタログ定義
  - [ ] リクエスト承認フロー完全実装
- [ ] **CMDB（進行中）**
  - [ ] CI 関係管理・依存解析
  - [ ] CMDB 検索・フィルタリング
- [ ] **GitHub Webhook 受信処理**
  - [ ] Issues イベント処理
  - [ ] PR イベント処理
  - [ ] Actions 完了イベント処理

---

## 🔄 Phase 3: AI/Agent統合レイヤー（20% 進行中）

**目標**: ClaudeCode Agent Teams を ServiceMatrix の知性エンジンとして統合

**依存**: Phase 2 完了 ✅

### 完了済みタスク
- [x] **AI トリアージエンジン（Step 12）**
  - [x] Incident 内容から優先度・カテゴリ自動判定
  - [x] FastAPI BackgroundTasks（非同期・非ブロッキング実行）
  - [x] キーワードマッチング実装・LLMプロバイダー切替対応

### 残タスク
- [ ] 類似 Incident の自動検索
  - [ ] 影響範囲の自動特定（CMDB連携）
- [ ] **変更影響分析 Agent**
  - [ ] RFC の自動リスク評価
  - [ ] 影響 CI の自動特定
  - [ ] 過去変更との競合チェック
- [ ] **自動修復 Agent**
  - [ ] CI 失敗の自動診断
  - [ ] 修復候補の生成と提示
  - [ ] 低リスク修復の自動実行
- [ ] **AI 決定ログシステム**
  - [ ] すべての AI 判断を記録
  - [ ] GitHub Issue コメントへの自動記録
- [ ] **Agent Teams オーケストレーター**
  - [ ] タスク複雑度による自動 spawn 判断
  - [ ] チーム構成の動的最適化

---

## 🔄 Phase 4: API レイヤー構築（70% 進行中）

**目標**: RESTful API による外部連携インターフェース整備

**依存**: Phase 2 完了（Phase 3 と並行可）

### 完了済みタスク
- [x] **FastAPI ルーター設計（部分実装）**
  - [x] `/api/v1/incidents` - Incident CRUD
  - [x] `/api/v1/changes` - Change CRUD + 承認フロー
  - [x] `/api/v1/problems` - Problem 管理
  - [ ] `/api/v1/requests` - ServiceRequest 管理（進行中）
  - [ ] `/api/v1/sla` - SLA 照会・違反通知（進行中）
  - [ ] `/api/v1/cmdb/cis` - CI 管理（進行中）
  - [ ] `/api/v1/audit-logs` - 監査ログ照会
  - [ ] `/api/v1/ai/analyze` - AI 分析リクエスト
- [x] **認証・認可**
  - [x] JWT トークン発行・検証
  - [x] RBAC ミドルウェア
  - [x] 監査ミドルウェア
  - [ ] GitHub OAuth 連携
- [ ] **API ドキュメント（OpenAPI/Swagger）完全化**
- [ ] **Webhook 送信機能**
  - [ ] Incident 作成時 Webhook
  - [ ] SLA 違反時 Webhook
  - [ ] Change 承認時 Webhook

---

## ⏳ Phase 5: UI/ダッシュボード実装（未着手）

**目標**: Web インターフェースによる可視化とオペレーション

**依存**: Phase 4 完了

### 主要タスク
- [ ] **フロントエンド技術選定**: Next.js or Vue.js
- [ ] **メインダッシュボード**
  - [ ] KPI サマリーカード（SLA達成率、Incident件数、Change成功率）
  - [ ] リアルタイム Incident ストリーム
  - [ ] SLA 違反アラート
- [ ] **Incident 管理画面**
  - [ ] 一覧表（フィルタ・ソート）
  - [ ] 詳細画面（タイムライン・コメント）
  - [ ] 新規作成フォーム
- [ ] **Change 管理画面**
  - [ ] Change カレンダー
  - [ ] RFC 詳細・承認画面
- [ ] **SLA 監視画面**
  - [ ] サービス別 SLA ゲージ
  - [ ] 月次トレンドグラフ
- [ ] **AI 活動ログ画面**
  - [ ] Agent Teams 実行履歴
  - [ ] AI 決定ログビューア
- [ ] **CMDB ビジュアライザー**
  - [ ] CI 関連グラフ（D3.js）

---

## ⏳ Phase 6: SLA自動監視エンジン（未着手）

**目標**: SLA 監視・違反検知・自動通知の完全自動化

**依存**: Phase 4 完了

### 主要タスク
- [ ] **SLA タイマー管理**
  - [ ] Incident 作成時に SLA デッドライン自動計算
  - [ ] バックグラウンドジョブ（定期チェック）
- [ ] **違反予測アラート**
  - [ ] SLA 残り30分で事前警告
  - [ ] AI による違反リスク予測
- [ ] **自動通知**
  - [ ] GitHub Issue コメント自動投稿
  - [ ] Webhook 送信
- [ ] **SLA 月次レポート自動生成**
  - [ ] GitHub Actions での定期実行
  - [ ] Markdown レポート自動 Issue 作成

---

## 🔄 Phase 7: テスト・品質保証（30% 進行中）

**目標**: 全レイヤーのテストカバレッジ確保

**依存**: Phase 2～5 実装進捗に応じて並行実施

### 完了済みタスク
- [x] テストフレームワーク整備（pytest + pytest-cov）
- [x] カバレッジ計測設定（現在: **67.93%** ✅）
- [x] **162テストケース実装済み**（Unit / API / E2E）
  - [x] Incident サービスのユニットテスト
  - [x] Change サービスのユニットテスト
  - [x] Problem サービスのユニットテスト
  - [x] API エンドポイントテスト（Incident/Change/Problem）
  - [x] **Step 11**: Ruff設定移行・コード品質修正（`pyproject.toml` 統合）
  - [x] **Step 12**: AIトリアージエンジン（キーワードベース・BackgroundTasks実装）
  - [x] **Step 13**: E2Eシナリオテスト（Incident/Change全フロー実装）
  - [x] **Step 15**: カバレッジ67.93%達成（閾値67%）

### 残タスク
- [ ] **Unit テスト** (目標: 80%+ カバレッジ)
  - [ ] SLA 計算ロジックのユニットテスト
  - [ ] RBAC・認証ロジックのユニットテスト
  - [ ] AI スコアリングロジックのユニットテスト
- [ ] **Integration テスト**
  - [ ] DB 連携テスト（実DB使用）
  - [ ] GitHub API モック連携テスト
- [ ] **E2E テスト拡張**
  - [x] Incident 作成～クローズフロー（完了）
  - [x] Change 申請～承認フロー（完了）
  - [ ] SLA 違反検知フロー
- [ ] **セキュリティテスト**
  - [ ] OWASP Top 10 チェック
  - [ ] 依存パッケージ脆弱性スキャン（Dependabot）
- [ ] **パフォーマンステスト**
  - [ ] 負荷テスト（同時100ユーザー）
  - [ ] API レスポンスタイム目標: 200ms以下

---

## ⏳ Phase 8: 本番対応・コンプライアンス（未着手）

**目標**: 本番環境デプロイと監査対応完備

**依存**: Phase 7 完了

### 主要タスク
- [ ] **本番環境構築**
  - [ ] コンテナ化（Docker / Docker Compose）
  - [ ] CI/CD 本番デプロイパイプライン
  - [ ] 環境変数・シークレット管理（GitHub Secrets）
- [ ] **監視・可観測性**
  - [ ] アプリケーションログ集約
  - [ ] メトリクス収集（Prometheus/Grafana）
  - [ ] アラート設定
- [ ] **セキュリティ強化**
  - [ ] HTTPS 強制
  - [ ] WAF設定
  - [ ] 定期セキュリティスキャン自動化
- [ ] **監査対応**
  - [ ] ISO 20000 適合性評価
  - [ ] J-SOX 統制評価書作成
  - [ ] 監査証跡完全性確認
- [ ] **ドキュメント最終化**
  - [ ] 運用マニュアル
  - [ ] 障害対応ガイド
  - [ ] オンボーディングガイド

---

## 📐 アーキテクチャ概要（実装方針）

```
┌─────────────────────────────────────────────────────┐
│                  ServiceMatrix                       │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  Web UI  │  │  REST API│  │  GitHub Actions  │  │
│  │(Next.js) │  │(FastAPI) │  │  (CI/CD/Bot)    │  │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
│       │             │                  │             │
│  ┌────▼─────────────▼──────────────────▼──────────┐ │
│  │              Core Engine (Python)               │ │
│  │  Incident │ Change │ Problem │ Request │ SLA    │ │
│  └────────────────────┬────────────────────────────┘ │
│                       │                              │
│  ┌────────────────────▼────────────────────────────┐ │
│  │              AI/Agent Layer                     │ │
│  │   ClaudeCode Agent Teams │ AI Triage │ AutoFix  │ │
│  └────────────────────┬────────────────────────────┘ │
│                       │                              │
│  ┌────────────────────▼────────────────────────────┐ │
│  │              Data Layer                         │ │
│  │    PostgreSQL │ CMDB │ AuditLog │ SLA Metrics   │ │
│  └─────────────────────────────────────────────────┘ │
│                                                     │
│  ┌─────────────────────────────────────────────────┐ │
│  │           GitHub Native Layer                   │ │
│  │   Issues │ Pull Requests │ Actions │ Webhooks   │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

---

## 🎯 マイルストーン

| マイルストーン | 目標日 | 状態 |
|--------------|--------|------|
| M0: 基盤確立 | 2026-03-08 | ✅ 完了 |
| M1: データモデル確定 | 2026-03-22 | ✅ 完了 |
| M2: コアAPI MVP | 2026-04-12 | ✅ 完了 |
| M3: AI統合 α版 | 2026-04-30 | 🔄 進行中（20%） |
| M4: UI β版 | 2026-05-20 | ⏳ 未着手 |
| M5: SLA自動監視稼働 | 2026-06-07 | ⏳ 未着手 |
| M6: テスト完備版 | 2026-06-28 | ⏳ 未着手 |
| M7: 本番リリース v1.0 | 2026-07-31 | ⏳ 未着手 |

---

## 🔀 調整済みフェーズ（A〜E）：実装順序最適化

現在の進捗を踏まえ、フェーズ依存関係を整理した実装ロードマップ。

### ✅ Phase A: コアAPI補完（完了）

**目標**: Phase 2/4 の未完了タスクを完結させ、フルMVPを確立する

- [x] ServiceRequest API の完全実装（CRUD + 承認フロー）
- [x] CMDB API の完全実装（CI管理・関係グラフ）
- [x] SLA API の完全実装（照会・違反通知）
- [x] Webhook 送信機能（Incident/Change/SLA違反）
- [x] 認証・RBAC 完全実装（JWT + 監査ミドルウェア）
- [x] Ruff設定移行・コード品質修正（Step 11）
- [x] カバレッジ67.93%達成（Step 15）

**達成状態**: 全 `/api/v1/*` エンドポイント動作・カバレッジ 67.93% ✅

---

### 🔄 Phase B: AI/Agent統合（優先度: 高）

**目標**: ClaudeCode Agent Teams を ServiceMatrix の知性エンジンとして統合

- [x] **Step 12**: AI トリアージエンジン（Incident 優先度・カテゴリ自動判定）
  - [x] キーワードベース判定ロジック実装
  - [x] FastAPI BackgroundTasks による非同期実行
  - [x] LLMプロバイダー切替対応（keyword/openai/azure_openai/ollama）
- [ ] 類似 Incident 自動検索
- [ ] 影響範囲の自動特定（CMDB連携）
- [ ] 変更影響分析 Agent（RFC の自動リスク評価）
- [ ] 自動修復 Agent（CI 失敗の自動診断・修復候補生成）
- [ ] AI 決定ログシステム（全 AI 判断を記録）
- [ ] Agent Teams オーケストレーター

**完了基準**: AI エージェントが Incident/Change に対して自動分析を実行できる

---

### ⏳ Phase C: UI/ダッシュボード（優先度: 中）

**目標**: Web インターフェースによる可視化とオペレーション

- [ ] フロントエンド技術選定（Next.js 推奨）
- [ ] メインダッシュボード（KPI・SLA達成率・Incident件数）
- [ ] Incident 管理画面（一覧・詳細・タイムライン）
- [ ] Change 管理画面（カレンダー・RFC詳細・承認）
- [ ] SLA 監視画面（サービス別ゲージ・月次トレンド）
- [ ] AI 活動ログ画面（Agent Teams 実行履歴）
- [ ] CMDB ビジュアライザー（D3.js CI関係グラフ）

**完了基準**: ブラウザから全主要操作が完結する

---

### 🔄 Phase D: テスト強化・品質保証（優先度: 高）

**目標**: カバレッジ 80%+ 達成・統合テスト・E2E 整備

- [x] カバレッジ 67.93% 達成（Step 15 / 閾値67%クリア）
- [x] E2E テスト整備（Incident/Change フル実装）（Step 13）
- [ ] カバレッジ 80%+ 達成（現在: 67.93%）
- [ ] ServiceRequest / CMDB / SLA のユニットテスト追加
- [ ] DB 連携統合テスト（実 PostgreSQL 使用）
- [ ] OWASP Top 10 セキュリティチェック
- [ ] 負荷テスト（同時100ユーザー / API 200ms以下）

**完了基準**: CI でカバレッジ 80%+ を継続維持

---

### ⏳ Phase E: 本番リリース準備（優先度: 最低→最終）

**目標**: 本番環境デプロイと監査対応完備

- [ ] Docker / Docker Compose 本番構成
- [ ] CI/CD 本番デプロイパイプライン
- [ ] 環境変数・シークレット管理（GitHub Secrets）
- [ ] アプリケーションログ集約
- [ ] メトリクス収集（Prometheus/Grafana）
- [ ] HTTPS 強制・WAF 設定
- [ ] ISO 20000 適合性評価
- [ ] J-SOX 統制評価書作成
- [ ] 運用マニュアル・障害対応ガイド・オンボーディングガイド

**完了基準**: v1.0 本番リリース・監査証跡完全性確認

---

## 🔗 関連ドキュメント

- [SERVICEMATRIX_CHARTER.md](./SERVICEMATRIX_CHARTER.md)
- [docs/02_architecture/SYSTEM_ARCHITECTURE_OVERVIEW.md](./docs/02_architecture/SYSTEM_ARCHITECTURE_OVERVIEW.md)
- [docs/05_devops/BRANCH_STRATEGY.md](./docs/05_devops/BRANCH_STRATEGY.md)
- [docs/05_devops/CI_CD_PIPELINE_ARCHITECTURE.md](./docs/05_devops/CI_CD_PIPELINE_ARCHITECTURE.md)
- [docs/07_sla_metrics/SLA_DEFINITION.md](./docs/07_sla_metrics/SLA_DEFINITION.md)
- [docs/api/ai_triage.md](./docs/api/ai_triage.md)
- [docs/api/e2e_testing.md](./docs/api/e2e_testing.md)
