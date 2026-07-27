# Regras de qualidade e aceite — PE-4 RANP44 180 dias

## Bloqueios críticos
1. Janela diferente de 180 datas esperadas.
2. Duplicidade de data válida para PE_4 sem regra de consolidação.
3. Dados misturados com PE_2, PW-104DA, Riser_P4, Riser_P5 ou outro medidor.
4. Massa HC ou massa total calculada divergente da soma das fases.
5. Referência ausente e resultado classificado como conforme.
6. Critério oficial ausente e status classificado como aprovado/reprovado.
7. Unidade não declarada ou conversão não registrada.
8. Fonte de dado não rastreada por arquivo, tabela, linha, protocolo ou timestamp.

## Alertas
1. Dia sem dado horário, mas com dado diário.
2. Divergência app x XML 042 x Excel mensal.
3. GVF/BSW/P/T sem min/máx/média.
4. PVT/cromatografia/certificados vencidos ou sem validade declarada.
5. Rota PE_4 com inconsistência de riser/caminho PI/AF.

## Métricas no log
- datas esperadas;
- datas preenchidas;
- datas válidas;
- datas parciais;
- datas bloqueadas;
- arquivos consumidos;
- linhas PE_4 consumidas por fonte;
- linhas descartadas por entity/tag/riser divergente;
- divergências app vs Drive vs XML042;
- campos obrigatórios pendentes.
