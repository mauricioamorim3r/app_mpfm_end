<#
.SYNOPSIS
    Deploy MPFM App para Azure App Service (Python runtime, sem Docker necessário)

.DESCRIPTION
    Requer: módulo Az PowerShell (sem necessidade de Azure CLI separado)
    Instalar: Install-Module -Name Az -Scope CurrentUser -Repository PSGallery -Force
    Uso:      .\deploy_azure.ps1
              .\deploy_azure.ps1 -ResourceGroup "meu-grupo" -AppName "mpfm-app-prod"

.NOTES
    Migrado de az CLI para Az PowerShell module (Az.*).
    Ref: https://learn.microsoft.com/en-us/powershell/azure/migrate-from-azurerm-to-az
#>

param(
    [string]$ResourceGroup = "rg-mpfm-app",
    [string]$AppName       = "mpfm-metering",
    [string]$Location      = "brazilsouth",
    [string]$Sku           = "B2"
)

$ErrorActionPreference = "Stop"

# -------------------------------------------------------
# Pré-requisito: módulo Az instalado
# -------------------------------------------------------
if (-not (Get-Module -Name Az.Accounts -ListAvailable)) {
    Write-Host "Instalando modulo Az PowerShell..." -ForegroundColor Yellow
    Install-Module -Name Az -Scope CurrentUser -Repository PSGallery -Force -AllowClobber
}

Write-Host "=== Deploy MPFM App para Azure App Service ===" -ForegroundColor Cyan

# -------------------------------------------------------
# 1. Login (abre browser se não estiver autenticado)
# -------------------------------------------------------
Write-Host "`n[1/6] Verificando autenticacao Azure..." -ForegroundColor Yellow
$ctx = Get-AzContext
if (-not $ctx) {
    Connect-AzAccount
    $ctx = Get-AzContext
}
Write-Host "    Subscription: $($ctx.Subscription.Name)" -ForegroundColor Green

# -------------------------------------------------------
# 2. Resource Group
# -------------------------------------------------------
Write-Host "`n[2/6] Criando resource group '$ResourceGroup' em '$Location'..." -ForegroundColor Yellow
New-AzResourceGroup -Name $ResourceGroup -Location $Location -Force | Out-Null
Write-Host "    OK" -ForegroundColor Green

# -------------------------------------------------------
# 3. Storage para persistência do SQLite (Azure Files)
# -------------------------------------------------------
Write-Host "`n[3/6] Criando storage account para dados persistentes..." -ForegroundColor Yellow
$rawName   = "mpfmdata" + ($AppName -replace "[^a-z0-9]", "")
$StorageName = $rawName.ToLower().Substring(0, [Math]::Min(24, $rawName.Length))

$storageAccount = New-AzStorageAccount `
    -ResourceGroupName $ResourceGroup `
    -Name $StorageName `
    -Location $Location `
    -SkuName Standard_LRS `
    -Kind StorageV2

$storageKey = (Get-AzStorageAccountKey `
    -ResourceGroupName $ResourceGroup `
    -Name $StorageName)[0].Value

$storageCtx = New-AzStorageContext -StorageAccountName $StorageName -StorageAccountKey $storageKey
New-AzStorageShare -Name "mpfm-data" -Context $storageCtx | Out-Null
Write-Host "    Storage: $StorageName / share: mpfm-data" -ForegroundColor Green

# -------------------------------------------------------
# 4. App Service Plan + Web App (Python 3.12 Linux)
# -------------------------------------------------------
Write-Host "`n[4/6] Criando App Service Plan e Web App..." -ForegroundColor Yellow
New-AzAppServicePlan `
    -ResourceGroupName $ResourceGroup `
    -Name "$AppName-plan" `
    -Location $Location `
    -Tier $Sku `
    -Linux | Out-Null

New-AzWebApp `
    -ResourceGroupName $ResourceGroup `
    -Name $AppName `
    -AppServicePlan "$AppName-plan" `
    -Location $Location | Out-Null

# Configura runtime Python 3.12 e monta Azure Files em /data
$azureStoragePath = New-AzWebAppAzureStoragePath `
    -Name "mpfm-data" `
    -Type AzureFiles `
    -AccountName $StorageName `
    -ShareName "mpfm-data" `
    -AccessKey $storageKey `
    -MountPath "/data"

Set-AzWebApp `
    -ResourceGroupName $ResourceGroup `
    -Name $AppName `
    -LinuxFxVersion "PYTHON|3.12" `
    -StartupFile "bash startup.sh" `
    -AzureStoragePath $azureStoragePath | Out-Null

