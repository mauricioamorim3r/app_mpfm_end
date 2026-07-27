# Radar ANP - Dados necessários para ingestão

Este documento define o conjunto de dados necessário para manter o Radar ANP auditável, rastreável e preparado para novas cargas. A regra geral é: todo dado usado para decisão deve ter fonte, data operacional, identificador do ponto/equipamento, versão/arquivo de origem e evidência objetiva.

## 1. Fontes mínimas obrigatórias

| Grupo | O que entra | Formatos esperados | Chave principal | Uso no radar |
|---|---|---|---|---|
| `dailyReports` | Pacotes diários FPSO com CV, IHM e XML | Pastas, TXT, XLSX, XML, ZIP | data operacional + tag | Base diária de fechamento |
| `xmlSent` | XML/ZIP enviados à ANP: 001, 002, 003, 004, 039, 040 etc. | XML, ZIP | tipo XML + instalação + data + tag | Evidência do que foi gerado/enviado |
| `anpPanel` | Exports do Painel do Operador ANP | XLSX | data + tag + família XML | Evidência do que a ANP recebeu |
| `cvRaw` | Relatórios raw dos computadores de vazão | TXT Run_Daily, Run_Hourly, Configuration, Events | data + tag + FC | Origem bruta da medição |
| `alarmsEvents` | Alarmes, eventos e alterações de parâmetros | TXT, XML 004, XLSM consolidado | timestamp + tag/equipamento + parâmetro | Radar de mudanças sem evidência técnica |
| `cadastro` | Pontos, instalações, campos, poços, dados do ponto | XLSX | tag + instalação | Cadastro mestre e limites cadastrais |
| `mpfm` | Relatórios e consolidações MPFM | XLSX, PDF, TXT | data + poço/banco/tag | Fiscal x multifásico e reconciliação |
| `physchem` | Análises físico-químicas e boletins | XLSX, PDF, CSV, imagens | amostra + data + ponto/corrente | API, densidade, BSW, cromatografia, PVT |
| `samplingPlans` | Planos de coleta/amostragem | XLSX, PDF, DOCX | ponto/corrente + periodicidade | Verificação de execução e prazo |
| `calibration` | Certificados de calibração | PDF, XLSX, imagens | instrumento + série + validade | Validade, faixa calibrada, erro, incerteza |
| `uncertainty` | Memórias/certificados de incerteza | PDF, XLSX | ponto + sistema + versão | Incerteza diária e limite metrológico |
| `equipmentDocs` | Datasheets, PAM, folhas de dados, desenhos | PDF, XLSX, DOCX, imagens | tag/equipamento + revisão | Limites superiores/inferiores e faixa de medição |
| `regulations` | Normas, manuais, procedimentos | PDF, DOCX, HTML | documento + revisão | Base normativa de regras e prazos |
| `requirementsMatrix` | Matriz consolidada de requisitos SGM | PDF/CSV/JSON | ID do requisito RM | Obrigações, periodicidades, critérios e evidências esperadas |

## 2. Dados por ponto de medição

Para cada ponto fiscal, operacional ou multifásico, o radar precisa dos campos abaixo.

| Campo | Obrigatório | Origem preferida | Observação |
|---|---:|---|---|
| instalação | sim | Painel ANP / cadastro | Ex.: FPSO BACALHAU |
| código da instalação | sim | Painel ANP / cadastro | Ex.: 38480 |
| tag do ponto | sim | cadastro | Chave técnica principal |
| fluido | sim | cadastro | óleo, gás, água, multifásico |
| tipo de medição principal/secundária | sim | cadastro | fiscal, operacional, apropriação etc. |
| tipo de medidor | sim | cadastro/equipmentDocs | turbina, ultrassônico, placa, Coriolis etc. |
| computador de vazão | desejável | cadastro/CV | Relaciona FC e tag |
| número de série do medidor | sim | Painel ANP / certificado | Chave para calibração |
| número de série instrumentos P/T/DP/densidade | sim | XML/Painel/certificado | Necessário para validade metrológica |
| PAM/faixa de operação | sim | cadastro/PAM/datasheet | limite inferior/superior operacional |
| faixa calibrada | sim | certificado | valor inferior/superior calibrado por instrumento |
| limite de alarme | sim | CV/XML/Painel | pressão, temperatura, DP, BSW, densidade |
| incerteza máxima permitida | sim | cadastro/norma/memória | usado como limite de conformidade |
| incerteza calculada diária | desejável | memória/algoritmo | inicialmente pode ser manual/template |
| status ativo/fora de operação | sim | cadastro | evita falso alerta em ponto inativo |

## 3. Dados diários de medição

