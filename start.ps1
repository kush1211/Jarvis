# Starts llama-server in its own window (unless it's already running),
# waits until the model is loaded, then runs Jarvis in this window.
# Usage: .\start.ps1

$ServerExe  = "C:\llama.cpp\llama-server.exe"
$ServerArgs = "-hf unsloth/gemma-4-E2B-it-GGUF:Q4_K_M -c 4096 -ngl 99 --jinja --port 8080"
$HealthUrl  = "http://127.0.0.1:8080/health"   # returns {"status":"ok"} once the model is loaded

function Test-Server {
    try { (Invoke-RestMethod $HealthUrl -TimeoutSec 2).status -eq "ok" } catch { $false }
}

if (Test-Server) {
    Write-Host "llama-server is already running."
} else {
    Write-Host "Starting llama-server in a new window..."
    $server = Start-Process $ServerExe -ArgumentList $ServerArgs -PassThru
    while (-not (Test-Server)) {
        if ($server.HasExited) { Write-Host "llama-server stopped while loading. Check its window for the error."; exit 1 }
        Start-Sleep -Seconds 1
    }
    Write-Host "llama-server is ready."
}

& "$PSScriptRoot\.venv\Scripts\python.exe" "$PSScriptRoot\jarvis.py"
