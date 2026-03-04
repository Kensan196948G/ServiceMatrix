<#
.SYNOPSIS
    ServiceMatrix 起動スクリプト
.DESCRIPTION
    動的IPアドレス対応・ポート競合チェックを行い、
    バックエンド(FastAPI/uvicorn) とフロントエンド(Next.js) を起動します。
.NOTES
    PowerShell 5.1 対応
    Task Scheduler から SYSTEM 権限で実行されます
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 定数定義
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
$ScriptDir   = $PSScriptRoot
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir '..\..')).Path
$DataDir     = Join-Path $env:ProgramData 'ServiceMatrix'
$PidsFile    = Join-Path $DataDir 'pids.json'
$LogFile     = Join-Path $DataDir 'startup.log'
$LogSource   = 'ServiceMatrix'

$DefaultBackendPort  = 8000
$DefaultFrontendPort = 3000
$MaxPortRetry        = 10

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ログ関数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function Write-Log {
    param(
        [string]$Message,
        [ValidateSet('Information','Warning','Error')]
        [string]$EntryType = 'Information',
        [int]$EventId = 2000
    )
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "$timestamp [$EntryType] $Message"

    # ファイルログ
    if (-not (Test-Path $DataDir)) { New-Item -ItemType Directory -Path $DataDir -Force | Out-Null }
    Add-Content -Path $LogFile -Value $line -Encoding UTF8

    # イベントログ（ソース登録済みの場合のみ）
    try {
        if ([System.Diagnostics.EventLog]::SourceExists($LogSource)) {
            Write-EventLog -LogName Application -Source $LogSource `
                -EventId $EventId -EntryType $EntryType -Message $Message
        }
    } catch { }
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 動的 IP アドレス取得
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function Get-LocalIPAddress {
    # DHCP割り当てIPv4を優先取得
    $ip = (Get-NetIPAddress -AddressFamily IPv4 |
           Where-Object { $_.IPAddress -ne '127.0.0.1' -and $_.PrefixOrigin -eq 'Dhcp' } |
           Select-Object -First 1).IPAddress

    # DHCPがない場合はManual（固定IP）を試みる
    if (-not $ip) {
        $ip = (Get-NetIPAddress -AddressFamily IPv4 |
               Where-Object { $_.IPAddress -ne '127.0.0.1' -and $_.PrefixOrigin -eq 'Manual' } |
               Select-Object -First 1).IPAddress
    }

    # それでもなければ localhost
    if (-not $ip) {
        $ip = '127.0.0.1'
        Write-Log "DHCPアドレスが見つかりません。127.0.0.1 を使用します。" -EntryType Warning
    }

    return $ip
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ポート競合チェックと代替ポート選択
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function Get-AvailablePort {
    param([int]$StartPort)

    for ($port = $StartPort; $port -lt ($StartPort + $MaxPortRetry); $port++) {
        $inUse = (Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue) -ne $null
        if (-not $inUse) {
            return $port
        }
        Write-Log "ポート $port は使用中です。次のポートを試します..." -EntryType Warning
    }

    throw "ポート $StartPort ～ $($StartPort + $MaxPortRetry - 1) がすべて使用中です。"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# .env ファイル更新
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function Update-EnvFile {
    param(
        [string]$BackendHost,
        [int]$BackendPort,
        [string]$FrontendHost,
        [int]$FrontendPort
    )

    $envPath = Join-Path $ProjectRoot '.env'
    if (-not (Test-Path $envPath)) {
        Write-Log ".env ファイルが見つかりません: $envPath" -EntryType Warning
        return
    }

    $content = Get-Content $envPath -Encoding UTF8

    # 既存の BACKEND_HOST/PORT, FRONTEND_HOST/PORT を置換
    $content = $content -replace '^BACKEND_HOST=.*',  "BACKEND_HOST=$BackendHost"
    $content = $content -replace '^BACKEND_PORT=.*',  "BACKEND_PORT=$BackendPort"
    $content = $content -replace '^FRONTEND_HOST=.*', "FRONTEND_HOST=$FrontendHost"
    $content = $content -replace '^FRONTEND_PORT=.*', "FRONTEND_PORT=$FrontendPort"

    [System.IO.File]::WriteAllLines($envPath, $content, [System.Text.Encoding]::UTF8)
    Write-Log ".env を更新しました (Backend: ${BackendHost}:${BackendPort}, Frontend: ${FrontendHost}:${FrontendPort})"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# バックエンド起動 (FastAPI/uvicorn)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function Start-Backend {
    param([string]$Host, [int]$Port)

    $uvicornExe = Join-Path $ProjectRoot '.venv\Scripts\uvicorn.exe'
    if (-not (Test-Path $uvicornExe)) {
        throw "uvicorn が見つかりません: $uvicornExe"
    }

    $logPath = Join-Path $DataDir 'backend.log'
    $args = "src.main:app --host $Host --port $Port --workers 1"

    Write-Log "バックエンドを起動します: uvicorn $args"

    $proc = Start-Process `
        -FilePath $uvicornExe `
        -ArgumentList $args `
        -WorkingDirectory $ProjectRoot `
        -RedirectStandardOutput $logPath `
        -RedirectStandardError "$logPath.err" `
        -NoNewWindow `
        -PassThru

    Write-Log "バックエンド起動完了 PID=$($proc.Id) ポート=$Port"
    return $proc.Id
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# フロントエンド起動 (Next.js)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function Start-Frontend {
    param([string]$Host, [int]$Port)

    $frontendDir = Join-Path $ProjectRoot 'frontend'
    $npmExe = (Get-Command 'npm' -ErrorAction SilentlyContinue).Source
    if (-not $npmExe) {
        throw "npm が見つかりません。Node.js をインストールしてください。"
    }

    $logPath = Join-Path $DataDir 'frontend.log'
    # Next.js は PORT 環境変数でポートを制御
    $env:PORT = $Port
    $env:HOSTNAME = $Host

    Write-Log "フロントエンドを起動します: npm run start (port=$Port)"

    $proc = Start-Process `
        -FilePath $npmExe `
        -ArgumentList 'run', 'start' `
        -WorkingDirectory $frontendDir `
        -RedirectStandardOutput $logPath `
        -RedirectStandardError "$logPath.err" `
        -NoNewWindow `
        -PassThru

    Write-Log "フロントエンド起動完了 PID=$($proc.Id) ポート=$Port"
    return $proc.Id
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PID ファイル保存
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function Save-Pids {
    param(
        [int]$BackendPid,
        [int]$FrontendPid,
        [string]$LocalIP,
        [int]$BackendPort,
        [int]$FrontendPort
    )

    if (-not (Test-Path $DataDir)) {
        New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
    }

    $data = @{
        BackendPid   = $BackendPid
        FrontendPid  = $FrontendPid
        LocalIP      = $LocalIP
        BackendPort  = $BackendPort
        FrontendPort = $FrontendPort
        StartedAt    = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
    }

    $json = $data | ConvertTo-Json -Depth 3
    [System.IO.File]::WriteAllText($PidsFile, $json, [System.Text.Encoding]::UTF8)
    Write-Log "PIDファイルを保存しました: $PidsFile"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# メイン処理
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function Main {
    Write-Log "ServiceMatrix 起動処理を開始します。" -EventId 2001

    # ログローテーション（5MB超えたらリネーム）
    if ((Test-Path $LogFile) -and (Get-Item $LogFile).Length -gt 5MB) {
        Rename-Item $LogFile "$LogFile.old" -Force -ErrorAction SilentlyContinue
    }

    # 1. 動的 IP 取得
    $localIP = Get-LocalIPAddress
    Write-Log "ローカル IP アドレス: $localIP"

    # 2. ポート競合チェック
    $backendPort  = Get-AvailablePort -StartPort $DefaultBackendPort
    $frontendPort = Get-AvailablePort -StartPort $DefaultFrontendPort
    Write-Log "使用ポート: バックエンド=$backendPort, フロントエンド=$frontendPort"

    # 3. .env 更新
    Update-EnvFile -BackendHost '0.0.0.0' -BackendPort $backendPort `
                   -FrontendHost '0.0.0.0' -FrontendPort $frontendPort

    # 4. バックエンド起動
    $backendPid = Start-Backend -Host '0.0.0.0' -Port $backendPort

    # 5. フロントエンド起動
    $frontendPid = Start-Frontend -Host '0.0.0.0' -Port $frontendPort

    # 6. PID 保存
    Save-Pids -BackendPid $backendPid -FrontendPid $frontendPid `
              -LocalIP $localIP -BackendPort $backendPort -FrontendPort $frontendPort

    $msg = "ServiceMatrix 起動完了: Backend=http://${localIP}:${backendPort} Frontend=http://${localIP}:${frontendPort}"
    Write-Log $msg -EventId 2002
    Write-Host $msg
}

Main
