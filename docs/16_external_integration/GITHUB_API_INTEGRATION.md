# GitHub API 統合仕様

ServiceMatrix GitHub API Integration Specification

Version: 1.0
Status: Active
Classification: Internal Technical Document
Last Updated: 2026-03-02

---

## 1. 概要

本ドキュメントは、ServiceMatrix と GitHub API の統合仕様を定義する。
ServiceMatrix は GitHub を中心とした GitHubネイティブ アーキテクチャを採用しており、
Issue・PR・Webhook を通じたガバナンスワークフローを実現する。

---

## 2. GitHub API 利用方針

### 2.1 基本方針

| 原則 | 内容 |
|------|------|
| API優先 | GitHub UI 操作ではなく API 経由で操作を統一する |
| 冪等性 | 同一操作を複数回実行しても結果が変わらない設計 |
| 最小権限 | 必要最小限のスコープのみ要求する |
| エラー耐性 | レート制限・タイムアウトに対応したリトライ設計 |
| 監査証跡 | すべての API 呼び出しを監査ログに記録する |

### 2.2 認証方式

| 用途 | 認証方式 | スコープ |
|------|---------|---------|
| CI/CD パイプライン | GitHub Actions GITHUB_TOKEN | repo, issues, pull_requests |
| バックエンドサービス | GitHub App (Installation Token) | issues:write, pull_requests:write, contents:read |
| Webhook 受信 | Webhook Secret による署名検証 | - |
| 管理者操作 | PAT（Personal Access Token）Fine-grained | repo, admin |

### 2.3 レート制限対応

| 種別 | 制限値 | 対応策 |
|------|--------|--------|
| REST API（認証済み） | 5,000 req/時 | キャッシュ + リトライ |
| GraphQL API | 5,000 ポイント/時 | ポイント計算 + 最適化 |
| Search API | 30 req/分 | バッチ処理 + バックオフ |
| GitHub App | 15,000 req/時 | App 認証優先使用 |

---

## 3. Issue 統合

### 3.1 Issue 作成仕様

ServiceMatrix の ITSM プロセス（インシデント・変更・問題）は GitHub Issue と連携する。

| ITSM エンティティ | GitHub Issue 種別 | ラベル |
|-----------------|-----------------|-------|
| インシデント（P1/P2） | Bug / Incident | incident, priority:p1 |
| 変更要求（RFC） | Feature / RFC | change-request, risk:medium |
| 問題管理 | Bug / Problem | problem, root-cause |
| サービス要求 | Feature Request | service-request |

```
Issue作成ペイロード（例）:
  endpoint: POST /repos/{owner}/{repo}/issues
  payload:
    title: "[INC-{id}] {インシデントタイトル}"
    body: |
      ## インシデント概要
      - 重要度: {priority}
      - 発生日時: {occurred_at}
      - 影響サービス: {affected_services}
      - 担当者: @{assignee}

      ## 詳細
      {description}

      ## SLA期限
      - 応答期限: {response_deadline}
      - 解決期限: {resolution_deadline}
    labels: ["incident", "priority:{priority_lower}"]
    assignees: ["{assignee_login}"]
    milestone: {current_sprint_id}
```

### 3.2 Issue 更新仕様

| 操作 | エンドポイント | 用途 |
|------|--------------|------|
| ステータス更新 | PATCH /repos/{owner}/{repo}/issues/{issue_number} | Open/Closed |
| コメント追加 | POST /repos/{owner}/{repo}/issues/{issue_number}/comments | 進捗更新 |
| ラベル変更 | PUT /repos/{owner}/{repo}/issues/{issue_number}/labels | 優先度変更 |
| アサイニー変更 | PATCH /repos/{owner}/{repo}/issues/{issue_number} | 担当者変更 |

### 3.3 Issue 検索仕様

| 検索種別 | クエリ例 | 用途 |
|---------|---------|------|
| 未解決インシデント | `is:open label:incident` | ダッシュボード |
| P1 インシデント | `is:open label:incident label:priority:p1` | SLA 監視 |
| 期限超過 | `is:open label:incident created:<{sla_deadline}` | SLA 違反検出 |
| 特定担当者 | `is:open assignee:{login} label:incident` | 個人ワークリスト |

