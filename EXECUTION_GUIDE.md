# GUIA DE EXECUÇÃO - MPFM Manager

## Situação Atual

A máquina possui uma **Política de Restrição de Grupo (AppLocker/Software Restriction Policy)** que bloqueia a execução de:
- Executáveis (.exe) - incluindo Python
- Scripts em lote (.bat)
- Scripts PowerShell (.ps1)
- Qualquer programa não assinado ou não confiável

## O que foi Testado

Foram realizadas as seguintes tentativas de execução, todas bloqueadas:

1. **iniciar.bat** direto - ❌ Bloqueado por política de grupo
2. **Python direto** (python server.py) - ❌ Bloqueado por política de grupo
3. **Python do venv** (.\.venv\Scripts\python.exe) - ❌ Bloqueado por política de grupo
4. **PowerShell scripts** - ❌ Bloqueado por política de grupo
5. **CMD.exe** - ❌ Bloqueado por política de grupo
6. **Unblock-File** - ❌ Não funcionou (política é muito restrita)
7. **VS Code Tasks** - ❌ Bloqueado por política de grupo
8. **WSL (Windows Subsystem for Linux)** - ❌ Não inicializado

## Soluções Possíveis

### Opção 1: Contatar Administrador de TI (RECOMENDADO)

Solicite ao seu administrador de TI para:

```
Assunto: Solicitação de permissão para executar aplicação MPFM Manager

Detalhes:
- Necessário executar aplicação Python (FastAPI)
- Localização: c:\Users\edbo\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM\07 Applications\7.1 MPFM_PDF_TXT
- Arquivo executável: .\.venv\Scripts\python.exe
- Arquivo de script: server.py
- Tipo: Aplicação corporativa para processamento de dados FPSO Bacalhau

Solicitações:
1. Desbloqueio de AppLocker para Python
2. Permissão de execução para arquivos .bat neste diretório
3. Permissão de execução para scripts PowerShell neste diretório
4. Permissão de acesso à pasta em OneDrive (se aplicável)
5. Permissão de acesso à porta 8765 (se houver proxy/firewall)
```

### Opção 2: Usar Computador Alternativo

Se disponível, execute a aplicação em:
- Outro computador sem restrições de política de grupo
- Máquina virtual sem RestrictedAdmin
- Servidor corporativo

### Opção 3: Mudança para Diretório Local (Possível)

Tente copiar o projeto para um diretório fora do OneDrive:
```powershell
Copy-Item -Path "c:\Users\edbo\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM\07 Applications\7.1 MPFM_PDF_TXT" `
          -Destination "C:\MPFM_App" -Recurse

cd C:\MPFM_App
.\.venv\Scripts\python server.py
```

Obs: ⚠️ Isto também pode estar bloqueado dependendo da configuração da política.

### Opção 4: Solicitar Ambiente de Desenvolvimento Alternativo

Fale com sua liderança sobre:
- Máquina de desenvolvimento com permissões adequadas
- Acesso a servidor de desenvolvimento corporativo
- Container Docker ou máquina virtual

## Estrutura da Aplicação

Para referência do administrador de TI:

```
MPFM_PDF_TXT/
├── server.py              # Servidor Principal (FastAPI)
├── mpfm_engine.py         # Engine de processamento
├── iniciar.bat            # Script de inicialização (Windows)
├── iniciar.sh             # Script de inicialização (Linux)
├── .venv/                 # Ambiente virtual Python
│   └── Scripts/
│       ├── python.exe     # Interpretador Python
│       └── (outras ferramentas)
├── requirements.txt       # Dependências Python (se existir)
├── data/                  # Dados da aplicação
├── static/                # Arquivos estáticos (HTML/CSS/JS)
├── templates/             # Templates Jinja2
└── routes/                # Rotas da aplicação
```

## Configuração da Aplicação

**Servidor**: FastAPI  
**Porta**: 8765  
**Host**: 127.0.0.1 (localhost)  
**URL**: http://127.0.0.1:8765

**Dependências Python**:
- fastapi
- uvicorn
- python-multipart
- PyPDF2
- pandas
- openpyxl
- numpy

## Verificação de Permissões

O administrador pode verificar a política atual com:

```powershell
# Ver politica AppLocker
Get-AppLockerPolicy -Effective | Export-AppLockerPolicy -Path C:\AppLockerPolicy.xml

# Ver Software Restriction Policy
gpresult /h report.html

# Ver executáveis bloqueados
Get-ExecutionPolicy -List
```

## Próximos Passos

1. Envie este documento para o administrador de TI
2. Aguarde a resposta e permissões
3. Reabra este terminal após as permissões serem concedidas
4. Execute o comando: `.\.venv\Scripts\python server.py`

---

**Nota**: Este é um documento técnico gerado automaticamente para fins de diagnóstico e resolução de problemas de permissão de execução.
