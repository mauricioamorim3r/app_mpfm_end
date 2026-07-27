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

$pythonCmd = Get-PythonCommand
$pythonExe = $pythonCmd[0]
$pythonArgs = @()
if ($pythonCmd.Length -gt 1) {
    $pythonArgs = $pythonCmd[1..($pythonCmd.Length - 1)]
}

Write-Host "Instalando dependências com $pythonExe $($pythonArgs -join ' ')" -ForegroundColor Cyan
& $pythonExe @pythonArgs -m pip install --user -r (Join-Path $PSScriptRoot 'backend\\requirements.txt')