---

## 4. Pull Request 統合

### 4.1 PR 作成仕様

変更管理ワークフローにおける PR 作成仕様。

```
PR作成ペイロード（例）:
  endpoint: POST /repos/{owner}/{repo}/pulls
  payload:
    title: "[RFC-{id}] {変更タイトル}"
    body: |
      ## 変更概要
      関連Issue: #{issue_number}
      変更種別: {change_type}
      リスクレベル: {risk_level}

      ## 変更内容
      {description}

      ## レビュアー承認要件
      - [ ] テックリード承認
      - [ ] セキュリティレビュー（高リスクの場合）
      - [ ] CAB承認（緊急変更の場合）

      ## ロールバック手順
      {rollback_plan}
    head: "feature/{rfc_id}-{branch_slug}"
    base: "main"
    draft: false
    maintainer_can_modify: true
```

### 4.2 PR レビュー制御

| 操作 | エンドポイント | 用途 |
|------|--------------|------|
| レビュアー追加 | POST /repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers | 自動アサイン |
| レビュー提出 | POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews | 承認/却下 |
| Branch Protection | PUT /repos/{owner}/{repo}/branches/{branch}/protection | 統治設定 |

### 4.3 SoD（職務分離）検証

ServiceMatrix では PR 作成者と承認者の同一性を禁止する。

```
SoD検証ロジック:
  1. PR作成者（author）を取得
  2. レビュー承認者（approved_reviewers）を取得
  3. author ∈ approved_reviewers の場合 → 承認を拒否
  4. 拒否理由を PR コメントに記録
  5. 監査ログに記録（sod_violations テーブル）
```

---

## 5. Webhook 統合

### 5.1 Webhook イベント購読

| イベント | 目的 | 処理 |
|---------|------|------|
| `issues` | Issue 作成・更新の検知 | ITSM エンティティ同期 |
| `pull_request` | PR ライフサイクル管理 | 承認フロー制御 |
| `pull_request_review` | レビュー承認検知 | SoD 検証 |
| `push` | コード変更検知 | CI トリガー |
| `workflow_run` | CI/CD 結果受信 | 品質ゲート評価 |
| `deployment` | デプロイ状態追跡 | SLA 影響分析 |
| `release` | リリース検知 | バージョン管理同期 |

### 5.2 Webhook 署名検証

```
署名検証アルゴリズム:
  1. X-Hub-Signature-256 ヘッダーを取得
  2. WEBHOOK_SECRET でペイロードの HMAC-SHA256 を計算
  3. タイミング攻撃対策のため hmac.compare_digest() で比較
  4. 不一致の場合 400 Bad Request を返却
  5. 検証結果を監査ログに記録
```

---

## 6. GitHub App 設計

### 6.1 GitHub App 設定

| 項目 | 設定値 |
|------|--------|
| App 名 | ServiceMatrix Governance Bot |
| Installation 対象 | ServiceMatrix 組織全リポジトリ |
| Webhook URL | `https://{servicematrix-domain}/api/webhooks/github` |
| Webhook Secret | 環境変数 GITHUB_WEBHOOK_SECRET |

### 6.2 必要権限

| リソース | 権限 | 理由 |
|---------|------|------|
| Issues | Read & Write | ITSM 同期 |
| Pull requests | Read & Write | 変更管理 |
| Contents | Read | コード参照 |
| Checks | Read & Write | CI 品質ゲート |
| Deployments | Read & Write | デプロイ管理 |
| Metadata | Read | リポジトリ情報 |

### 6.3 Installation Token 取得フロー

```
Token取得フロー:
  1. GitHub App の Private Key で JWT を生成（有効期限 10 分）
  2. GET /app/installations で Installation ID を取得
  3. POST /app/installations/{id}/access_tokens で Token 取得
  4. Token をセキュアストレージにキャッシュ（有効期限 1 時間）
  5. Token 期限切れ前に自動更新
```

