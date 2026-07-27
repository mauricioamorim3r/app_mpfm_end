# MPFM - Como Executar

## ❌ Problema: Política de Restrição de Grupo

Sua máquina está configurada com uma política de segurança que bloqueia a execução de programas Python e scripts. 

## ✅ Solução: Contacte o Administrador de TI

**Envie esta mensagem ao TI:**

```
Olá,

Preciso de permissão para executar uma aplicação Python nesta máquina:

📁 Caminho: c:\Users\edbo\OneDrive - Equinor\DPB FPSO Bacalhau - Metering - 02 MULTIPHASE MANAGEMENT SYSTEM\07 Applications\7.1 MPFM_PDF_TXT

🎯 Objetivo: Aplicação de processamento de dados FPSO (MPFM Manager)

🔧 Necessário desbloqueio de:
- Python executável (.venv\Scripts\python.exe)
- Scripts batch (.bat)
- Acesso à pasta OneDrive/Equinor (se restrito)
- Porta 8765 (se houver firewall)

Obrigado!
```

## 🚀 Após Receber Permissão

Execute um destes comandos:

**Opção 1** (Automático):
```
.\iniciar.bat
```

**Opção 2** (Direto):
```
.\.venv\Scripts\python server.py
```

## 🌐 Acessar Aplicação

Quando em execução:
- Abra navegador: **http://127.0.0.1:8765**

## 📝 Documentação Completa

Veja `EXECUTION_GUIDE.md` ou `STATUS_EXECUCAO.md` para informações técnicas detalhadas.

---
*Gerado em 10 de abril, 2026*
