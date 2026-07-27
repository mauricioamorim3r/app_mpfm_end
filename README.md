# MPFM Manager — Bacalhau FPSO
## Aplicação Local de Reconciliação de Produção

---

## STATUS DA ENTREGA — 2026-04-27

Entrega estabilizada para operação local.

- Regras de data de produção preservadas: PDF usa período do conteúdo; TXT SEP usa período/conteúdo antes de fallback por nome.
- Carga de produção PDF/TXT ignora subpastas reservadas de alarmes, evitando que PDFs FCS320 sejam tratados como medição.
- Aba `CARDS_RESUMO` removida dos workbooks mensais e do Excel de produção por decisão operacional; cards seguem disponíveis na UI/API.
- Gráficos, XML042, alarmes FCS320 e exportações CSV/XLSX foram validados em runtime isolado.
- Validação automatizada final: `python -m pytest -q` com `289 passed` e `python scripts/api_smoke_test.py` com `SMOKE TEST PASSED`.

---

## O QUE É

Aplicação web que roda **100% no seu computador** — sem internet, sem API externa.
Você abre no browser como qualquer site, mas o servidor e o processamento são locais.

- Lê PDFs MPFM (Daily e Hourly) com extração por regex — sem IA
- Lê TXTs do Separador de Testes (OLEO / GAS / AGUA)
- Gera e atualiza Excel mensal incremental (adiciona dias sem apagar os anteriores)
- Mantém histórico local em SQLite com base de rastreabilidade `RAW` e `CURATED`
- Exporta Excel de produção sem aba de cards para manter o arquivo mais leve
- Funciona em Windows, Mac e Linux

---

## ESTRUTURA DE ARQUIVOS

```
mpfm_app/
├── app_config.py       ← Configuração central do app
├── db_schema.py        ← Schema e migrações SQLite
├── server.py           ← Composição principal do app FastAPI
├── scripts/           ← Utilitários de validação e apoio operacional
├── routes/            ← Rotas por domínio (system, ops, sep, recon, cards...)
├── services/          ← Regras de negócio e pipeline de ingestão
├── repositories/      ← Acesso a dados SQLite por domínio
├── index.html         ← Interface web (abre no browser)
├── static/            ← Frontend modularizado (`app.summary.js`, `app.sep.js`, etc.)
├── mpfm_engine.py     ← Motor de extração e geração do Excel  ← COPIE AQUI
├── docs/              ← PRD, memória do projeto e roadmap técnico
├── iniciar.bat        ← Atalho Windows (duplo clique)
├── iniciar.sh         ← Atalho Linux/Mac
├── data/
│   ├── uploads/       ← Pasta temporária de uploads (auto)
│   ├── outputs/       ← Arquivos Excel gerados
│   └── mpfm_local.db  ← Banco local SQLite
└── README.md
```

> **IMPORTANTE:** Copie o arquivo `mpfm_engine.py` para dentro desta pasta `mpfm_app/`

---

## COMO INSTALAR

### Requisito único: Python 3.9 ou superior

Verifique se já tem:
```
python --version        (Windows)
python3 --version       (Linux/Mac)
```

Se não tiver, baixe em: https://www.python.org/downloads/

---

## COMO INICIAR

### Windows
Dê **duplo clique** no arquivo `iniciar.bat`

O script instala as dependências automaticamente e abre o browser.

### Windows - modo equipe (uma maquina host)
Na maquina que vai hospedar o sistema, use `iniciar_rede.bat`.

Esse atalho:
- sobe o servidor com bind em `0.0.0.0`
- mostra os enderecos `http://IP_DA_MAQUINA:8765`
- mantém o banco ativo em uma unica maquina

Os outros usuarios devem acessar somente pelo navegador, usando o IP exibido na inicializacao.
Nao devem abrir o arquivo `mpfm_local.db` diretamente no VS Code em suas maquinas.

Se o Windows bloquear a execucao dos scripts por politica de grupo, tente `iniciar_com_shell.ps1` ou solicite liberacao da TI conforme `EXECUTION_GUIDE.md`.

### Linux / Mac
```bash
chmod +x iniciar.sh
./iniciar.sh
```

### Ou manualmente (qualquer sistema)
```bash
# Instalar dependências (só precisa fazer uma vez)
pip install fastapi uvicorn python-multipart PyPDF2 pandas openpyxl numpy

# Iniciar o servidor
python server.py        (Windows)
python3 server.py       (Linux/Mac)
```

Depois abra o browser em: **http://localhost:8765**

## CONFIGURAÇÃO

O servidor aceita configuração por variável de ambiente:

```bash
MPFM_DATA_DIR=./data
MPFM_DB_PATH=./data/mpfm_local.db
MPFM_HOST=0.0.0.0
MPFM_PORT=8765
MPFM_PUBLIC_BASE_URL=http://localhost:8765
```

O frontend agora usa automaticamente o host atual do navegador para encontrar a API local.
O frontend também foi quebrado em módulos JS por domínio, para facilitar manutenção e evolução.

### Operacao recomendada para equipe pequena

Quando houver 2-3 usuarios, a operacao recomendada e:
- uma unica maquina host executa o servidor
- o banco SQLite ativo fica somente nessa maquina
- os demais acessam via browser pelo IP da maquina host

Evite manter o banco SQLite live em pasta sincronizada por SharePoint/OneDrive para uso concorrente entre maquinas.
Se o codigo precisar ficar no SharePoint, o banco ativo deve apontar para um caminho local da maquina host via `MPFM_DATA_DIR` e `MPFM_DB_PATH`.