---

## 7. エラーハンドリングと耐障害設計

### 7.1 リトライ戦略

| エラー種別 | HTTP ステータス | リトライ | バックオフ |
|----------|---------------|---------|-----------|
| レート制限 | 429 | Yes | Retry-After ヘッダー準拠 |
| サーバーエラー | 500, 502, 503 | Yes | 指数バックオフ（最大 3 回）|
| タイムアウト | - | Yes | 10 秒後に 1 回リトライ |
| 認証エラー | 401 | Token 更新後 1 回 | - |
| 認可エラー | 403 | No | アラート発報 |
| Not Found | 404 | No | エラーログ記録 |

### 7.2 サーキットブレーカー設定

| パラメータ | 値 |
|----------|-----|
| 失敗閾値 | 連続 5 回失敗 |
| オープン期間 | 60 秒 |
| ハーフオープン試行数 | 1 回 |
| タイムアウト | 30 秒 |

### 7.3 フォールバック動作

| シナリオ | フォールバック動作 |
|---------|-----------------|
| GitHub API 障害 | ローカルキャッシュから読み取り、書き込みはキュー保留 |
| Webhook 受信失敗 | 再配信キューに追加（最大 5 回）|
| Issue 作成失敗 | ServiceMatrix 内部 DB に保存し、非同期で再試行 |

---

## 8. セキュリティ考慮事項

### 8.1 秘密情報管理

| 情報 | 保存場所 | ローテーション |
|------|---------|--------------|
| GitHub App Private Key | Kubernetes Secret / Vault | 年次 |
| Webhook Secret | 環境変数（暗号化） | 四半期 |
| PAT（管理者用） | Vault | 月次 |

### 8.2 セキュリティ制約

- GitHub App の Private Key はコードリポジトリに含めない
- Webhook ペイロードは署名検証前にログ出力しない
- Issue/PR の本文に機密情報を含めない（PII、認証情報等）
- API レスポンスに含まれる個人情報は最小化してキャッシュする

---

## 9. モニタリングと可観測性

### 9.1 メトリクス

| メトリクス | 説明 | アラート閾値 |
|----------|------|------------|
| github_api_request_total | API 呼び出し総数 | - |
| github_api_error_rate | エラー率 | 5% 超過で Warning |
| github_api_rate_limit_remaining | レート制限残数 | 500 以下で Warning |
| github_webhook_processing_latency | Webhook 処理時間 | P95 > 5 秒で Warning |
| github_api_circuit_breaker_state | CB 状態 | Open 状態で Critical |

### 9.2 ログ形式

```json
{
  "timestamp": "2026-03-02T10:00:00Z",
  "service": "github-integration",
  "event_type": "api_call",
  "method": "POST",
  "endpoint": "/repos/org/repo/issues",
  "status_code": 201,
  "duration_ms": 234,
  "rate_limit_remaining": 4876,
  "correlation_id": "req-{uuid}",
  "user_id": "usr-{uuid}"
}
```

---

## 10. 関連ドキュメント

| ドキュメント | 参照先 |
|---|---|
| Webhook イベントモデル | [WEBHOOK_EVENT_MODEL.md](./WEBHOOK_EVENT_MODEL.md) |
| サードパーティ統合ポリシー | [THIRD_PARTY_INTEGRATION_POLICY.md](./THIRD_PARTY_INTEGRATION_POLICY.md) |
| PR ポリシー | [PULL_REQUEST_POLICY.md](../05_devops/PULL_REQUEST_POLICY.md) |
| セキュリティテストポリシー | [SECURITY_TEST_POLICY.md](../13_testing_quality/SECURITY_TEST_POLICY.md) |
| ServiceMatrix 憲章 | [SERVICEMATRIX_CHARTER.md](../00_foundation/SERVICEMATRIX_CHARTER.md) |

---

*本ドキュメントは ServiceMatrix プロジェクトの統治原則に基づき管理される。*
*変更は Change Issue → PR → CI検証 → 承認 のフローに従うこと。*
