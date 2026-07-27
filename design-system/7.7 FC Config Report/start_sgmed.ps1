param(
    [int]$PreferredPort = 8010,
    [int]$MaxPort = 8099
)

Set-Location -Path $PSScriptRoot

function Get-PythonCommand {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($version in @('-3.14', '-3.13', '-3.12', '-3.11')) {
            & py $version -c "import sys" 2>$null
            if ($LASTEXITCODE -eq 0) {
                return @('py', $version)
            }
        }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $version = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($LASTEXITCODE -eq 0 -and $version -in @('3.14', '3.13', '3.12', '3.11')) {
            return @('python')
        }
        if ($LASTEXITCODE -eq 0) {
            throw "Python $version encontrado no PATH, mas este pacote foi validado apenas para Python 3.14/3.13/3.12/3.11."
        }
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        Write-Host 'Python 3.14/3.13/3.12/3.11 não encontrado via py launcher.' -ForegroundColor Yellow
        Write-Host 'Instale preferencialmente Python 3.14 para este pacote.' -ForegroundColor Yellow
    }
    throw 'Python não encontrado no PATH. Instale preferencialmente Python 3.14 e tente novamente.'
}

function Test-PortAvailable {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    $listener = $null
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        return $true
    } catch {
        return $false
    } finally {
        if ($listener -ne $null) {
            $listener.Stop()
        }
    }
}

function Get-FreePort {
    param(
        [int]$StartPort,
        [int]$EndPort
    )

    for ($port = $StartPort; $port -le $EndPort; $port++) {
        if (Test-PortAvailable -Port $port) {
            return $port
        }
    }

    throw "Nenhuma porta livre encontrada entre $StartPort e $EndPort."
}

$pythonCmd = Get-PythonCommand
$pythonExe = $pythonCmd[0]
$pythonArgs = @()
if ($pythonCmd.Length -gt 1) {
    $pythonArgs = $pythonCmd[1..($pythonCmd.Length - 1)]
}

try {
    & $pythonExe @pythonArgs -c "import uvicorn" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw 'uvicorn ausente'
    }
} catch {
    Write-Host 'Dependências Python não encontradas para o Flow Computer Configuration Analisys.' -ForegroundColor Yellow
    Write-Host 'Instale com:' -ForegroundColor Yellow
    Write-Host '  python -m pip install --user -r backend\\requirements.txt' -ForegroundColor Yellow
    Write-Host 'ou, se usar o launcher:' -ForegroundColor Yellow
    Write-Host '  py -3.14 -m pip install --user -r backend\\requirements.txt' -ForegroundColor Yellow
    exit 1
}

$selectedPort = Get-FreePort -StartPort $PreferredPort -EndPort $MaxPort
$appUrl = "http://127.0.0.1:$selectedPort"

Write-Host "Iniciando Flow Computer Configuration Analisys com $pythonExe $($pythonArgs -join ' ')" -ForegroundColor Cyan
Write-Host "Porta selecionada: $selectedPort" -ForegroundColor Green
Write-Host "Abra no navegador: $appUrl" -ForegroundColor Green
& $pythonExe @pythonArgs -m uvicorn app.main:app --host 127.0.0.1 --port $selectedPort --app-dir (Join-Path $PSScriptRoot 'backend')
