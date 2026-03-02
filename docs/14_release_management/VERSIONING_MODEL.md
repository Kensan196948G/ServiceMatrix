# バージョニングモデル

ServiceMatrix Versioning Model

Version: 1.0
Status: Active
Classification: Internal Development Standard
Last Updated: 2026-03-02

---

## 1. 概要

本ドキュメントは、ServiceMatrix プロジェクトにおけるバージョン管理の方針・命名規則・運用手順を定義する。
Semantic Versioning 2.0.0 および Conventional Commits に準拠し、
変更履歴を一貫して管理することでリリースの透明性と監査可能性を確保する。

---

## 2. バージョン体系

### 2.1 Semantic Versioning（SemVer 2.0.0）

```
MAJOR.MINOR.PATCH[-PRERELEASE][+BUILDMETA]

例:
  1.0.0          - 正式リリース
  1.2.3          - メジャー1、マイナー2、パッチ3
  2.0.0-alpha.1  - メジャー2のアルファ版
  2.0.0-beta.2   - メジャー2のベータ版
  2.0.0-rc.1     - リリース候補1
```

### 2.2 バージョン番号の意味

| セグメント | 変更条件 | 例 |
|-----------|---------|-----|
| MAJOR | 後方互換性のないAPI変更、破壊的変更 | 認証方式の変更、APIエンドポイント削除 |
| MINOR | 後方互換性のある新機能追加 | 新しいAPIエンドポイント追加 |
| PATCH | 後方互換性のあるバグ修正 | バグ修正、パフォーマンス改善 |
| PRERELEASE | テスト・評価用のプレリリース版 | alpha, beta, rc |

### 2.3 初期バージョン方針

| フェーズ | バージョン範囲 | 説明 |
|---------|--------------|------|
| 開発中 | 0.x.x | APIは安定していない可能性がある |
| 最初の安定版 | 1.0.0 | 本番利用開始 |
| 安定運用 | 1.x.x 以降 | 後方互換性を維持 |

---

## 3. Conventional Commits

### 3.1 コミットメッセージ形式

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### 3.2 コミットタイプ一覧

| タイプ | バージョン影響 | 説明 | 例 |
|--------|-------------|------|-----|
| feat | MINOR | 新機能追加 | feat(incident): add priority escalation |
| fix | PATCH | バグ修正 | fix(sla): correct timer calculation |
| docs | なし | ドキュメント変更のみ | docs: update API reference |
| style | なし | コードスタイル変更 | style: format with prettier |
| refactor | なし | 機能変更なしのコード整理 | refactor(auth): extract token validator |
| perf | PATCH | パフォーマンス改善 | perf(query): add index for incident lookup |
| test | なし | テスト追加・修正 | test(unit): add incident service tests |
| build | なし | ビルドシステム変更 | build: upgrade to Node 20 |
| ci | なし | CI設定変更 | ci: add security scan step |
| chore | なし | その他の変更 | chore: update dependencies |
| revert | PATCH | 変更の取り消し | revert: revert "feat(auth): add SSO" |
| BREAKING CHANGE | MAJOR | 破壊的変更（フッターに記載） | feat!: change authentication API |

### 3.3 破壊的変更の記法

```
feat!: replace JWT with OAuth2 tokens

BREAKING CHANGE: The /auth/token endpoint now returns OAuth2 tokens.
Previous JWT tokens will not be accepted. Migration guide: docs/migration/auth-v2.md
```

---

## 4. リリースタグ管理

### 4.1 Gitタグ命名規則

| タグ種別 | 命名パターン | 例 |
|---------|------------|-----|
| 正式リリース | `v{MAJOR}.{MINOR}.{PATCH}` | v1.2.3 |
| アルファ版 | `v{MAJOR}.{MINOR}.{PATCH}-alpha.{N}` | v2.0.0-alpha.1 |
| ベータ版 | `v{MAJOR}.{MINOR}.{PATCH}-beta.{N}` | v2.0.0-beta.2 |
| リリース候補 | `v{MAJOR}.{MINOR}.{PATCH}-rc.{N}` | v2.0.0-rc.1 |

### 4.2 タグ作成手順

