# HealthLens AI - start the app (Windows). Easiest: double-click start.bat
$root = $PSScriptRoot
Set-Location "$root\backend"
if (-not (Test-Path .\.venv\Scripts\python.exe) -or -not (Test-Path .\models\heart.joblib)) {
    Write-Host "The app is not set up yet. Run setup.bat (or .\setup.ps1) first." -ForegroundColor Red
    exit 1
}
Write-Host "Starting HealthLens AI at http://localhost:8501  (press Ctrl+C or close this window to stop)" -ForegroundColor Green
# open the browser a few seconds after the server starts
Start-Process cmd -ArgumentList "/c timeout /t 4 >nul & start http://localhost:8501" -WindowStyle Hidden
.\.venv\Scripts\python.exe -m streamlit run healthlens.py --server.address 127.0.0.1 --server.port 8501
