# Radar ANP - Análise do material recebido em Painel_Operador

Data da análise: 2026-06-16.

## 1. Novas fontes relevantes identificadas

Além dos arquivos de envio ANP, relatórios diários CV/IHM e exports do Painel do Operador, a pasta contém agora uma base documental ampla para construir o radar metrológico completo.

| Área | Evidência encontrada | Uso no radar |
|---|---|---|
| Matriz SGM1 | `Matriz_dos_Requisitos_Metrologicos_Operacionais_SGM1.pdf` | base de requisitos, periodicidades, critérios, penalidades e evidências |
| Fiscal - óleo | `02 FISCAL/01 OIL METERING SKID - 20JX101` | densidade, BSW, PVT, PEV, calibração, incerteza e trilha de medição fiscal |
| Fiscal - flowline/well injection | `02 FISCAL/02 WELL INJECTION - 13JX151` e duplicatas em pacotes OneDrive | flowline, calibração, incerteza, certificados secundários |
| Fiscal - flare/gás | `03 HP FLARE - 43FT0102`, `04 LP FLARE - 43FT0227`, `05 PILOT - 45FT0360`, `06 TOTAL FUEL GAS - 45FT0555`, `07 GAS TO IGG - 45FT0640` | gás fiscal, composição, pressão/temperatura, certificados e eventos |
| Memorial descritivo | `02 - Memorial Descriptive` | entendimento do sistema gerador XML, MPFM e descrição funcional |
| Calibração | `Calibration Plan`, `Validacao de Corrida de Calibracao`, checklists secundários | validade, proving, MF/KF, rastreabilidade e faixa calibrada |
| Incerteza | `Checklist Calculo de Incerteza_rev2.xlsx`, templates de uncertainty | cálculo/limite de incerteza por ponto |
| PAM | `OneDrive_2026-06-16 (14)/02 PAM Bacalhau` | portarias INMETRO, autorização/adequação legal e faixa/escopo |
| PVT/cromatografia | `OneDrive_2026-06-16 (10)/03 ALLOCATION/.../PVT` e `Cromatografia` | validação de atualização de PVT/composição |
| Densidade/BSW | `02 FISCAL/01 OIL METERING SKID.../01 Densidade e BSW` | validação de evento de densidade/BSW contra laudo |

## 2. Volumetria resumida

Inventário sem `node_modules`, `dist`, `.git` e artefatos de navegador:

| Grupo superior | Arquivos | Perfil |
|---|---:|---|
| `FPSO-Bacalhau_Daily reports_2026-06-01` | 2095 | TXT CV, XML, ZIP, XLSX |
| `FPSO-Bacalhau_Daily reports_2026-06-02` | 2044 | TXT CV, XML, ZIP, XLSX |
| `02 FISCAL` | 595 | PDF, TXT, ZIP, PNG, MSG |
| `OneDrive_2026-06-16 (9)` | 595 | espelho de material fiscal |
| `OneDrive_2026-06-16 (1)` | 508 | fiscal, calibração, incerteza, XML, imagens |
| `OneDrive_2026-06-16 (6)` | 149 | offloading/calibração |
| `OneDrive_2026-06-16 (8)` | 85 | Book ANP, templates, calibração/incerteza |
| `OneDrive_2026-06-16 (10)` | 26 | allocation, PVT, cromatografia |
| `02 - Memorial Descriptive` | 11 | DOCX/PDF de memorial e descrição funcional |
| `OneDrive_2026-06-16 (14)` | 7 | PAM Bacalhau |

## 3. Matriz SGM1 extraída

A matriz foi extraída para:

- `data/matriz_requisitos_sgm1.json`
- `data/matriz_requisitos_sgm1.csv`

Resumo:

| Categoria | Quantidade |
|---|---:|
| Metrológico | 19 |
| Operacional | 15 |
| Regulatório | 8 |
| Total | 42 |

Principais subcategorias:

- Calibração: 11 requisitos.
- Procedimentos de Campo: 4.
- Envio de Dados: 4.
- Validação de Dados: 3.
- Padrões de Medição: 2.
- Fator de Correção: 2.
- Conformidade Regulatória: 2.
- Gestão de Equipamentos: 2.
- Amostragem: 2.
- Multifásico: 2.

## 4. Requisitos SGM1 com impacto direto no radar

| ID | Requisito | Impacto no radar |
|---|---|---|
| RM-001 | Calibração de medidores ultrassônicos | monitorar certificado, validade, classe e rastreabilidade |
| RM-002 | Proving em campo | monitorar corridas, variação, fator de medição e evidência |
| RM-021 | Plano de amostragem físico-química de petróleo | cruzar plano, coleta, laudo, implementação em FCS e prazo |
| RM-022 | Plano de amostragem físico-química de gás natural | cruzar cromatografia, composição, CG/FCS e periodicidade |
| RM-038 | Tanques e arqueamento | controlar tabela de arqueamento e programação antes do vencimento |
| RM-039 | Teste de estanqueidade de válvulas | controlar execução anual e resultado pass/fail |
| RM-040 | Auditoria interna do SGM | controlar relatório, NCs, plano de ação e evidências |
| RM-042 | Aprovação de modelo INMETRO | controlar portarias/PAM e validade legal dos instrumentos |

## 5. Regras novas recomendadas

1. Evento de densidade sem laudo em `Densidade e BSW` no período aplicável.
2. Evento de cromatografia sem relatório cromatográfico ou composição implementada.
3. Evento de PVT sem relatório PVT/versão aplicável.
4. Alteração de MF/KF sem proving/calibração correspondente.
5. Medição diária fora do PAM ou fora da faixa calibrada.
6. Certificado secundário vencido ou série divergente do XML/Painel.
7. Incerteza sem memória válida ou acima do limite.
8. Requisito RM com periodicidade vencendo sem evidência esperada.

## 6. Próximo passo técnico

Implementar o correlacionador `evento -> evidência esperada`:

1. extrair eventos de PMAE 004, `AlarmsAndEvents` e configuração CV;
2. classificar parâmetro afetado: densidade, BSW, cromatografia, PVT, MF/KF, range, limite, PAM;
3. buscar evidência nas fontes configuradas;
4. comparar janela de data, tag/equipamento, valor e versão;
5. registrar divergência auditável com arquivo, página/aba/linha e regra RM associada.
