# ServiceMatrix セットアップガイド

## 対応プラットフォーム

| プラットフォーム | 自動起動方法 | 対応バージョン |
|---|---|---|
| Linux (Ubuntu) | systemd | Ubuntu 20.04 / 22.04 / 24.04 LTS |
| Windows 11 | Task Scheduler (SYSTEM権限) | Windows 11 / Windows Server 2022 |

---

## Linux (Ubuntu) セットアップ

### 前提条件

```bash
# Python 3.10以上
python3 --version

# Node.js 18以上（フロントエンド使用時）
node --version

# pip
pip3 --version
```

### インストール（一発セットアップ）

```bash
# リポジトリをクローン
git clone https://github.com/Kensan196948G/ServiceMatrix.git
cd ServiceMatrix

# インストールスクリプトを実行（root権限必要）
sudo bash scripts/linux/install-service.sh

# Dockerを使用する場合
sudo bash scripts/linux/install-service.sh --docker-only

# 開発環境（/opt/servicematrix へのコピーなし）
sudo bash scripts/linux/install-service.sh --dev
```

### インストール内容

インストールスクリプトは以下を自動実行します：

1. 依存関係チェック（Python3, Node.js, Docker）
2. `servicematrix` システムユーザー作成
3. `/opt/servicematrix` へプロジェクトコピー
4. Python 仮想環境（`.venv`）作成・依存関係インストール
5. フロントエンドビルド（`npm ci && npm run build`）
6. 動的IP・ポート競合チェックして `.env` 生成
7. systemd サービスファイルをインストール・有効化
8. UFW ファイアウォールルール追加

### systemd サービス管理

```bash
# バックエンド (FastAPI)
sudo systemctl start   servicematrix-backend
sudo systemctl stop    servicematrix-backend
sudo systemctl restart servicematrix-backend
sudo systemctl status  servicematrix-backend

# フロントエンド (Next.js)
sudo systemctl start   servicematrix-frontend
sudo systemctl stop    servicematrix-frontend
sudo systemctl status  servicematrix-frontend

# Docker モード（docker-compose.prod.yml を使用）
sudo systemctl start   servicematrix-docker
sudo systemctl stop    servicematrix-docker
sudo systemctl status  servicematrix-docker

# ログ確認
sudo journalctl -u servicematrix-backend -f
sudo journalctl -u servicematrix-frontend -f
```

### 起動フロー

```
PC起動
  └─ systemd (multi-user.target)
       ├─ network.target
       ├─ postgresql.service  (利用可能な場合)
       ├─ redis.service        (利用可能な場合)
       └─ servicematrix-backend.service
            ├─ ExecStartPre: check-ports.sh  ← ポート競合検出・IP取得・.env更新
            ├─ ExecStart:    start-backend.sh ← uvicorn または docker-compose 起動
            └─ servicematrix-frontend.service (After=backend)
                 └─ start-frontend.sh ← npm start または standalone
```

### ポート競合時の動作

| サービス | デフォルトポート | 競合時の代替 |
|---|---|---|
| バックエンド | 8000 | 8001, 8002, ..., 8009 |
| フロントエンド | 3000 | 3001, 3002, ..., 3009 |
| PostgreSQL | 5432 | 5433, 5434, ..., 5441 |
| Redis | 6379 | 6380, 6381, ..., 6388 |

### アンインストール

```bash
sudo bash scripts/linux/uninstall-service.sh

# 設定ファイルも完全削除する場合
sudo bash scripts/linux/uninstall-service.sh --purge
```

### クロスプラットフォーム Python マネージャー（代替手段）

```bash
# 起動
python3 scripts/service_manager.py start

# 停止
python3 scripts/service_manager.py stop

# 状態確認
python3 scripts/service_manager.py status

# .env 環境設定再生成
python3 scripts/service_manager.py setup
```

---

## Windows 11 セットアップ

### 前提条件

- Python 3.10以上（https://www.python.org）
  - インストール時に「Add Python to PATH」にチェック
- Node.js 18以上（https://nodejs.org）（フロントエンド使用時）
- PowerShell 5.1以上（Windows 11 標準搭載）

### インストール（管理者 PowerShell で実行）

```powershell
# リポジトリをクローン
git clone https://github.com/Kensan196948G/ServiceMatrix.git
cd ServiceMatrix

# 実行ポリシーを一時的に許可（このプロセスのみ）
Set-ExecutionPolicy Bypass -Scope Process -Force

# インストーラー実行（管理者権限必要）
.\scripts\windows\Install-ServiceMatrix.ps1
```

### インストール内容

インストールスクリプトは以下を自動実行します：

1. 依存関係チェック（Python, Node.js）
2. Python 仮想環境（`.venv`）作成・依存関係インストール
3. フロントエンドビルド（`npm ci && npm run build`）
4. 動的IP・ポート競合チェックして `.env` 生成
5. **Task Scheduler に自動起動タスクを登録（SYSTEM権限・ログイン前起動）**
6. Windows Firewall インバウンドルール追加（TCP 8000, 3000）

### サービス管理

```powershell
# 起動
.\scripts\windows\Start-ServiceMatrix.ps1

# 停止
.\scripts\windows\Stop-ServiceMatrix.ps1

# 状態確認
.\scripts\windows\Get-ServiceMatrixStatus.ps1

# アンインストール
.\scripts\windows\Uninstall-ServiceMatrix.ps1
```

### 自動起動の仕組み