---

## COMO USAR

### 1. Configure o mês
Na barra superior, coloque o mês no formato `AAAA-MM` (ex: `2026-03`).
O nome do arquivo Excel é sugerido automaticamente.

### 2. Envie os arquivos — duas opções:

**Opção A — Upload direto:**
- Aba "Enviar Arquivos" → arraste os PDFs e TXTs ou clique para selecionar
- Pode enviar tudo de uma vez, em qualquer ordem

**Opção B — Via pasta:**
- Aba "Via Pasta" → informe o caminho da pasta onde estão os arquivos
- O sistema busca em subpastas automaticamente
- Ideal para processar um dia inteiro de uma vez

### 3. O sistema detecta automaticamente

| Nome do arquivo          | Tipo detectado  |
|--------------------------|-----------------|
| `B10_MPFM_Daily-*.pdf`   | Daily PDF       |
| `B10_MPFM_Hourly-*.pdf`  | Hourly PDF      |
| `Run_*_OLEO.txt`         | Separador Óleo  |
| `Run_*_GAS.txt`          | Separador Gás   |
| `Run_*_AGUA.txt`         | Separador Água  |

### 4. Base incremental
- O Excel do mês é **atualizado** a cada processamento
- Dias já processados são **pulados** automaticamente
- Para reprocessar um dia: clique em "Reset Mês" e reenvie

### 5. Baixar o Excel
- Botão "Baixar Excel" na barra superior — qualquer hora
- Ou aba "Arquivos" para ver todos os Excel gerados

---

## ESTRUTURA DE PASTAS RECOMENDADA PARA OS DADOS

```
2026-03/
├── MPFM_Daily_FCS/
│   ├── B10_MPFM_Daily-20260302-000000+0000.pdf
│   └── B08_MPFM_Daily-20260223-000000_0000.pdf
├── MPFM_Hourly_FCS/
│   ├── B10_MPFM_Hourly-20260301-010000+0000.pdf
│   ├── B10_MPFM_Hourly-20260301-020000+0000.pdf
│   └── ...
└── SEP_TESTE_CV/
    ├── Run_24Hours1-1.20260302000000_OLEO.txt
    ├── Run_24Hours2-1.20260302000000_GAS.txt
    └── Run_24Hours1-1.20260302000000_AGUA.txt
```

---

## CONFIGURAÇÕES AVANÇADAS

| Campo              | Descrição                                    | Padrão   |
|--------------------|----------------------------------------------|----------|
| Mês                | Ano-mês no formato AAAA-MM                   | —        |
| Arquivo Excel      | Nome do arquivo de saída                     | Auto     |
| Density SEP (kg/m³)| Densidade de simulação do separador de testes| 790.78   |

---

## DEPENDÊNCIAS PYTHON

```
fastapi           — Servidor web
uvicorn           — Runner ASGI
python-multipart  — Upload de arquivos
PyPDF2            — Leitura de PDFs
pandas            — Manipulação de dados
openpyxl          — Geração de Excel
numpy             — Cálculos numéricos
```

## DOCUMENTAÇÃO INTERNA

- `docs/PRD_EVOLUCAO_MPFM_APP.md`
- `docs/PROJECT_MEMORY.md`
- `docs/ROADMAP_TECNICO.md`
- `docs/QA_STABILIZATION_LOG.md`
- `docs/HANDOFF_OPERACIONAL.md`
- `docs/CHECKLIST_ACEITE_UI.md`

## VALIDAÇÃO RÁPIDA

Para rodar uma checagem automática isolada da API:

```bash
python scripts/api_smoke_test.py
```

Isso sobe uma instância temporária com banco local descartável e valida fluxos principais como:
- health
- preferências
- deadlines
- alinhamentos SEP
- medições manuais MPFM e SEP
- PVT
- cards manuais

Para validar somente leitura contra uma instância já rodando:

```bash
python scripts/api_smoke_test.py --base-url http://127.0.0.1:8765
```

---

## SOLUÇÃO DE PROBLEMAS

**"Porta 8765 já está em uso"**
→ Outro processo está usando a porta. Feche outros servidores ou defina `MPFM_PORT=8766` antes de iniciar.

**"mpfm_engine.py não encontrado"**
→ Copie o `mpfm_engine.py` para dentro da pasta `mpfm_app/`.

**"Módulo não encontrado"**
→ Execute `pip install fastapi uvicorn python-multipart PyPDF2 pandas openpyxl numpy` e tente novamente.

**Excel não abre / está corrompido**
→ Verifique na aba Log se houve erros durante o processamento.

**Preciso validar se o app está saudável**
→ Consulte `GET /api/health` para ver status, versão, último dia processado e contagens principais.

**Outras maquinas nao conseguem acessar pelo navegador**
→ Confirme que a maquina host foi iniciada com `iniciar_rede.bat` e libere a porta `8765/TCP` no Firewall do Windows da maquina host.

**Usuarios estao tentando abrir o banco pelo VS Code em maquinas diferentes**
→ Nao compartilhe o arquivo SQLite live entre maquinas. Deixe o banco ativo somente na maquina host e use acesso HTTP pelo navegador.

---

## VERSÃO WEB (alternativa com internet)

Além desta versão local, existe também uma versão que roda como artifact no Claude.ai.
A versão web usa a API da Anthropic para extrair PDFs (mais flexível) mas requer conexão.
Esta versão local usa regex direto (mais rápida e sem dependência de internet).
