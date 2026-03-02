# 決定事項ログ

ServiceMatrix Decision Log

Version: 1.0
Status: Active
Classification: Internal Governance Document
Last Updated: 2026-03-02

---

## 1. 概要

本ドキュメントは、ServiceMatrix プロジェクトにおける重要な技術的・
設計的・ガバナンス的決定を記録する。
決定の背景・選択肢・判断根拠を残すことで、将来の意思決定の参考とする。

---

## 2. 決定事項記録フォーマット

各決定は以下の形式で記録する。

```
決定 ID: ADR-{連番}
タイトル: {決定の簡潔な名称}
状態: Active / Superseded / Deprecated
日付: YYYY-MM-DD
決定者: {役職/名前}
関連 Issue: #{GitHub Issue 番号}

背景:
  {なぜこの決定が必要だったか}

検討した選択肢:
  Option A: {内容}
  Option B: {内容}

決定:
  {採用した選択肢と理由}

結果:
  {この決定がもたらす影響}
```

---

## 3. アーキテクチャ決定記録

### ADR-001: フロントエンドフレームワーク選定

| 項目 | 内容 |
|------|------|
| 状態 | Active |
| 日付 | 2026-03-01 |
| 決定者 | テックリード |

**背景:** ServiceMatrix のフロントエンドを開発するにあたり、フレームワークの選定が必要だった。

**検討した選択肢:**
- Option A: Next.js (React)
- Option B: Nuxt.js (Vue)
- Option C: SvelteKit

**決定:** Next.js を採用する。

**理由:**
- React エコシステムの豊富なライブラリ群
- App Router による優れたサーバーサイドレンダリング
- TypeScript との優れた統合
- Vercel/AWS 等のホスティングオプションの豊富さ
- チームの既存スキルセットとの適合

**結果:** フロントエンドは Next.js + TypeScript で構築。

---

### ADR-002: バックエンドフレームワーク選定

| 項目 | 内容 |
|------|------|
| 状態 | Active |
| 日付 | 2026-03-01 |
| 決定者 | テックリード |

**背景:** バックエンド API サーバーのフレームワーク選定が必要だった。

**検討した選択肢:**
- Option A: FastAPI (Python)
- Option B: NestJS (TypeScript)
- Option C: Go + Gin

**決定:** FastAPI を採用する。

**理由:**
- Python 3.12 の非同期処理（asyncio）の成熟
- 自動 OpenAPI ドキュメント生成
- SQLAlchemy 2.0 との優れた統合
- Claude AI SDK との親和性
- データ処理・分析系ライブラリの豊富さ

**結果:** バックエンドは Python 3.12 + FastAPI + SQLAlchemy 2.0 で構築。

---

### ADR-003: データベース選定

| 項目 | 内容 |
|------|------|
| 状態 | Active |
| 日付 | 2026-03-01 |
| 決定者 | テックリード |

**背景:** メインデータベースの選定が必要だった。

**検討した選択肢:**
- Option A: PostgreSQL
- Option B: MySQL
- Option C: MongoDB（ドキュメント DB）

**決定:** PostgreSQL 16 を採用する。

**理由:**
- JSONB 型による柔軟なスキーマレスデータ保存
- 全文検索の組み込みサポート
- 強力なトランザクション保証（J-SOX 対応）
- pg_stat_statements によるクエリ分析
- 豊富な拡張機能（pgcrypto, uuid-ossp 等）

**結果:** 主要データストアとして PostgreSQL 16 を使用。キャッシュに Redis 7 を補助使用。

---

### ADR-004: AI 自律レベルの初期設定

| 項目 | 内容 |
|------|------|
| 状態 | Active |
| 日付 | 2026-03-01 |
| 決定者 | CTO + CISO |

**背景:** AI エージェントの自律度をどのレベルから開始するか決定が必要だった。

**検討した選択肢:**
- Option A: L0（完全手動）
- Option B: L1（助言のみ）
- Option C: L2（半自動）
- Option D: L3（条件付き自動）

**決定:** L1（助言のみ）から開始し、段階的に向上させる。

**理由:**
- J-SOX IT 全般統制の要件（AI 判断の人間レビュー必須）
- 初期段階での AI 信頼性確立の必要性
- 誤った AI 判断による業務影響リスクの最小化
- 段階的学習・改善サイクルの構築

