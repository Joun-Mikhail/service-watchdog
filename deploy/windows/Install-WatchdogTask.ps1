<#
.SYNOPSIS
    Registers service-watchdog as Windows scheduled tasks.

.DESCRIPTION
    Creates two scheduled tasks for the current user:
      service-watchdog          starts at boot, restarts automatically on failure
      service-watchdog-report   writes reports\uptime-latest.html every day

    The tasks run whether or not the user is logged on (S4U logon), without
    storing a password. Must be run from an elevated PowerShell session.

.PARAMETER Uninstall
    Stop and remove both tasks.

.PARAMETER Python
    Path to python.exe. Defaults to the first python on PATH.

.PARAMETER ReportTime
    Time of day for the daily report (24h, e.g. 07:00).

.EXAMPLE
    .\deploy\windows\Install-WatchdogTask.ps1

.EXAMPLE
    .\deploy\windows\Install-WatchdogTask.ps1 -Uninstall
#>
[CmdletBinding()]
param(
    [switch]$Uninstall,
    [string]$Python,
    [string]$ReportTime = '07:00'
)

$ErrorActionPreference = 'Stop'
$TaskNames = @{ Monitor = 'service-watchdog'; Report = 'service-watchdog-report' }
$AppDir = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

$identity = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $identity.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this script from an elevated PowerShell session (Run as Administrator).'
}

if ($Uninstall) {
    foreach ($name in $TaskNames.Values) {
        if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) {
            Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
            Unregister-ScheduledTask -TaskName $name -Confirm:$false
            Write-Output "Removed scheduled task '$name'"
        }
    }
    return
}

if (-not $Python) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $cmd -or $cmd.Source -like '*\WindowsApps\*') {
        throw 'Python was not found on PATH (the Microsoft Store alias does not count). Install Python 3.10+ from python.org or pass -Python <path>.'
    }
    $Python = $cmd.Source
}

Write-Output "Application directory: $AppDir"
Write-Output "Python: $Python"

if (-not (Test-Path (Join-Path $AppDir '.env'))) {
    Write-Warning ".env not found - alerts will only be logged. Copy .env.example to .env and add SMTP credentials."
}

Push-Location $AppDir
try {
    Write-Output 'Installing Python dependencies...'
    & $Python -m pip install --quiet --disable-pip-version-check -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'pip install failed' }

    Write-Output 'Validating config.yaml...'
    & $Python -c "import config; config.load_config('config.yaml')"
    if ($LASTEXITCODE -ne 0) { throw 'config.yaml is invalid - fix it and run this script again.' }
}
finally {
    Pop-Location
}

$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew

$monitorTask = @{
    TaskName    = $TaskNames.Monitor
    Description = 'service-watchdog uptime monitor'
    Action      = New-ScheduledTaskAction -Execute $Python -Argument 'watchdog.py --config config.yaml' -WorkingDirectory $AppDir
    Trigger     = New-ScheduledTaskTrigger -AtStartup
    Principal   = $principal
    Settings    = $settings
    Force       = $true
}
Register-ScheduledTask @monitorTask | Out-Null

$reportTask = @{
    TaskName    = $TaskNames.Report
    Description = 'service-watchdog daily uptime report'
    Action      = New-ScheduledTaskAction -Execute $Python -Argument 'report.py --hours 24 --html reports\uptime-latest.html' -WorkingDirectory $AppDir
    Trigger     = New-ScheduledTaskTrigger -Daily -At $ReportTime
    Principal   = $principal
    Settings    = $settings
    Force       = $true
}
Register-ScheduledTask @reportTask | Out-Null

Start-ScheduledTask -TaskName $TaskNames.Monitor

Get-ScheduledTask -TaskName @($TaskNames.Values) | Format-Table TaskName, State -AutoSize
Write-Output "Logs:    $AppDir\logs\watchdog.log"
Write-Output "Report:  $AppDir\reports\uptime-latest.html (daily at $ReportTime)"
Write-Output "Remove:  .\deploy\windows\Install-WatchdogTask.ps1 -Uninstall"
