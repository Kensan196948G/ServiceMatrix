#Requires -RunAsAdministrator
<#
.SYNOPSIS
    ServiceMatrix Windows 自動起動インストーラー
.DESCRIPTION
    ServiceMatrix を Windows 環境にインストールし、
    PC起動時に自動起動するよう Task Scheduler に登録します。
.NOTES
    PowerShell 5.1 対応
    管理者権限で実行してください
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 定数定義
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
$ScriptDir   = $PSScriptRoot
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir '..\..')).Path
$DataDir     = Join-Path $env:ProgramData 'ServiceMatrix'
$LogSource   = 'ServiceMatrix'
$TaskName    = 'ServiceMatrix-Startup'

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# イベントログ初期化
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function Initialize-EventLog {
    if (-not [System.Diagnostics.EventLog]::SourceExists($LogSource)) {
        New-EventLog -LogName Application -Source $LogSource
        Write-Host "[OK] イベントログソース '$LogSource' を登録しました。"
    }
}

function Write-Log {
    param(
        [string]$Message,
        [ValidateSet('Information','Warning','Error')]
        [string]$EntryType = 'Information'
    )
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $prefix = switch ($EntryType) {
        'Information' { '[INFO]' }
        'Warning'     { '[WARN]' }
        'Error'       { '[ERROR]' }
    }
    Write-Host "$timestamp $prefix $Message"
    try {
        Write-EventLog -LogName Application -Source $LogSource `
            -EventId 1000 -EntryType $EntryType -Message $Message
    } catch {
        # イベントログ書き込み失敗は無視
    }
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 依存ツール確認
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function Test-Prerequisites {
    Write-Log "依存ツールを確認しています..."

    $tools = @(
        @{ Name = 'python'; Args = '--version'; Label = 'Python 3' },
        @{ Name = 'pip';    Args = '--version'; Label = 'pip'      },
        @{ Name = 'node';   Args = '--version'; Label = 'Node.js'  },
        @{ Name = 'npm';    Args = '--version'; Label = 'npm'      }
    )

    $missing = @()
    foreach ($tool in $tools) {
        try {
            $ver = & $tool.Name $tool.Args 2>&1
            Write-Log "$($tool.Label) 確認済み: $ver"
        } catch {
            $missing += $tool.Label
            Write-Log "$($tool.Label) が見つかりません。" -EntryType Warning
        }
    }

    if ($missing.Count -gt 0) {
        throw "以下のツールがインストールされていません: $($missing -join ', ')`nインストール後に再実行してください。"
    }
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Python 仮想環境のセットアップ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function Initialize-PythonVenv {
    Write-Log "Python 仮想環境をセットアップしています..."

    $venvPath = Join-Path $ProjectRoot '.venv'
    if (-not (Test-Path $venvPath)) {
        Write-Log "仮想環境を作成します: $venvPath"
        & python -m venv $venvPath
    } else {
        Write-Log "既存の仮想環境を使用します: $venvPath"
    }

    $pipExe = Join-Path $venvPath 'Scripts\pip.exe'
    if (-not (Test-Path $pipExe)) {
        throw "仮想環境の pip が見つかりません: $pipExe"
    }

    Write-Log "pip install を実行しています..."
    & $pipExe install --upgrade pip --quiet
    & $pipExe install -r (Join-Path $ProjectRoot 'requirements.txt') --quiet 2>&1 | ForEach-Object {
        if ($_ -match 'error') { Write-Log $_ -EntryType Warning }
    }
    Write-Log "Python パッケージのインストールが完了しました。"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# フロントエンド依存関係インストール
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function Initialize-Frontend {
    Write-Log "フロントエンド依存関係をインストールしています..."

    $frontendDir = Join-Path $ProjectRoot 'frontend'
    if (-not (Test-Path (Join-Path $frontendDir 'package.json'))) {
        throw "frontend/package.json が見つかりません: $frontendDir"
    }

    Push-Location $frontendDir
    try {
        Write-Log "npm ci を実行しています..."
        & npm ci --silent
        Write-Log "npm run build を実行しています..."
        & npm run build
        Write-Log "フロントエンドのビルドが完了しました。"
    } finally {
        Pop-Location
    }
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# データベースマイグレーション
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function Invoke-DatabaseMigration {
    Write-Log "データベースマイグレーションを実行しています..."

    $pythonExe = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
    $alembicExe = Join-Path $ProjectRoot '.venv\Scripts\alembic.exe'

    if (-not (Test-Path $alembicExe)) {
        Write-Log "alembic が見つかりません。スキップします。" -EntryType Warning
        return
    }

    Push-Location $ProjectRoot
    try {
        & $alembicExe upgrade head
        Write-Log "alembic upgrade head 完了。"
    } catch {
        Write-Log "マイグレーション失敗: $_" -EntryType Warning
    } finally {
        Pop-Location
    }
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# .env ファイル生成
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function New-EnvFile {
    Write-Log ".env ファイルを生成しています..."

    $envPath = Join-Path $ProjectRoot '.env'
    if (Test-Path $envPath) {
        Write-Log ".env ファイルが既に存在します。上書きをスキップします。"
        return
    }

    $envContent = @"
# ServiceMatrix 環境設定 (自動生成)
# 生成日時: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

# バックエンド設定
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# フロントエンド設定
FRONTEND_HOST=0.0.0.0
FRONTEND_PORT=3000

# データベース設定
DATABASE_URL=postgresql+asyncpg://servicematrix:password@localhost:5432/servicematrix

# Redis設定
REDIS_URL=redis://localhost:6379/0

# セキュリティ設定
SECRET_KEY=changeme-replace-with-secure-random-string
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 環境
ENVIRONMENT=production
DEBUG=false
"@

    [System.IO.File]::WriteAllText($envPath, $envContent, [System.Text.Encoding]::UTF8)
    Write-Log ".env ファイルを生成しました: $envPath"
    Write-Log "注意: .env の SECRET_KEY および DATABASE_URL を適切な値に変更してください。" -EntryType Warning
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Task Scheduler タスク登録
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function Register-StartupTask {
    Write-Log "Task Scheduler にタスクを登録しています..."

    $startScript = Join-Path $ScriptDir 'Start-ServiceMatrix.ps1'
    if (-not (Test-Path $startScript)) {
        throw "起動スクリプトが見つかりません: $startScript"
    }

    # 既存タスクを削除
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Log "既存タスク '$TaskName' を削除しました。"
    }

    # タスク定義
    $action = New-ScheduledTaskAction `
        -Execute 'powershell.exe' `
        -Argument "-NonInteractive -NoProfile -ExecutionPolicy Bypass -File `"$startScript`"" `
        -WorkingDirectory $ProjectRoot

    $trigger = New-ScheduledTaskTrigger -AtStartup

    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit (New-TimeSpan -Hours 0)  # 無制限

    $principal = New-ScheduledTaskPrincipal `
        -UserId 'SYSTEM' `
        -LogonType ServiceAccount `
        -RunLevel Highest

    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description 'ServiceMatrix バックエンド/フロントエンド 自動起動' `
        -Force | Out-Null

    Write-Log "タスク '$TaskName' を登録しました (SYSTEM権限, AtStartup)。"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Windows Firewall ルール追加
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function Add-FirewallRules {
    Write-Log "Windows Firewall ルールを設定しています..."

    $rules = @(
        @{ Name = 'ServiceMatrix-Backend';  Port = 8000; Description = 'ServiceMatrix バックエンド (FastAPI)' },
        @{ Name = 'ServiceMatrix-Frontend'; Port = 3000; Description = 'ServiceMatrix フロントエンド (Next.js)' }
    )

    foreach ($rule in $rules) {
        $existing = Get-NetFirewallRule -DisplayName $rule.Name -ErrorAction SilentlyContinue
        if ($existing) {
            Write-Log "Firewall ルール '$($rule.Name)' は既に存在します。スキップします。"
            continue
        }

        New-NetFirewallRule `
            -DisplayName $rule.Name `
            -Direction Inbound `
            -Protocol TCP `
            -LocalPort $rule.Port `
            -Action Allow `
            -Description $rule.Description | Out-Null

        Write-Log "Firewall ルール追加: $($rule.Name) (TCP $($rule.Port) Inbound)"
    }
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# データディレクトリ初期化
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function Initialize-DataDirectory {
    if (-not (Test-Path $DataDir)) {
        New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
        Write-Log "データディレクトリを作成しました: $DataDir"
    }
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# メイン処理
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function Main {
    Write-Host '============================================'
    Write-Host '  ServiceMatrix インストーラー'
    Write-Host "  プロジェクトルート: $ProjectRoot"
    Write-Host '============================================'

    Initialize-EventLog
    Write-Log "ServiceMatrix インストールを開始します。"

    Initialize-DataDirectory
    Test-Prerequisites
    Initialize-PythonVenv
    Initialize-Frontend
    Invoke-DatabaseMigration
    New-EnvFile
    Register-StartupTask
    Add-FirewallRules

    Write-Log "ServiceMatrix のインストールが完了しました。"
    Write-Host ''
    Write-Host '============================================'
    Write-Host '  インストール完了'
    Write-Host "  タスク名: $TaskName"
    Write-Host "  データDir: $DataDir"
    Write-Host ''
    Write-Host '  次のステップ:'
    Write-Host "  1. $ProjectRoot\.env を編集し DATABASE_URL / SECRET_KEY を設定"
    Write-Host '  2. PC を再起動するか、タスクスケジューラーからタスクを手動実行'
    Write-Host '============================================'
}

Main