Write-Host "    App: $AppName (Python 3.12, $Sku)" -ForegroundColor Green

# -------------------------------------------------------
# 5. Configurar variáveis de ambiente (carregadas do .env local)
# -------------------------------------------------------
Write-Host "`n[5/6] Configurando variaveis de ambiente..." -ForegroundColor Yellow

# Base — variáveis da aplicação
$appSettings = @{
    "MPFM_DATA_DIR"                = "/data"
    "MPFM_DB_PATH"                 = "/data/mpfm_local.db"
    "MPFM_PORT"                    = "8080"
    "MPFM_HOST"                    = "0.0.0.0"
    "MPFM_PUBLIC_BASE_URL"         = "https://$AppName.azurewebsites.net"
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "true"
}

# Carrega .env local (sobrepõe apenas chaves de AI providers)
$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | Where-Object { $_ -match "^[A-Z_]+=.+" -and $_ -notmatch "^#" } | ForEach-Object {
        $parts = $_ -split "=", 2
        $appSettings[$parts[0].Trim()] = $parts[1].Trim().Trim('"')
    }
    Write-Host "    .env carregado" -ForegroundColor Green
} else {
    Write-Warning ".env nao encontrado. Configure chaves de IA manualmente no portal."
}

Set-AzWebApp `
    -ResourceGroupName $ResourceGroup `
    -Name $AppName `
    -AppSettings $appSettings | Out-Null

Write-Host "    Variaveis configuradas" -ForegroundColor Green

# -------------------------------------------------------
# 6. Deploy do código via ZIP (Publish-AzWebApp)
# -------------------------------------------------------
Write-Host "`n[6/6] Criando ZIP e fazendo deploy..." -ForegroundColor Yellow

$zipPath = Join-Path $env:TEMP "mpfm_deploy.zip"
$appRoot  = $PSScriptRoot

# Lista de pastas/arquivos a excluir do ZIP
$excludeDirs  = @("data", ".git", "old", "__pycache__", ".vscode")
$excludeFiles = @(".env", "*.bak", "*.tmp", "playwright_*.json", "_diag_*.py", "_screenshot_*.py")

$allItems = Get-ChildItem -Path $appRoot -Recurse -File | Where-Object {
    $rel = $_.FullName.Substring($appRoot.Length + 1)
    $skip = $false
    foreach ($d in $excludeDirs)  { if ($rel -like "$d\*" -or $rel -like "$d/*") { $skip = $true } }
    foreach ($f in $excludeFiles) { if ($_.Name -like $f) { $skip = $true } }
    -not $skip
}

# Cria ZIP
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
$compress = @{ LiteralPath = $allItems.FullName; DestinationPath = $zipPath }
Compress-Archive @compress
Write-Host "    ZIP criado: $zipPath ($([Math]::Round((Get-Item $zipPath).Length/1MB,1)) MB)" -ForegroundColor Green

# Deploy via Az PowerShell
Publish-AzWebApp `
    -ResourceGroupName $ResourceGroup `
    -Name $AppName `
    -ArchivePath $zipPath `
    -Force | Out-Null

$appUrl = "https://$AppName.azurewebsites.net"
Write-Host "`n===============================" -ForegroundColor Cyan
Write-Host "Deploy concluido!" -ForegroundColor Green
Write-Host "URL:       $appUrl" -ForegroundColor Cyan
Write-Host "Health:    $appUrl/api/health" -ForegroundColor Cyan
Write-Host "IA Status: $appUrl/api/ai/status" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan

# -------------------------------------------------------
# Pós-deploy: copiar o banco SQLite local para Azure Files
# -------------------------------------------------------
Write-Host "`nPara carregar o banco local para Azure Files (Az PowerShell):" -ForegroundColor Yellow
$dbLocal = Join-Path $appRoot "data\mpfm_local.db"
if (Test-Path $dbLocal) {
    Write-Host "  Executando upload do banco de dados..." -ForegroundColor Yellow
    $uploadCtx = New-AzStorageContext -StorageAccountName $StorageName -StorageAccountKey $storageKey
    Set-AzStorageFileContent `
        -ShareName "mpfm-data" `
        -Source $dbLocal `
        -Path "mpfm_local.db" `
        -Context $uploadCtx `
        -Force | Out-Null
    Write-Host "  Banco carregado: /data/mpfm_local.db" -ForegroundColor Green
} else {
    Write-Warning "Banco nao encontrado em $dbLocal. Carregue manualmente via portal Azure Files."
}
