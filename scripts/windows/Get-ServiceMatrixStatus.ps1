<#
.SYNOPSIS
    ServiceMatrix ステータス確認スクリプト
.DESCRIPTION
    プロセスの生存確認・ポートListen確認・ヘルスチェックを行います。
.NOTES
    PowerShell 5.1 対応
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'SilentlyContinue'

$DataDir  = Join-Path $env:ProgramData 'ServiceMatrix'
$PidsFile = Join-Path $DataDir 'pids.json'

function Write-StatusLine {
    param([string]$Label, [string]$Value, [string]$Status)
    $color = switch ($Status) {
        'OK'      { 'Green'  }
        'WARN'    { 'Yellow' }
        'ERROR'   { 'Red'    }
        default   { 'White'  }
    }
    $padLabel = $Label.PadRight(28)
    Write-Host "  $padLabel : " -NoNewline
    Write-Host $Value -ForegroundColor $color
}

function Test-PortListening {
    param([int]$Port)
    return (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) -ne $null
}

function Test-HealthEndpoint {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Get-ProcessStatus {
    param([int]$Pid)
    if ($Pid -le 0) { return $null }
    return Get-Process -Id $Pid -ErrorAction SilentlyContinue
}

function Main {
    Write-Host ''
    Write-Host '══════════════════════════════════════════════' -ForegroundColor Cyan
    Write-Host '  ServiceMatrix ステータス'                     -ForegroundColor Cyan
    Write-Host "  確認日時: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
    Write-Host '══════════════════════════════════════════════' -ForegroundColor Cyan
    Write-Host ''

    if (-not (Test-Path $PidsFile)) {
        Write-Host '  [情報] PIDファイルが存在しません。ServiceMatrix は停止中です。' -ForegroundColor Yellow
        Write-Host ''
        return
    }

    $pidsData = Get-Content $PidsFile -Raw -Encoding UTF8 | ConvertFrom-Json

    $backendPid   = [int]$pidsData.BackendPid
    $frontendPid  = [int]$pidsData.FrontendPid
    $localIP      = $pidsData.LocalIP
    $backendPort  = [int]$pidsData.BackendPort
    $frontendPort = [int]$pidsData.FrontendPort
    $startedAt    = $pidsData.StartedAt

    Write-Host '  【起動情報】' -ForegroundColor White
    Write-StatusLine '起動日時'    $startedAt   'OK'
    Write-StatusLine 'ローカル IP' $localIP     'OK'
    Write-Host ''

    # ── バックエンド ──
    Write-Host '  【バックエンド (FastAPI/uvicorn)】' -ForegroundColor White
    $backendProc = Get-ProcessStatus -Pid $backendPid
    if ($backendProc) {
        Write-StatusLine 'プロセス'    "PID=$backendPid (稼働中)"  'OK'
        Write-StatusLine 'メモリ使用量' "$([math]::Round($backendProc.WorkingSet64/1MB,1)) MB" 'OK'
    } else {
        Write-StatusLine 'プロセス'    "PID=$backendPid (停止中)" 'ERROR'
    }

    $portOk = Test-PortListening -Port $backendPort
    Write-StatusLine "ポート $backendPort (Listen)" $(if ($portOk) { 'Listen中' } else { '停止' }) $(if ($portOk) { 'OK' } else { 'ERROR' })

    $healthUrl = "http://localhost:${backendPort}/health"
    $healthOk = Test-HealthEndpoint -Url $healthUrl
    Write-StatusLine 'ヘルスチェック (/health)' $(if ($healthOk) { "OK ($healthUrl)" } else { "NG ($healthUrl)" }) $(if ($healthOk) { 'OK' } else { 'ERROR' })

    Write-Host ''

    # ── フロントエンド ──
    Write-Host '  【フロントエンド (Next.js)】' -ForegroundColor White
    $frontendProc = Get-ProcessStatus -Pid $frontendPid
    if ($frontendProc) {
        Write-StatusLine 'プロセス'    "PID=$frontendPid (稼働中)"  'OK'
        Write-StatusLine 'メモリ使用量' "$([math]::Round($frontendProc.WorkingSet64/1MB,1)) MB" 'OK'
    } else {
        Write-StatusLine 'プロセス'    "PID=$frontendPid (停止中)" 'ERROR'
    }

    $fportOk = Test-PortListening -Port $frontendPort
    Write-StatusLine "ポート $frontendPort (Listen)" $(if ($fportOk) { 'Listen中' } else { '停止' }) $(if ($fportOk) { 'OK' } else { 'ERROR' })

    $frontendUrl = "http://localhost:${frontendPort}"
    $frontendOk = Test-HealthEndpoint -Url $frontendUrl
    Write-StatusLine 'フロントエンド疎通' $(if ($frontendOk) { "OK ($frontendUrl)" } else { "NG ($frontendUrl)" }) $(if ($frontendOk) { 'OK' } else { 'ERROR' })

    Write-Host ''
    Write-Host '  【アクセス URL】' -ForegroundColor White
    Write-StatusLine 'バックエンド API'  "http://${localIP}:${backendPort}"  'OK'
    Write-StatusLine 'API ドキュメント'  "http://${localIP}:${backendPort}/docs" 'OK'
    Write-StatusLine 'フロントエンド'    "http://${localIP}:${frontendPort}" 'OK'
    Write-Host ''
    Write-Host '══════════════════════════════════════════════' -ForegroundColor Cyan
    Write-Host ''
}

Main