| Campo | Origem | Comparação |
|---|---|---|
| volume bruto | CV Run_Daily -> XML -> Painel ANP | raw x XML x ANP |
| volume bruto corrigido / base / standard | CV Run_Daily -> XML -> Painel ANP | raw x XML x ANP |
| volume líquido | CV Run_Daily -> XML -> Painel ANP | raw x XML x ANP |
| totalizador inicial/final | CV/XML/Painel | continuidade e fechamento |
| pressão média/estática | CV/XML/Painel | limite inferior/superior |
| temperatura média | CV/XML/Painel | limite inferior/superior |
| diferencial de pressão | CV/XML/Painel | limite inferior/superior |
| duração de fluxo efetivo | CV/XML/Painel | disponibilidade e qualidade |
| BSW em linha | XML 040 / Painel / laboratório | BSW online x lab x limite |
| densidade | laboratório / CV / XML / Painel | evento de atualização x boletim |
| cromatografia | laboratório / CV / XML / Painel | evento de atualização x laudo |
| PVT | MPFM / memória / relatório | evento de atualização x versão PVT |

## 4. Dados de alarmes e eventos

O radar deve ingerir eventos com pelo menos:

| Campo | Obrigatório | Exemplo |
|---|---:|---|
| data/hora do evento | sim | 2026-06-02 00:10 |
| origem | sim | PMAE 004, AlarmsAndEvents, CV Event Snapshot |
| tag/equipamento afetado | sim | 43FT0102 |
| tipo de evento | sim | alteração de parâmetro, alarme, configuração |
| parâmetro alterado | sim, se aplicável | densidade, cromatografia, PVT, MF, KF, range |
| valor anterior | desejável | 0.8566 |
| valor novo | desejável | 0.8537 |
| usuário/responsável | desejável | operador/sistema |
| motivo/comentário | desejável | boletim BAC-FM-... |
| arquivo de evidência | sim | TXT/XML/XLSX/PDF |

## 5. Dados analíticos físico-químicos

| Tipo | Campos mínimos | Uso |
|---|---|---|
| óleo fiscal | data da amostra, boletim, API, densidade, BSW, método, ponto/corrente | validação de densidade/API/BSW em XML e CV |
| gás fiscal | data, cromatografia completa, poder calorífico, densidade relativa, método | validação de composição e cálculo |
| multifásico/PVT | data, versão PVT, banco/poço, óleo/gás/água, densidades, fatores | reconciliação MPFM e atualização de modelo |
| BSW | data, boletim, BSW lab, BSW em linha, método | divergência lab x online x XML 040 |

## 6. Dados de calibração e incerteza

| Tipo | Campos mínimos | Regra |
|---|---|---|
| certificado de calibração | instrumento, série, tag, data calibração, validade, faixa calibrada, erro, incerteza, laboratório | alerta se vencido ou medição fora da faixa calibrada |
| certificado/memória de incerteza | ponto, versão, data, incerteza calculada, limite normativo, componentes | alerta se incerteza diária > limite |
| datasheet/PAM | tag, range mínimo/máximo, unidade, revisão, fonte | alerta se operação fora do envelope |

## 7. Dados regulatórios

Para auditoria, cada regra deve apontar para:

| Campo | Conteúdo |
|---|---|
| obrigação | envio XML, análise, calibração, falha, teste de poço etc. |
| base normativa | resolução, portaria, manual ou procedimento |
| periodicidade | diária, mensal, sob evento, anual etc. |
| prazo | data limite ou janela de atendimento |
| evidência esperada | arquivo, relatório, XML, certificado, laudo |
| regra de conformidade | condição objetiva para OK/atenção/crítico |

## 8. Template manual de contingência

Quando o arquivo original não estiver disponível ou não puder ser lido automaticamente, preencher o template geral:

`templates/Radar_ANP_Template_Ingestao.xlsx`

O template não substitui a evidência original. Ele serve como camada de contingência para ingestão estruturada e deve sempre referenciar o arquivo, documento ou justificativa que originou o dado.

## 9. Fontes fiscais reais já identificadas

| Pasta | Conteúdo esperado | Grupo de ingestão |
|---|---|---|
| `02 FISCAL/01 OIL METERING SKID - 20JX101/01 Densidade e BSW` | laudos, boletins e evidências de atualização de densidade/BSW | `physchem` |
| `02 FISCAL/01 OIL METERING SKID - 20JX101/02 PVT` | relatórios PVT e versões aplicáveis | `physchem` |
| `02 FISCAL/01 OIL METERING SKID - 20JX101/03 PEV` | evidências operacionais associadas | `physchem` / `equipmentDocs` |
| `OneDrive_2026-06-16 (10)/03 ALLOCATION/.../Cromatografia` | relatórios de composição de gás | `physchem` |
| `OneDrive_2026-06-16 (10)/03 ALLOCATION/.../PVT` | relatórios PVT multifásicos/alocação | `physchem` / `mpfm` |
| `OneDrive_2026-06-16 (1)/02 FISCAL/.../Primary` | validações de corrida de calibração/proving | `calibration` |
| `OneDrive_2026-06-16 (1)/02 FISCAL/.../Secondary` | checklists/certificados secundários P/T/DP | `calibration` |
| `OneDrive_2026-06-16 (1)/02 FISCAL/.../Uncertainty` | cálculo de incerteza | `uncertainty` |
| `OneDrive_2026-06-16 (14)/02 PAM Bacalhau` | portarias/PAM INMETRO | `equipmentDocs` / `regulations` |
| `02 - Memorial Descriptive` | memorial do gerador XML, MPFM e descrição funcional | `equipmentDocs` / `regulations` |