**結果:** 初期リリースでは AI は提案のみを行い、実行はすべて人間が承認する L1 モードで運用。

---

### ADR-005: GitHub ネイティブアーキテクチャの採用

| 項目 | 内容 |
|------|------|
| 状態 | Active |
| 日付 | 2026-03-01 |
| 決定者 | プロジェクトリード |

**背景:** ITSM ワークフローをどのシステムを中心に構築するか決定が必要だった。

**検討した選択肢:**
- Option A: ServiceNow を基盤として使用
- Option B: GitHub を中心とした GitHubネイティブ設計
- Option C: 独自のカスタム ITSM エンジン

**決定:** GitHub ネイティブアーキテクチャを採用する。

**理由:**
- 開発チームがすでに GitHub を日常的に使用
- Issue/PR/Actions の組み合わせで豊富なワークフロー実現
- CI/CD との自然な統合
- 変更管理と開発ワークフローの統一
- ライセンスコスト削減

**結果:** GitHub Issue が ITSM エンティティのシステムオブレコードとなり、ServiceMatrix と双方向同期する。

---

### ADR-006: テストフレームワーク選定

| 項目 | 内容 |
|------|------|
| 状態 | Active |
| 日付 | 2026-03-01 |
| 決定者 | テックリード |

**背景:** フロントエンド・バックエンドのテストフレームワーク選定が必要だった。

**検討した選択肢:**
- Option A: Jest
- Option B: Vitest
- Option C: Mocha + Chai

**決定:** Vitest を採用する（フロントエンド・バックエンド統一）。

**理由:**
- Vite ベースで高速（Jest 比 2-4 倍）
- ESM ネイティブサポート
- Jest 互換 API で移行コスト低減
- フロントエンド・バックエンドでツールを統一できる

**結果:** 全テスト（ユニット・統合）で Vitest を使用。E2E は Playwright を使用。

---

### ADR-007: バージョニング戦略

| 項目 | 内容 |
|------|------|
| 状態 | Active |
| 日付 | 2026-03-01 |
| 決定者 | テックリード |

**背景:** リリースバージョン管理の方式を決定する必要があった。

**検討した選択肢:**
- Option A: カレンダーバージョニング（CalVer）
- Option B: セマンティックバージョニング（SemVer）
- Option C: 独自バージョニング

**決定:** Semantic Versioning 2.0.0 を採用する。

**理由:**
- MAJOR.MINOR.PATCH の明確な意味
- Conventional Commits との自動連携（release-please）
- API バージョン管理との整合性
- エンタープライズ製品として普及している標準

**結果:** Git タグ v{MAJOR}.{MINOR}.{PATCH} 形式でバージョン管理。CHANGELOG は release-please で自動生成。

---

## 4. 決定事項の管理規則

### 4.1 記録対象

以下に該当する決定は本ログに記録する。

| 記録対象 | 例 |
|---------|-----|
| アーキテクチャ上の重要な選択 | フレームワーク選定・DB 選定 |
| ガバナンスポリシーの制定 | AI 自律レベル・承認フロー |
| セキュリティ方針 | 認証方式・暗号化標準 |
| 技術的負債の受入 | 既知の制約を認識して採用した設計 |
| 廃止された選択肢の記録 | 検討したが採用しなかった技術 |

### 4.2 決定の状態管理

| 状態 | 説明 |
|------|------|
| Active | 現在有効な決定 |
| Superseded | 後継の ADR によって置き換えられた |
| Deprecated | 廃止されたが記録として残す |

---

## 5. 関連ドキュメント

| ドキュメント | 参照先 |
|---|---|
| オープン課題 | [OPEN_QUESTIONS.md](./OPEN_QUESTIONS.md) |
| 改訂履歴 | [REVISION_HISTORY.md](./REVISION_HISTORY.md) |
| ServiceMatrix 憲章 | [SERVICEMATRIX_CHARTER.md](../00_foundation/SERVICEMATRIX_CHARTER.md) |
| 意思決定フレームワーク | [DECISION_FRAMEWORK.md](../00_foundation/DECISION_FRAMEWORK.md) |

---

*本ドキュメントは ServiceMatrix プロジェクトの統治原則に基づき管理される。*
*変更は Change Issue → PR → CI検証 → 承認 のフローに従うこと。*
