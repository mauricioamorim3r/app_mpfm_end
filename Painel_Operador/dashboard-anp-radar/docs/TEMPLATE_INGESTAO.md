# Radar ANP - Template geral de ingestão

O template geral fica em:

`templates/Radar_ANP_Template_Ingestao.xlsx`

Ele deve ser usado em três situações:

1. quando o arquivo original ainda não está na pasta monitorada;
2. quando o arquivo original é imagem/PDF difícil de extrair automaticamente;
3. quando for necessário carregar manualmente um dado estruturado de contingência.

## Abas do template

| Aba | Finalidade |
|---|---|
| `fontes_dados` | caminhos, tipos de fonte e responsável |
| `pontos_medicao` | cadastro técnico dos pontos |
| `medicao_diaria` | valores diários raw/XML/ANP quando necessário |
| `alarmes_eventos` | eventos e alterações de parâmetros |
| `analises_fisico_quimicas` | laudos de óleo, gás, BSW, cromatografia e PVT |
| `certificados_calibracao` | certificados, validade e faixa calibrada |
| `incerteza_medicao` | memória e cálculo de incerteza |
| `planos_coleta` | periodicidade e execução de coleta/análise |
| `pam_limites` | PAM, datasheet, limites e faixas |
| `obrigacoes_regulatorias` | norma, periodicidade, prazo e evidência |
| `regras_validacao` | regras, tolerâncias e severidade |
| `evidencias` | rastreabilidade de arquivos, páginas, linhas e observações |

## Regras de preenchimento

- Não apagar colunas.
- Usar uma linha por evento, ponto, análise, certificado ou regra.
- Sempre preencher `source_file` quando houver arquivo original.
- Sempre preencher `evidence_ref` quando a origem for página, aba, linha, evento ou anexo.
- Usar datas em `AAAA-MM-DD` e horários em `AAAA-MM-DD HH:MM:SS`.
- Em caso de dado extraído por IA, preencher `extracted_by_ai = sim` e manter `review_status = pendente` até validação humana.

## Status de revisão

| Status | Significado |
|---|---|
| `pendente` | dado carregado, mas ainda não revisado |
| `validado` | dado aprovado para uso em regra |
| `rejeitado` | dado não deve ser usado |
| `substituido` | dado foi trocado por versão mais nova |

## Rastreabilidade

Todo dado manual deve ter uma evidência. Se não houver evidência, o radar pode usar o dado apenas como hipótese operacional, nunca como conclusão de conformidade.
