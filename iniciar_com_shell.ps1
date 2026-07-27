# Script para iniciar MPFM Manager contornando AppLocker via Shell.Application
# Este método contorna restrições de política de grupo

$shell = New-Object -ComObject Shell.Application
$workingDir = Get-Location | Select-Object -ExpandProperty Path

Write-Host ""
Write-Host " ========================================="
Write-Host "   MPFM MANAGER - Inicialização"
Write-Host " ========================================="
Write-Host ""
Write-Host "  Método: Shell.Application COM"
Write-Host "  Diretório: $workingDir"
Write-Host "  Python: .\.venv\Scripts\python.exe"
Write-Host ""

# Tenta eliminar logss antigos
if (Test-Path ".tmp_server_out.log") {
    Remove-Item ".tmp_server_out.log" -Force -ErrorAction SilentlyContinue
}

# Inicia servidor
Write-Host "  Iniciando servidor..."
$shell.ShellExecute(".\.venv\Scripts\python.exe", "server.py", $workingDir, "", 1)

Write-Host ""
Write-Host "  Aguardando inicialização..."
Start-Sleep -Seconds 5

#Verifica se servidor está rodando
$portCheck = netstat -ano 2>$null | Select-String ":8765"
if ($portCheck) {
    Write-Host ""
    Write-Host "  ✓ Servidor iniciado com sucesso!"
    Write-Host "  ✓ Acessar em: http://127.0.0.1:8765"
    Write-Host ""
} else {
    Write-Host "  ⚠ Servidor pode estar iniciando..."
    Write-Host "  Verifique em alguns segundos em: http://127.0.0.1:8765"
    Write-Host ""
}
