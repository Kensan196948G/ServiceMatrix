# AI トリアージ機能仕様

> **実装ステップ**: Step 12
> **実装方式**: FastAPI BackgroundTasks（非同期・非ブロッキング）
> **実装場所**: `src/servicematrix/services/ai_triage.py`

---

## 概要

Incident作成時にバックグラウンドで自動実行される優先度・カテゴリ自動判定機能。

---

## 動作仕様

| 項目 | 内容 |
|------|------|
| トリガー | `POST /api/v1/incidents`（Incident新規作成時） |
| 実行方式 | FastAPI BackgroundTasks（非同期・非ブロッキング） |
| 判定ロジック | キーワードマッチング（LLMプロバイダー切り替え可能） |
| 結果反映 | Incident レコードの `priority` / `category` フィールドを更新 |

---

## 優先度判定ルール

| 優先度 | キーワード例 |
|--------|------------|
| Critical | down, outage, production, 障害, 停止 |
| High | error, failed, timeout, エラー, 失敗 |
| Medium | slow, degraded, intermittent |
| Low | その他 |

---

## カテゴリ判定ルール

| カテゴリ | キーワード例 |
|----------|------------|
| Security | security, breach, unauthorized |
| Network | network, connectivity, dns |
| Database | database, db, sql, query |
| Application | app, service, api |
| Infrastructure | server, cpu, memory, disk |

---

## LLMプロバイダー設定

環境変数 `AI_TRIAGE_PROVIDER` で切り替え。

| 設定値 | 説明 |
|--------|------|
| `keyword`（デフォルト） | キーワードベース（LLM不要・常時利用可） |
| `openai` | OpenAI API使用（`OPENAI_API_KEY` 必要） |
| `azure_openai` | Azure OpenAI使用（`AZURE_OPENAI_*` 設定必要） |
| `ollama` | ローカルOllama使用（`OLLAMA_BASE_URL` 必要） |

---

## 関連ドキュメント

- [docs/04_agents_ai/AI_GOVERNANCE_POLICY.md](../04_agents_ai/AI_GOVERNANCE_POLICY.md)
- [docs/04_agents_ai/AI_DECISION_LOGGING_MODEL.md](../04_agents_ai/AI_DECISION_LOGGING_MODEL.md)
