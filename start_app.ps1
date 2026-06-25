$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$LogsDir = Join-Path $ProjectRoot "logs"
$BackendUrl = "http://localhost:8000"
$FrontendUrl = "http://localhost:5173"
$OllamaUrl = "http://localhost:11434"
$OllamaModel = "qwen3:4b"

function Write-Section {
    param([string]$Message)
    Write-Host ""
    Write-Host "== $Message ==" -ForegroundColor Cyan
}

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-HttpReady {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 2
    )
    try {
        Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSeconds | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Wait-ForUrl {
    param(
        [string]$Url,
        [string]$Name,
        [int]$TimeoutSeconds = 90
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-HttpReady -Url $Url -TimeoutSeconds 3) {
            Write-Host "$Name is ready at $Url" -ForegroundColor Green
            return $true
        }
        Start-Sleep -Seconds 2
    }

    Write-Host "$Name did not respond at $Url within $TimeoutSeconds seconds. Check the log window." -ForegroundColor Yellow
    return $false
}

function Start-VisibleProcess {
    param(
        [string]$Title,
        [string]$WorkingDirectory,
        [string]$Command
    )

    $windowCommand = @"
`$Host.UI.RawUI.WindowTitle = '$Title'
Set-Location -LiteralPath '$WorkingDirectory'
$Command
"@

    Start-Process powershell.exe -ArgumentList @(
        "-NoExit",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command", $windowCommand
    ) | Out-Null
}

Write-Host "Sinhala + English Local RAG Document QA System" -ForegroundColor Green
Write-Host "Project root: $ProjectRoot"

New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null

Write-Section "Checking required tools"
if (-not (Test-Command "ollama")) {
    Write-Host "Ollama was not found on PATH. Install Ollama or restart this terminal after installation." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
if (-not (Test-Command "python")) {
    Write-Host "Python was not found on PATH. Install Python 3.10+ and try again." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
if (-not (Test-Command "npm")) {
    Write-Host "npm was not found on PATH. Install Node.js 18+ and try again." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Ollama, Python, and npm are available." -ForegroundColor Green

Write-Section "Checking Ollama"
if (-not (Test-HttpReady -Url $OllamaUrl -TimeoutSeconds 2)) {
    Write-Host "Starting Ollama server in a separate log window..."
    Start-VisibleProcess `
        -Title "Sinhala RAG - Ollama" `
        -WorkingDirectory $ProjectRoot `
        -Command "ollama serve 2>&1 | Tee-Object -FilePath '$LogsDir\ollama.log' -Append"

    if (-not (Wait-ForUrl -Url $OllamaUrl -Name "Ollama" -TimeoutSeconds 45)) {
        Read-Host "Press Enter to exit"
        exit 1
    }
}
else {
    Write-Host "Ollama is already running." -ForegroundColor Green
}

Write-Host "Checking model: $OllamaModel"
$modelList = ollama list 2>$null
if (($modelList -join "`n") -notmatch [regex]::Escape($OllamaModel)) {
    Write-Host "Model $OllamaModel is missing. Pulling it now. This can take several minutes..."
    ollama pull $OllamaModel
}
else {
    Write-Host "Model $OllamaModel is available." -ForegroundColor Green
}

Write-Section "Preparing backend"
$BackendEnv = Join-Path $BackendDir ".env"
$BackendEnvExample = Join-Path $BackendDir ".env.example"
if (-not (Test-Path -LiteralPath $BackendEnv) -and (Test-Path -LiteralPath $BackendEnvExample)) {
    Copy-Item -LiteralPath $BackendEnvExample -Destination $BackendEnv
    Write-Host "Created backend\.env from backend\.env.example"
}

$BackendPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $BackendPython)) {
    Write-Host "Backend virtual environment was not found. Creating it now..."
    python -m venv (Join-Path $BackendDir ".venv")
    & $BackendPython -m pip install --upgrade pip
    & $BackendPython -m pip install -r (Join-Path $BackendDir "requirements.txt")
}
else {
    Write-Host "Backend virtual environment found." -ForegroundColor Green
}

Write-Section "Preparing frontend"
if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir "node_modules"))) {
    Write-Host "Frontend dependencies were not found. Running npm install..."
    Push-Location $FrontendDir
    npm install
    Pop-Location
}
else {
    Write-Host "Frontend dependencies found." -ForegroundColor Green
}

Write-Section "Starting services"
Start-VisibleProcess `
    -Title "Sinhala RAG - Backend API" `
    -WorkingDirectory $BackendDir `
    -Command "& '$BackendPython' -m uvicorn app.main:app --reload --port 8000 2>&1 | Tee-Object -FilePath '$LogsDir\backend.log' -Append"

Start-VisibleProcess `
    -Title "Sinhala RAG - Frontend" `
    -WorkingDirectory $FrontendDir `
    -Command "npm run dev 2>&1 | Tee-Object -FilePath '$LogsDir\frontend.log' -Append"

Wait-ForUrl -Url "$BackendUrl/api/health" -Name "Backend API" -TimeoutSeconds 90 | Out-Null
Wait-ForUrl -Url $FrontendUrl -Name "Frontend" -TimeoutSeconds 90 | Out-Null

Write-Section "Opening browser"
Start-Process $FrontendUrl

Write-Host ""
Write-Host "Application started." -ForegroundColor Green
Write-Host "Frontend: $FrontendUrl"
Write-Host "Backend:  $BackendUrl"
Write-Host "Logs:     $LogsDir"
Write-Host ""
Write-Host "Keep the Ollama, Backend, and Frontend windows open while using the app."
Write-Host "Close those windows when you want to stop the system."
Read-Host "Press Enter to close this launcher window"
