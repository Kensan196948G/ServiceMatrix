# 🗺️ ServiceMatrix 開発ロードマップ

> **プロジェクト**: ServiceMatrix - Multi-Dimensional Service Governance Platform
> **最終更新**: 2026-03-02
> **現在フェーズ**: Phase 0（基盤構築）

---

## 📊 全体フェーズ概要

```
Phase 0 ████████░░░░░░░░░░░░ 40%  [現在] 基盤構築・ドキュメント整備
Phase 1 ░░░░░░░░░░░░░░░░░░░░  0%  データモデル・スキーマ設計
Phase 2 ░░░░░░░░░░░░░░░░░░░░  0%  コアプロセスエンジン実装
Phase 3 ░░░░░░░░░░░░░░░░░░░░  0%  AI/Agent統合レイヤー
Phase 4 ░░░░░░░░░░░░░░░░░░░░  0%  API レイヤー構築
Phase 5 ░░░░░░░░░░░░░░░░░░░░  0%  UI/ダッシュボード実装
Phase 6 ░░░░░░░░░░░░░░░░░░░░  0%  SLA自動監視エンジン
Phase 7 ░░░░░░░░░░░░░░░░░░░░  0%  テスト・品質保証
Phase 8 ░░░░░░░░░░░░░░░░░░░░  0%  本番対応・コンプライアンス
```

---

## 🔵 Phase 0: 基盤構築・ドキュメント整備（現在）

**目標**: Git/GitHub基盤確立、全設計ドキュメント作成、CI/CD整備

**期間**: 2026-03-02 ～ 2026-03-08（予定）

### 完了済みタスク
- [x] SERVICEMATRIX_CHARTER.md 作成
- [x] CLAUDE.md（統治規則）策定
- [x] README.md 作成
- [x] GitHub リポジトリ作成
- [x] git init + remote 接続
- [x] .gitignore 設定
- [x] .github/workflows/ci.yml 設定
- [x] .github/workflows/pr-governance.yml 設定
- [x] docs/ フォルダ構造作成

### 進行中タスク
- [ ] docs/00_foundation/ 全ファイル作成（Agent: foundation-governance）
- [ ] docs/01_governance/ 全ファイル作成（Agent: foundation-governance）
- [ ] docs/02_architecture/ 全ファイル作成（Agent: architecture-devops）
- [ ] docs/03_process/ 全ファイル作成（Agent: process-operations）
- [ ] docs/04_agents_ai/ 全ファイル作成（Agent: ai-security）
- [ ] docs/05_devops/ 全ファイル作成（Agent: architecture-devops）
- [ ] docs/06_security_compliance/ 全ファイル作成（Agent: ai-security）
- [ ] docs/07_sla_metrics/ 全ファイル作成（Agent: metrics-cmdb-data）
- [ ] docs/08_operations/ 全ファイル作成（Agent: process-operations）
- [ ] docs/09_ui_ux/ 全ファイル作成（Agent: quality-ui-audit）
- [ ] docs/10_cmdb/ 全ファイル作成（Agent: metrics-cmdb-data）
- [ ] docs/11_data_model/ 全ファイル作成（Agent: metrics-cmdb-data）
- [ ] docs/12_risk_management/ 全ファイル作成（Agent: quality-ui-audit）
- [ ] docs/13_testing_quality/ 全ファイル作成（Agent: quality-ui-audit）
- [ ] docs/14_release_management/ 全ファイル作成（Agent: process-operations）
- [ ] docs/15_audit_evidence/ 全ファイル作成（Agent: quality-ui-audit）
- [ ] docs/16_external_integration/ 全ファイル作成（Agent: quality-ui-audit）
- [ ] docs/99_appendix/ 全ファイル作成（Agent: quality-ui-audit）
- [ ] 初回 git commit + push

### Phase 0 完了基準
- 全 docs/ ドキュメント（60+ファイル）作成完了
- GitHub Actions CI が main ブランチで通過
- PR テンプレート整備完了

---

## 🟡 Phase 1: データモデル・スキーマ設計

**目標**: システム全体のデータ構造を確定し、実装の土台を固める

**依存**: Phase 0 完了

### 主要タスク
- [ ] **データベース選定**: PostgreSQL or SQLite（軽量版）
- [ ] **ORM/スキーマ定義**: SQLAlchemy or Prisma
- [ ] **Incident テーブル設計**
  ```sql
  incidents(id, title, description, priority, status, category,
            reporter_id, assignee_id, ci_id, sla_deadline,
            created_at, updated_at, resolved_at, closed_at)
  ```
- [ ] **Change テーブル設計**
  ```sql
  changes(id, title, type, risk_score, status, requested_by,
          approved_by, cab_required, scheduled_date,
          created_at, updated_at, implemented_at)
  ```
- [ ] **Problem テーブル設計**
  ```sql
  problems(id, title, root_cause, workaround, status,
           related_incidents[], created_at, resolved_at)
  ```
- [ ] **Request テーブル設計**
- [ ] **CMDB テーブル設計**（CI, Relationships）
- [ ] **SLA テーブル設計**（definitions, measurements, breaches）
- [ ] **AuditLog テーブル設計**
- [ ] **User/Team テーブル設計**
- [ ] マイグレーションファイル作成
- [ ] テストデータシード作成

### 技術スタック候補（Phase 1 確定予定）
- **言語**: Python 3.12+
- **フレームワーク**: FastAPI
- **DB**: PostgreSQL 16
- **ORM**: SQLAlchemy 2.0 + Alembic
- **バリデーション**: Pydantic v2

