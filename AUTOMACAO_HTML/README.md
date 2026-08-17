# Pacote de distribuição — Automação Base_Unica

Pacote portátil para usuários Windows gerarem a Base_Unica, o histórico incremental, dashboards HTML, PETEC e XML042.

## Instalação rápida

1. Instale Python 3.10 ou superior e marque **Add Python to PATH**.
2. Extraia esta pasta para um local com permissão de gravação.
3. Execute `instalar_dependencias.bat` uma vez.
4. Execute `executar_base_unica.bat` e informe os caminhos solicitados.

O pacote **não contém credenciais, e-mails, PDFs, planilhas históricas ou caminhos pessoais**. Cada usuário deve ter acesso às suas próprias pastas de origem.

## Fluxo principal

O programa pede:

- pasta raiz dos PDFs MPFM;
- pasta raiz dos Daily Reports/TXT do SEP;
- opção operacional e janela de datas.

A opção recomendada para começar é **7 — Apenas Base_Unica**. Use `--no-pi` quando o coletor PI não estiver instalado ou não for necessário.

Exemplo direto:

```powershell
python gerar_base_unica_standalone.py --operation-mode 7 --mpfm-root "D:\Relatorios\MPFM" --sep-root "D:\Relatorios\SEP" --no-pi --ask-period
```

As saídas são gravadas ao lado do script, salvo se `--output`, `--master-output` ou os parâmetros de dashboard forem informados.

## Integrações opcionais

- **E-mail/ZIP:** requer Outlook desktop configurado. Defina `DPB_MAILBOX`, `DPB_DAILY_REPORTS_DESTINATION` e `DPB_FCVS_DESTINATION` antes de usar os modos 1, 3, 4 ou 5.
- **PI Vision:** requer o coletor PI/Daily Control instalado separadamente, Edge com sessão autenticada e acesso aos displays corporativos. Configure `BASE_UNICA_PI_ROOT` e `BASE_UNICA_DAILY_CONTROL_ROOT`, ou use `--pi-root`.
- **XML042:** use `XML042_STANDALONE_PACOTE\executar_xml042_standalone.bat` depois de gerar `BASE_UNICA_TOTAL.xlsx`. Revise catálogo, CNPJ e `registry_path` antes da geração oficial. A emissão é única por data + código ANP do poço e não admite sobrescrita, mesmo com outro nome ou diretório. O pacote já inclui o histórico inicial dos nove XMLs reais fornecidos em 12/08/2026; outros acervos antigos podem ser importados por `history_dirs` ou `--history-dir`. Um conflito histórico para o mesmo dia + poço bloqueia a emissão até ser investigado. Um dia oficial comprovadamente zerado continua elegível; valores ausentes, negativos ou duplicados são rejeitados.
- **PETEC:** execute `preencher_petec.py`; a rotina exige `BASE_UNICA_TOTAL.xlsx`, `dados para PETEC.xlsx` e uma pasta SEP válida. Use `--bank`, `--tag` ou `--instrument` para restringir o MPFM. `--allow-missing-sep` deve ser usado somente quando a saída com abas SEP vazias for intencional.

## Identidade MPFM corrigida

O cadastro não possui B17. Os instrumentos `18FT1506 / PE_4` e `18FT1706 / PE_EO105` pertencem ao banco B05, em seções físicas distintas do mesmo PDF.

No B05, `18FT1406 / PE_EO10` e `18FT1806 / PE_EO4` também são mantidos como instrumentos independentes; não são aliases de `18FT1706 / PE_EO105`.

## Comparações e CEP mensal

- Convenção única: `(MPFM corrigido − referência) / referência × 100`.
- Subsea × Topside: Subsea é o numerador e o riser Topside é a referência.
- MPFM × SEP: o TXT do Separador é extraído como fonte independente na Base Única. A comparação só é calculada no HTML depois que o usuário escolhe MPFM, variável, granularidade e período; pode ser exportada em CSV compatível com Excel e não recebe veredito regulatório automático.
- HC usa limite ±10%; Total usa ±7%; referência abaixo de 0,1 t não produz percentual.
- O CEP do HTML usa, por padrão, todos os dias da Base Única pertencentes ao mês da janela escolhida, com filtros por mês, par e métrica.
- PE‑02/18FT0506 é comparado ao Riser P2/13FT0217.

## Estrutura incluída

- `gerar_base_unica_standalone.py` — gerador principal autocontido.
- `migrar_base_unica_normalizada.py` — cria as abas normalizadas sem apagar a Base legada. Execute primeiro com `--output` para validar em uma cópia e só então substitua a Base oficial.
- `executar_base_unica.bat` — launcher assistido.
- `preencher_petec.py` e `dados para PETEC.xlsx` — preenchimento PETEC.
- `OUTRAS_AUTOMACOES` — download/organização de ZIPs e PDFs/TXTs.
- `XML042_STANDALONE_PACOTE` — geração XML042.
- `logo.png` — logo usado nos dashboards.

## Modelo normalizado da Base Única

A Base Única passa a manter as fontes históricas sem repetir as mesmas medições em abas de apresentação:

- `MPFM_MEDICOES` guarda MPFM diário e horário.
- `SEP_CV_OLEO`, `SEP_CV_GAS` e `SEP_CV_AGUA` guardam as fases do C.V. separadamente.
- `RECONCILIACAO`, `CADASTRO_MEDIDORES`, `FONTES_IMPORTADAS` e `LOG_IMPORTACAO` preservam cálculo, cadastro e rastreabilidade.

O dashboard monta em memória HC e Total do Separador a partir das três fases. Rankings, comparativos e cartões continuam sendo visões do HTML, não cópias persistidas no Excel. Durante a transição, `BASE_UNICA_TOTAL` permanece preservada para compatibilidade.

## Solução de problemas

- `ModuleNotFoundError`: execute novamente `instalar_dependencias.bat`.
- Nenhum PDF encontrado: confirme que `--mpfm-root` aponta para a pasta acima das subpastas dos bancos.
- SEP incompleto: confirme as pastas `FC13`, `FC14` e `FC17`.
- Arquivo Excel bloqueado: feche `BASE_UNICA_TOTAL.xlsx` no Excel antes de executar.
- PI indisponível: use `--no-pi` ou `--continue-without-pi`.

Para preservar rastreabilidade, compartilhe o Excel e o HTML gerados junto com o manifesto `*_VALIDACAO.json` quando ele existir.
