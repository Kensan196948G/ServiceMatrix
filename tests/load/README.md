# 負荷テスト (k6)

## セットアップ

```bash
# k6 インストール (Ubuntu/Debian)
sudo apt-get install k6

# または brew
brew install k6
```

## 実行方法

### CIスモークテスト（10ユーザー×30秒）

```bash
k6 run tests/load/k6_smoke_test.js
```

### 本番負荷テスト（100ユーザー×10分）

```bash
k6 run tests/load/k6_full_test.js
```

### 環境変数指定

```bash
BASE_URL=http://api.example.com k6 run tests/load/k6_full_test.js
```

## 目標値

| メトリクス | 目標 |
|-----------|------|
| P99レスポンスタイム | 200ms以下 |
| エラーレート | 1%未満 |
| 同時ユーザー | 100 |