---

## 🟠 Phase 2: コアプロセスエンジン実装

**目標**: Incident / Change / Problem / Request 管理の中核ロジック実装

**依存**: Phase 1 完了

### 主要タスク
- [ ] **Incident Management**
  - [ ] Incident 作成・更新・クローズAPI
  - [ ] 優先度自動判定ロジック
  - [ ] SLA タイマー開始・監視
  - [ ] GitHub Issues 自動作成連携
  - [ ] エスカレーション自動発火ロジック
- [ ] **Change Management**
  - [ ] RFC 作成・審査フロー
  - [ ] CAB 承認ロジック（GitHub PR ベース）
  - [ ] リスクスコア自動算出
  - [ ] 変更カレンダー管理
- [ ] **Problem Management**
  - [ ] Incident → Problem 連携
  - [ ] RCA テンプレート生成
  - [ ] KEDB 登録・検索
- [ ] **Request Management**
  - [ ] サービスカタログ定義
  - [ ] リクエスト承認フロー
- [ ] **GitHub Webhook 受信処理**
  - [ ] Issues イベント処理
  - [ ] PR イベント処理
  - [ ] Actions 完了イベント処理

---

## 🔴 Phase 3: AI/Agent統合レイヤー

**目標**: ClaudeCode Agent Teams を ServiceMatrix の知性エンジンとして統合

**依存**: Phase 2 完了

### 主要タスク
- [ ] **AI トリアージエンジン**
  - [ ] Incident 内容から優先度自動判定
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

## 🟣 Phase 4: API レイヤー構築

**目標**: RESTful API による外部連携インターフェース整備

**依存**: Phase 2 完了（Phase 3 と並行可）

### 主要タスク
- [ ] **FastAPI ルーター設計**
  - [ ] `/api/v1/incidents` - Incident CRUD
  - [ ] `/api/v1/changes` - Change CRUD + 承認フロー
  - [ ] `/api/v1/problems` - Problem 管理
  - [ ] `/api/v1/requests` - Request 管理
  - [ ] `/api/v1/sla` - SLA 照会・違反通知
  - [ ] `/api/v1/cmdb/cis` - CI 管理
  - [ ] `/api/v1/audit-logs` - 監査ログ照会
  - [ ] `/api/v1/ai/analyze` - AI 分析リクエスト
- [ ] **認証・認可**
  - [ ] GitHub OAuth 連携
  - [ ] JWT トークン発行
  - [ ] RBAC ミドルウェア
- [ ] **API ドキュメント（OpenAPI/Swagger）**
- [ ] **Webhook 送信機能**
  - [ ] Incident 作成時 Webhook
  - [ ] SLA 違反時 Webhook
  - [ ] Change 承認時 Webhook

---

## 🔵 Phase 5: UI/ダッシュボード実装

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

## ⚪ Phase 6: SLA自動監視エンジン

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

## ⚪ Phase 7: テスト・品質保証

**目標**: 全レイヤーのテストカバレッジ確保

**依存**: Phase 2～5 実装進捗に応じて並行実施

### 主要タスク
- [ ] **Unit テスト** (目標: 80%+ カバレッジ)
  - [ ] プロセスロジックのユニットテスト
  - [ ] SLA 計算ロジックのユニットテスト
  - [ ] AI スコアリングロジックのユニットテスト
- [ ] **Integration テスト**
  - [ ] API エンドポイントテスト
  - [ ] DB 連携テスト
  - [ ] GitHub API モック連携テスト
- [ ] **E2E テスト** (Playwright)
  - [ ] Incident 作成～クローズフロー
  - [ ] Change 申請～承認フロー
  - [ ] SLA 違反検知フロー
- [ ] **セキュリティテスト**
  - [ ] OWASP Top 10 チェック
  - [ ] 依存パッケージ脆弱性スキャン（Dependabot）
- [ ] **パフォーマンステスト**
  - [ ] 負荷テスト（同時100ユーザー）
  - [ ] API レスポンスタイム目標: 200ms以下

---

## ⚪ Phase 8: 本番対応・コンプライアンス

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
| M0: 基盤確立 | 2026-03-08 | 🔄 進行中 |
| M1: データモデル確定 | 2026-03-22 | ⏳ 未着手 |
| M2: コアAPI MVP | 2026-04-12 | ⏳ 未着手 |
| M3: AI統合 α版 | 2026-04-30 | ⏳ 未着手 |
| M4: UI β版 | 2026-05-20 | ⏳ 未着手 |
| M5: SLA自動監視稼働 | 2026-06-07 | ⏳ 未着手 |
| M6: テスト完備版 | 2026-06-28 | ⏳ 未着手 |
| M7: 本番リリース v1.0 | 2026-07-31 | ⏳ 未着手 |

---

## 🔗 関連ドキュメント

- [SERVICEMATRIX_CHARTER.md](./SERVICEMATRIX_CHARTER.md)
- [docs/02_architecture/SYSTEM_ARCHITECTURE_OVERVIEW.md](./docs/02_architecture/SYSTEM_ARCHITECTURE_OVERVIEW.md)
- [docs/05_devops/BRANCH_STRATEGY.md](./docs/05_devops/BRANCH_STRATEGY.md)
- [docs/05_devops/CI_CD_PIPELINE_ARCHITECTURE.md](./docs/05_devops/CI_CD_PIPELINE_ARCHITECTURE.md)
- [docs/07_sla_metrics/SLA_DEFINITION.md](./docs/07_sla_metrics/SLA_DEFINITION.md)