| ステップ | コマンド | 説明 |
|---------|---------|------|
| 1 | `git tag -a v1.2.3 -m "Release v1.2.3"` | 署名付きアノテーションタグ作成 |
| 2 | `git push origin v1.2.3` | タグをリモートにプッシュ |
| 3 | GitHub Releases 作成 | タグからリリースページを生成 |

### 4.3 タグ保護設定

| 設定 | 値 |
|------|-----|
| 保護パターン | `v*` |
| 作成権限 | Release Manager のみ |
| 削除権限 | Admin のみ |
| タグへの直接プッシュ | 禁止 |

---

## 5. CHANGELOG管理

### 5.1 CHANGELOGフォーマット（Keep a Changelog準拠）

```
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 追加された新機能

### Changed
- 既存機能の変更

### Deprecated
- 将来削除予定の機能

### Removed
- 削除された機能

### Fixed
- バグ修正

### Security
- セキュリティ修正

## [1.2.3] - 2026-03-02
...
```

### 5.2 CHANGELOG自動生成

| ツール | 用途 |
|--------|------|
| conventional-changelog | Conventional Commits からCHANGELOGを自動生成 |
| release-please | PR作成・バージョン更新・CHANGELOG更新の自動化 |

### 5.3 CHANGELOG更新タイミング

| タイミング | 方法 | 担当 |
|-----------|------|------|
| PR マージ時 | release-please が自動でCHANGELOGを更新するPR作成 | 自動 |
| リリース時 | [Unreleased] セクションをバージョン番号に変換 | release-please / Release Manager |

---

## 6. バージョンの適用範囲

### 6.1 コンポーネント別バージョン管理

| コンポーネント | バージョン方針 | 備考 |
|--------------|--------------|------|
| メインアプリケーション | プロジェクト共通バージョン | monorepo |
| API（REST） | OpenAPI spec にバージョン記載 | /api/v1/, /api/v2/ |
| データベーススキーマ | マイグレーションにタイムスタンプ付与 | 001_xxx, 002_xxx |
| ドキュメント | コード変更に同期 | 別バージョンは管理しない |
| GitHub Actions Workflow | コードと同期 | 別バージョンは管理しない |

### 6.2 API バージョニング

| 方針 | 説明 |
|------|------|
| URLパスベース | `/api/v1/`, `/api/v2/` でバージョンを示す |
| 後方互換性維持期間 | 旧バージョンは新バージョンリリース後 6ヶ月間サポート |
| 廃止通知 | 廃止6ヶ月前に Deprecated ヘッダーで通知 |
| Breaking Change | 必ずメジャーバージョンをインクリメント |

---

## 7. リリース番号の採番ルール

### 7.1 採番権限

| バージョン種別 | 採番権限 | 承認 |
|--------------|---------|------|
| MAJOR | テックリード提案 → Admin承認 | 必須 |
| MINOR | テックリード | 確認（承認不要） |
| PATCH | Release Manager | 確認（承認不要） |
| PRERELEASE | Release Manager | 確認（承認不要） |

### 7.2 バージョンアップのトリガー

| トリガー | バージョン変更 |
|---------|-------------|
| Breaking Change を含むリリース | MAJOR++ |
| 新機能を含むリリース（Breaking Changeなし） | MINOR++ |
| バグ修正のみのリリース | PATCH++ |
| セキュリティ緊急パッチ | PATCH++（緊急リリースプロセス） |
| 依存関係更新のみ | PATCH++ |

---

## 8. 関連ドキュメント

| ドキュメント | 参照先 |
|---|---|
| リリース戦略 | [RELEASE_STRATEGY.md](./RELEASE_STRATEGY.md) |
| デプロイポリシー | [DEPLOYMENT_POLICY.md](./DEPLOYMENT_POLICY.md) |
| ロールバック戦略 | [ROLLBACK_STRATEGY.md](./ROLLBACK_STRATEGY.md) |
| CI/CDパイプライン | [CI_CD_PIPELINE_ARCHITECTURE.md](../05_devops/CI_CD_PIPELINE_ARCHITECTURE.md) |
| ブランチ戦略 | [BRANCH_STRATEGY.md](../05_devops/BRANCH_STRATEGY.md) |

---

*本ドキュメントは ServiceMatrix プロジェクトの統治原則に基づき管理される。*
*変更は Change Issue → PR → CI検証 → 承認 のフローに従うこと。*
