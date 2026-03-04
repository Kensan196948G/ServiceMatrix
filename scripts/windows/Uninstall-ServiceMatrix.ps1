#Requires -RunAsAdministrator
<#
.SYNOPSIS
    ServiceMatrix アンインストールスクリプト
.DESCRIPTION
    Task Scheduler のタスクと Windows Firewall ルールを削除します。
.NOTES
    PowerShell 5.1 対応
    管理者権限で実行してください
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'SilentlyContinue'

$TaskName  = 'ServiceMatrix-Startup'
$DataDir   = Join-Path $env:ProgramData 'ServiceMatrix'
$LogSource = 'ServiceMatrix'

function Write-Log {
    param(
        [string]$Message,
        [ValidateSet('Information','Warning','Error')]
        [string]$EntryType = 'Information'
    )
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Write-Host "$timestamp [$EntryType] $Message"
    try {
        if ([System.Diagnostics.EventLog]::SourceExists($LogSource)) {
            Write-EventLog -LogName Application -Source $LogSource `
                -EventId 4000 -EntryType $EntryType -Message $Message
        }
    } catch { }
}

function Remove-ScheduledTask-Safe {
    Write-Log "Task Scheduler からタスクを削除しています..."

    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) {
        # 実行中ならまず停止
        if ($task.State -eq 'Running') {
            Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
            Write-Log "実行中のタスクを停止しました。"
        }
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
        Write-Log "タスク '$TaskName' を削除しました。"
    } else {
        Write-Log "タスク '$TaskName' は存在しません。スキップします。"
    }
}

function Remove-FirewallRules-Safe {
    Write-Log "Windows Firewall ルールを削除しています..."

    $ruleNames = @('ServiceMatrix-Backend', 'ServiceMatrix-Frontend')
    foreach ($name in $ruleNames) {
        $rule = Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue
        if ($rule) {
            Remove-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue
            Write-Log "Firewall ルール '$name' を削除しました。"
        } else {
            Write-Log "Firewall ルール '$name' は存在しません。スキップします。"
        }
    }
}

function Main {
    Write-Host '============================================'
    Write-Host '  ServiceMatrix アンインストーラー'
    Write-Host '============================================'

    $confirm = Read-Host "ServiceMatrix のタスクとFirewallルールを削除しますか? [y/N]"
    if ($confirm -ne 'y' -and $confirm -ne 'Y') {
        Write-Host "アンインストールをキャンセルしました。"
        return
    }

    Remove-ScheduledTask-Safe
    Remove-FirewallRules-Safe

    Write-Host ''
    Write-Host '============================================'
    Write-Host '  アンインストール完了'
    Write-Host ''
    Write-Host '  以下は手動で削除が必要な場合があります:'
    Write-Host "  - プロジェクトファイル: (インストール先)"
    Write-Host "  - データディレクトリ: $DataDir"
    Write-Host "  - 仮想環境: (プロジェクトルート)\.venv"
    Write-Host '============================================'
}

Main
