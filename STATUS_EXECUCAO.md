# MPFM Manager - Status de Execução

## Status atualizado em 2026-04-27

A aplicação foi estabilizada e validada no ambiente local deste projeto.

- Backend/frontend modularizados e funcionais.
- Regras de alocação de data de produção PDF/TXT mantidas.
- Excel mensal e Excel de produção não geram mais aba de cards.
- Carga de produção ignora subpastas de alarmes FCS320.
- Validação automatizada: `289 passed`.
- Smoke isolado da API: `SMOKE TEST PASSED`.
- ZIP de distribuição deve ser gerado por `python scripts/make_dist_package.py`.

As seções abaixo registram o diagnóstico histórico de política corporativa de execução em outro ambiente. Elas permanecem como referência para TI caso a aplicação seja copiada para máquina com AppLocker/SRP.

---

## ⚠️ PROBLAMA ENCONTRADO

A execução da aplicação MPFM foi impedida por uma **Política de Restrição de Grupo** ativa na máquina, que bloqueia todos os executáveis e scripts.

## 🔍 Diagnóstico

**Problema**: `Program 'python.exe' failed to run: This program is blocked by group policy`

**Afetados**:
- ❌ Python executável
- ❌ Scripts .bat
- ❌ Scripts .ps1
- ❌ Programas .exe

**Não Afetados**:
- ✅ PowerShell cmdlets nativos (Get-Process, etc)
- ✅ Comandos do Windows (netstat, etc)
- ✅ Leitura/Escrita de arquivos

## 🚀 Como Executar

### Método 1: Com Permissão de TI (Recomendado)

Após o administrador liberar as permissões:

```powershell
cd "c:\Users\edbo\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM\07 Applications\7.1 MPFM_PDF_TXT"

# Opção A: Usar script de inicialização
.\iniciar.bat

# OU Opção B: Executar diretamente
.\.venv\Scripts\python server.py
```

### Método 2: Copiar para Pasta Local (Possível Workaround)

```powershell
# Copiar para C:\MPFM_App
Copy-Item -Path "c:\Users\edbo\OneDrive - Equinor\..." -Destination "C:\MPFM_App" -Recurse -Force

cd C:\MPFM_App
.\.venv\Scripts\python server.py
```

⚠️ Pode ainda estar bloqueado dependendo da configuração.

## 📞 Próximos Passos

1. **Abra um ticket com TI** 
   - Assunto: "Solicitar desbloqueio - MPFM Manager Application"
   - Anexe: `EXECUTION_GUIDE.md`
   - Mencione: Necessário executar aplicação Python em `7.1 MPFM_PDF_TXT`

2. **Aguarde a autorização**
   - Pode levar 24-48 horas

3. **Após aprovação**
   - Reinicie o PowerShell
   - Execute: `cd 7.1 MPFM_PDF_TXT && .\.venv\Scripts\python server.py`

## 🌐 URLs da Aplicação

Quando rodando corretamente:
- **Principal**: http://127.0.0.1:8765
- **Health Check**: http://127.0.0.1:8765/api/health

## 📋 Verificação de Status

Para confirmar que a política está bloqueando:

```powershell
# Teste 1: Tenta executar Python
.\.venv\Scripts\python --version
# Resultado esperado: "This program is blocked by group policy"

# Teste 2: Verifica política de execução
Get-ExecutionPolicy -List

# Teste 3: Lista políticas aplicadas
gpresult /h report.html
# (Abre em navegador para análise detalhada)
```

## 📌 Informações Técnicas

**Tipo de Restrição**: AppLocker ou Software Restriction Policy (SRP)

**Arquivos Afetados**:
- `.venv\Scripts\python.exe` 
- `iniciar.bat`
- `start_app.ps1`

**Linguagem**: Python 3.x
**Framework**: FastAPI
**Porta**: 8765

---

*Documento gerado em: 2026-04-10*  
*Motivo: Tentativa de execução impedida por política de segurança*
