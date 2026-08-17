$sw = [System.Diagnostics.Stopwatch]::StartNew()
$resp = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/ops/processing-history?limit=3' -TimeoutSec 10
$sw.Stop()
Write-Output ("tempo_ms=" + $sw.ElapsedMilliseconds)
Write-Output ("runs_count=" + $resp.runs.Count)
