# E2E テスト仕様

> **実装ステップ**: Step 13
> **テストフレームワーク**: pytest + TestClient（FastAPI）
> **テストディレクトリ**: `tests/e2e/`

---

## 概要

Incident および Change の実運用フローを網羅するエンドツーエンドシナリオテスト。
実DBを使わずインメモリSQLiteで完結し、CIで毎回実行される。

---

## テストシナリオ

### Incident ライフサイクル（`tests/e2e/test_incident_lifecycle.py`）

| シナリオ | 内容 |
|----------|------|
| 全フロー | Incident作成 → In_Progress → Resolved → Closed |
| 一覧取得 | 一覧取得・ステータスフィルタリング |
| SLA確認 | SLAデッドライン自動設定の確認 |
| 不正遷移 | 無効なステータス遷移のエラーハンドリング |
| 未認証 | 認証なしアクセス拒否（401確認） |

### Change 承認フロー（`tests/e2e/test_change_approval_flow.py`）

| シナリオ | 内容 |
|----------|------|
| 通常フロー | Change作成 → Review → Approved → Implementing → Completed |
| CAB却下 | CAB却下 → 再申請フロー |
| リスク比較 | リスクスコアの自動算出・比較 |

---

## 実行方法

```bash
# E2Eテストのみ実行
pytest tests/e2e/ -v

# 全テスト実行（162テスト）
pytest --no-header -q

# カバレッジ付き実行
pytest --cov=src/servicematrix --cov-report=term-missing
```

---

## CI統合

GitHub Actions CI（`.github/workflows/ci.yml`）にて自動実行。
カバレッジ閾値: **67%**（`pyproject.toml` の `[tool.coverage.report]` で設定）。

---

## 関連ドキュメント

- [docs/13_testing_quality/TEST_STRATEGY.md](../13_testing_quality/TEST_STRATEGY.md)
- [docs/13_testing_quality/UNIT_TEST_POLICY.md](../13_testing_quality/UNIT_TEST_POLICY.md)
- [docs/13_testing_quality/INTEGRATION_TEST_MODEL.md](../13_testing_quality/INTEGRATION_TEST_MODEL.md)
