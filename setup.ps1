# HealthLens AI - one-time setup (Windows). Easiest: double-click setup.bat
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

function Step($n, $text) { Write-Host "`n[$n/4] $text" -ForegroundColor Cyan }
function Fail($text) {
    Write-Host "`nERROR: $text" -ForegroundColor Red
    Write-Host "See the Troubleshooting section in README.md" -ForegroundColor Yellow
    exit 1
}

Write-Host "=== HealthLens AI setup ===" -ForegroundColor Green

# --- Python check -------------------------------------------------------
$ver = $null
try { $ver = (& python -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null) } catch {}
if (-not $ver) { Fail "Python was not found. Install Python 3.10+ from https://www.python.org/downloads/ and tick 'Add python.exe to PATH'." }
$major, $minor = $ver.Split(".") | ForEach-Object { [int]$_ }
if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) { Fail "Python $ver found, but 3.10 or newer is required." }
Write-Host "Found Python $ver"

Set-Location "$root\backend"

Step 1 "Creating a private Python environment (.venv)"
if (-not (Test-Path .venv)) { python -m venv .venv; if (-not $?) { Fail "Could not create the virtual environment." } }
$py = ".\.venv\Scripts\python.exe"

Step 2 "Installing Python packages (takes 1-3 minutes the first time)"
& $py -m pip install --upgrade pip --quiet --disable-pip-version-check
& $py -m pip install -r requirements.txt --quiet --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { Fail "Package installation failed. Check your internet connection and try again." }

Step 3 "Training the AI models (about 1 minute)"
& $py ml\download_data.py
& $py -m ml.train
if ($LASTEXITCODE -ne 0) { Fail "Model training failed." }
& $py -m ml.samples

Step 4 "Preparing the website"
if (Test-Path "$root\frontend\dist\index.html") {
    Write-Host "Website is already built - nothing to do."
} elseif (Get-Command npm -ErrorAction SilentlyContinue) {
    Set-Location "$root\frontend"; npm install; npm run build
} else {
    Fail "frontend/dist is missing and Node.js is not installed. Install Node.js 20+ from https://nodejs.org and run setup again."
}

Write-Host "`nSetup complete! Now double-click start.bat (or run .\start.ps1)." -ForegroundColor Green
