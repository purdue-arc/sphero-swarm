<#
Installs the coordinator on the Windows mini-PC as a background task that starts at
boot (no login needed), and turns on Windows' SSH server so a Mac can open the
dashboard through an SSH tunnel (scripts/open_dashboard.sh).

Run once, from the repo root, in an *Administrator* PowerShell:
    powershell -ExecutionPolicy Bypass -File scripts\install_coordinator_windows.ps1 -Token <pi-token>

Re-running is safe: it replaces the task and restarts the coordinator with the current code.
#>
param([Parameter(Mandatory = $true)][string]$Token)
$ErrorActionPreference = "Stop"

$identity = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $identity.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this from an Administrator PowerShell (right-click PowerShell > Run as administrator)."
}
if ($Token -notmatch '^[A-Za-z0-9_-]+$') { throw "Token may only contain letters, digits, '-' and '_'." }

$Repo = Split-Path -Parent $PSScriptRoot
$TaskName = "SpheroCoordinator"
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$Log = Join-Path $Repo "coordinator\coordinator.log"
$TokenDir = Join-Path $env:USERPROFILE ".config"
$TokenFile = Join-Path $TokenDir "sphero-coordinator.json"
Write-Host "Repo: $Repo"

# 1. Python environment (the mini-PC runs the full project, so a normal uv sync).
if (-not (Test-Path $Python)) {
    $uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
    if (-not $uv) { $uv = Join-Path $env:USERPROFILE ".local\bin\uv.exe" }
    if (-not (Test-Path $uv)) { throw "uv not found. Install it: powershell -c `"irm https://astral.sh/uv/install.ps1 | iex`"" }
    Push-Location $Repo; & $uv sync; Pop-Location
}
& $Python -c "import flask, requests" 2>$null
if ($LASTEXITCODE -ne 0) { throw "flask/requests don't import from $Python; run 'uv sync' in the repo and re-run." }

# 2. Token file, outside the repo so it never ends up in git.
New-Item -ItemType Directory -Force -Path $TokenDir | Out-Null
@{ token = $Token } | ConvertTo-Json | Set-Content -Encoding ascii $TokenFile
icacls $TokenFile /inheritance:r /grant:r "${env:USERNAME}:F" "SYSTEM:F" "Administrators:F" | Out-Null
Write-Host "Token saved to $TokenFile"

# 3. Background task: starts 30 s after boot as SYSTEM (no login), restarts if it dies.
#    -u = unbuffered output so coordinator.log is written live.
$cmdArgs = "/c `"`"$Python`" -u coordinator\server.py --no-browser --token-file `"$TokenFile`" >> `"$Log`" 2>&1`""
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $cmdArgs -WorkingDirectory $Repo
$trigger = New-ScheduledTaskTrigger -AtStartup
$trigger.Delay = "PT30S"
$settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
}
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
    Where-Object { $_.CommandLine -like "*coordinator\server.py*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Write-Host "Task '$TaskName' registered (starts at every boot)."

# 4. Windows SSH server, so the Mac can tunnel to the dashboard. Skip the install if an
#    sshd service already exists (e.g. installed via winget): Add-WindowsCapability goes
#    through Windows Update and can stall for a very long time on managed machines.
if (-not (Get-Service -Name sshd -ErrorAction SilentlyContinue)) {
    Write-Host "Installing OpenSSH Server via winget..."
    winget install --id Microsoft.OpenSSH.Preview -e --source winget --accept-source-agreements --accept-package-agreements
    if (-not (Get-Service -Name sshd -ErrorAction SilentlyContinue)) {
        throw "OpenSSH Server isn't installed. Install it (winget install --id Microsoft.OpenSSH.Preview -e) and re-run."
    }
}
Set-Service -Name sshd -StartupType Automatic
Start-Service sshd
if (-not (Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -DisplayName "OpenSSH Server (sshd)" -Enabled True `
        -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
}
Write-Host "SSH server is on."

# 5. Check the coordinator answers.
Write-Host "Waiting for the coordinator on http://127.0.0.1:8000 ..."
$ok = $false
# 127.0.0.1, not localhost: Windows tries IPv6 (::1) first, and the server only listens on IPv4.
# 60 s: the first start after a fresh .venv is slow (bytecode compile + antivirus scan).
foreach ($i in 1..60) {
    try { Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8000/favicon.ico" -TimeoutSec 2 | Out-Null; $ok = $true; break }
    catch { Start-Sleep -Seconds 1 }
}
if ($ok) { Write-Host "OK: the coordinator is running and will start on every boot." -ForegroundColor Green }
else { Write-Warning "The coordinator did not answer within 60 s. Last lines of $Log :"; Get-Content $Log -Tail 30 -ErrorAction SilentlyContinue }

$ips = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } |
    Select-Object -ExpandProperty IPAddress
Write-Host ""
Write-Host "From your Mac (on the same Wi-Fi), open the dashboard with:"
foreach ($ip in $ips) { Write-Host "    bash scripts/open_dashboard.sh `"$env:USERNAME@$ip`"" }
Write-Host "It will ask for this Windows account's password."
Write-Host "Tip: keep the mini-PC awake so the dashboard stays reachable:  powercfg /change standby-timeout-ac 0"
