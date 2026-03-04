<#
.SYNOPSIS
    ServiceMatrix 停止スクリプト
.DESCRIPTION
    pids.json に記録されたプロセスを停止します。
.NOTES
    PowerShell 5.1 対応
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'SilentlyContinue'

$DataDir  = Join-Path $env:ProgramData 'ServiceMatrix'
$PidsFile = Join-Path $DataDir 'pids.json'
$LogFile  = Join-Path $DataDir 'startup.log'
$LogSource = 'ServiceMatrix'

function Write-Log {
    param(
        [string]$Message,
        [ValidateSet('Information','Warning','Error')]
        [string]$EntryType = 'Information'
    )
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "$timestamp [$EntryType] $Message"
    Add-Content -Path $LogFile -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
    Write-Host $line
    try {
        if ([System.Diagnostics.EventLog]::SourceExists($LogSource)) {
            Write-EventLog -LogName Application -Source $LogSource `
                -EventId 3000 -EntryType $EntryType -Message $Message
        }
    } catch { }
}

function Stop-ServiceByPid {
    param([int]$Pid, [string]$Name)

    if ($Pid -le 0) {
        Write-Log "$Name の PID が無効です。スキップします。" -EntryType Warning
        return
    }

    $proc = Get-Process -Id $Pid -ErrorAction SilentlyContinue
    if ($proc) {
        try {
            Stop-Process -Id $Pid -Force -ErrorAction Stop
            Write-Log "$Name (PID=$Pid) を停止しました。"
        } catch {
            Write-Log "$Name (PID=$Pid) の停止に失敗しました: $_" -EntryType Error
        }
    } else {
        Write-Log "$Name (PID=$Pid) は既に停止しています。"
    }
}

function Main {
    Write-Log "ServiceMatrix 停止処理を開始します。" 

    if (-not (Test-Path $PidsFile)) {
        Write-Log "PIDファイルが見つかりません: $PidsFile" -EntryType Warning
        Write-Host "ServiceMatrix は起動していないか、PIDファイルが存在しません。"
        return
    }

    # PID ファイル読み込み
    $pidsData = Get-Content $PidsFile -Raw -Encoding UTF8 | ConvertFrom-Json

    Stop-ServiceByPid -Pid ([int]$pidsData.BackendPid)  -Name 'バックエンド (uvicorn)'
    Stop-ServiceByPid -Pid ([int]$pidsData.FrontendPid) -Name 'フロントエンド (Next.js)'

    # PID ファイルクリア
    Remove-Item $PidsFile -Force -ErrorAction SilentlyContinue
    Write-Log "PIDファイルを削除しました。"

    Write-Log "ServiceMatrix の停止が完了しました。" 
    Write-Host "ServiceMatrix を停止しました。"
}

Main