```
PC電源ON
  └─ Windows 起動
       └─ Task Scheduler (ServiceMatrix-Startup タスク)
            ├─ タイミング: AtStartup (ログイン前・30秒遅延)
            ├─ 実行ユーザー: SYSTEM (S-1-5-18)
            ├─ 権限: HighestAvailable
            └─ Start-ServiceMatrix.ps1
                 ├─ 動的IP取得 (Get-NetIPAddress)
                 ├─ ポート競合チェック (Get-NetTCPConnection)
                 ├─ .env 更新
                 ├─ uvicorn バックグラウンド起動
                 └─ npm start バックグラウンド起動
```

### Task Scheduler XML を使った手動登録

```powershell
# SCRIPT_PATH を実際のパスに置換してから登録
$xmlContent = Get-Content .\scripts\windows\ServiceMatrix-Startup.xml | Out-String
$xmlContent = $xmlContent -replace "SCRIPT_PATH", "C:\ServiceMatrix\scripts\windows\Start-ServiceMatrix.ps1"
$xmlContent = $xmlContent -replace "WORKING_DIR", "C:\ServiceMatrix"
Register-ScheduledTask -Xml $xmlContent -TaskName "ServiceMatrix-Startup" -Force
```

### ログ確認

```powershell
# イベントログ（サービス起動記録）
Get-EventLog -LogName Application -Source ServiceMatrix -Newest 20

# ファイルログ
Get-Content "$env:ProgramData\ServiceMatrix\startup.log" -Tail 50

# バックエンドログ
Get-Content .\logs\backend.log -Tail 50

# フロントエンドログ
Get-Content .\logs\frontend.log -Tail 50
```

### ポート競合時の動作

Windows版も Linux版と同様に自動で代替ポートを選択します。

---

## クロスプラットフォーム: Python service_manager.py

OS に依存しない統合管理ツールです。

```bash
# Linux
python3 scripts/service_manager.py start
python3 scripts/service_manager.py status

# Windows
python scripts\service_manager.py start
python scripts\service_manager.py status
```

### コマンド一覧

| コマンド | 説明 |
|---|---|
| `start` | 環境設定検出後にバックエンド・フロントエンドを起動 |
| `stop` | 全サービスを停止 |
| `restart` | 停止→起動 |
| `status` | 稼働状態・URL・ポートを表示 |
| `setup` | IPアドレス・ポート検出して `.env` を生成/更新 |

---

## .env ファイルの自動生成

### 手動で再生成する場合

```bash
# Linux/Mac
python3 scripts/generate_env.py

# 強制再生成（SECRET_KEY以外を更新）
python3 scripts/generate_env.py --force

# Windows
python scripts\generate_env.py
```

### 生成される主要設定

| 変数 | 説明 |
|---|---|
| `LOCAL_IP` | 自動検出されたローカルIPアドレス |
| `BACKEND_PORT` | 競合のない利用可能なポート（8000〜8009） |
| `FRONTEND_PORT` | 競合のない利用可能なポート（3000〜3009） |
| `BACKEND_URL` | `http://{LOCAL_IP}:{BACKEND_PORT}` |
| `FRONTEND_URL` | `http://{LOCAL_IP}:{FRONTEND_PORT}` |
| `SECRET_KEY` | 自動生成（既存値を引き継ぎ）|

---

## アクセスURL

セットアップ完了後、以下のURLでアクセスできます：

| サービス | URL |
|---|---|
| フロントエンド | `http://{LOCAL_IP}:{FRONTEND_PORT}` |
| バックエンド API | `http://{LOCAL_IP}:{BACKEND_PORT}` |
| API ドキュメント (Swagger) | `http://{LOCAL_IP}:{BACKEND_PORT}/docs` |
| ReDoc | `http://{LOCAL_IP}:{BACKEND_PORT}/redoc` |
| ヘルスチェック | `http://{LOCAL_IP}:{BACKEND_PORT}/health` |
| メトリクス (Prometheus) | `http://{LOCAL_IP}:{BACKEND_PORT}/metrics/prometheus` |

---

## トラブルシューティング

### Linux: サービスが起動しない

```bash
# エラー確認
sudo journalctl -u servicematrix-backend --no-pager -n 50

# 手動実行でエラーを確認
sudo -u servicematrix /opt/servicematrix/scripts/linux/start-backend.sh

# ポート確認
ss -tulpn | grep -E '8000|3000'

# .env 再生成
sudo -u servicematrix python3 /opt/servicematrix/scripts/generate_env.py
```

### Windows: タスクが起動しない

```powershell
# タスクの状態確認
Get-ScheduledTask -TaskName "ServiceMatrix-Startup" | Get-ScheduledTaskInfo

# イベントログでエラー確認
Get-WinEvent -LogName "Microsoft-Windows-TaskScheduler/Operational" | 
    Where-Object {$_.Message -like "*ServiceMatrix*"} | Select-Object -First 10

# 手動でスクリプトを管理者実行してデバッグ
powershell.exe -ExecutionPolicy Bypass -File .\scripts\windows\Start-ServiceMatrix.ps1
```

### ポート競合が解消されない

```bash
# 使用中のポートを確認 (Linux)
ss -tulpn | grep -E '8000|8001|3000|3001'

# 使用中のポートを確認 (Windows PowerShell)
Get-NetTCPConnection -State Listen | Where-Object {$_.LocalPort -in @(8000,8001,3000,3001)}

# .env を手動編集してポートを変更
nano .env  # Linux
notepad .env  # Windows
```
