# Painel Operador - Manual de preenchimento e leitura operacional

Este manual define como usar os campos do Painel Operador dentro do MPFM e quais informacoes devem aparecer como resultado de medicao. A regra principal e simples: o topo da tela deve mostrar o que ajuda a fechar, comparar ou auditar um dia de producao. Contagens internas de arquivos, duplicidades e staging ficam como saude da integracao.

## 1. O que deve comandar a tela

Use como indicadores principais:

- Dias de producao no periodo, separados em completos, parciais, atencao e sem dado.
- XMLs oficiais por familia: 001 oleo, 002 gas, 003 gas diferencial, 039 falhas e 040 BSW.
- Dados medidos por dia/tag/familia: fiscal, ANP, MPFM, checklist e comparacoes.
- Pendencias abertas que impedem fechamento ou exigem reprocessamento.
- Checklist Diario importado por abas e periodo.
- Limites/PAM e alteracoes de CV que indiquem operacao fora de faixa ou mudanca de configuracao.

Nao use como KPI principal:

- Arquivos catalogados: serve para auditoria de fonte e busca de lacunas.
- Duplicados leves: serve para higiene de ingestao e prevencao de uso de fonte repetida.
- Staging total: serve para saber se o contrato tecnico sincronizou.
- Linhas totais de export ANP: so tem valor quando quebradas por familia, periodo, tags e status.

## 2. Visao Geral

### Campos principais

- **Dias de producao**: quantidade de dias lidos no recorte. Deve ser interpretada com o status do dia.
- **XML/ANP oficiais**: quantidade de arquivos e linhas oficiais por familia. Para fechamento mensal, avalie se ha XML 001, 002, 003, 039 e 040 esperados.
- **Dados medidos**: total fiscal, ANP e MPFM do recorte. Use para detectar ausencia ou divergencia, nao para substituir a tela de comparacao.
- **Pendencias abertas**: itens que exigem baixa, correcao, proposta ou nota tecnica.
- **Checklist Diario**: linhas e abas importadas do arquivo diario, quando ainda necessario.
- **Limites & CV**: comparacoes de configuracao, mudancas de parametros, faixas calibradas e PAM.

### Inventario tecnico

Os cards de arquivos catalogados, duplicados, export ANP total e staging tecnico devem ficar em area secundaria. Eles explicam a confiabilidade da ingestao, mas nao medem producao.

## 3. Ingestao

Preencha ou revise os caminhos das fontes. Cada caminho pode apontar para pasta ou arquivo, e o processo pode varrer subpastas.

Campos esperados:

- **Fonte**: grupo operacional, como XML ANP, exports ANP, MPFM, checklist, certificados, analises ou regulamentos.
- **Caminhos**: uma entrada por linha, preferencialmente pastas de origem oficiais.
- **Subpastas**: habilite quando os arquivos diarios ficam em estrutura por mes/dia/equipamento.
- **Status**: valida se o caminho existe e contem arquivos coerentes.

Use esta tela quando houver lacuna de dados no fechamento, nao para decidir medicao.

## 4. Exports ANP

Os exports ANP sao espelho/confirmacao do que a ANP recebeu. Eles nao substituem a fonte interna de medicao.

Preenchimento e leitura:

- **Familia**: use 001, 002, 003, 039 e 040 para separar oleo, gas, gas diferencial, falhas e BSW.
- **Periodo**: sempre filtre pelo dia ou mes de producao.
- **Tag**: use para comparar ponto a ponto.
- **Tipo**: selecione o tipo de registro importado quando houver mais de um layout.

Boa leitura operacional: "em junho, ha 20 registros 001, 19 registros 002, 20 registros 003, 2 falhas 039 e 20 BSW 040". Leitura fraca: "3.876 linhas importadas".

## 5. Validacao XML

Use para conferir se os XMLs oficiais estao presentes, legiveis, vinculados e coerentes.

Campos relevantes:

- **Data inferida**: dia de producao identificado no nome ou conteudo.
- **Tipo documental**: XML fiscal, falha/BSW, parametros CV ou seguranca CV.
- **Familia**: 001, 002, 003, 039, 040 ou outra familia reconhecida.
- **Tag**: ponto de medicao ou instrumento relacionado.
- **Status**: OK, atencao ou critico.
- **Duplicado**: alerta de revisao antes da ingestao pesada.

Acoes esperadas:

- Abrir comparacao quando houver XML e dado fiscal/MPFM no mesmo periodo.
- Abrir Limites & CV quando o XML indicar parametros, seguranca ou configuracao.
- Reindexar fontes quando o arquivo esperado nao aparece.

## 6. Dados Medidos

Esta e a area de apuracao diaria. Use para consolidar o que foi medido por fonte.

Campos esperados:

- **Data de medicao**: dia operacional.
- **Fonte**: Fiscal/Radar, ANP, MPFM diario ou checklist.
- **Familia/tag**: ponto de medicao e familia do registro.
- **Metricas fiscais**: raw, XML e ANP quando disponiveis.
- **Metricas ANP**: volume corrigido, bruto, liquido e BSW quando aplicavel.
- **Metricas MPFM**: valor, unidade e indicador de hidrocarboneto quando aplicavel.
- **Status**: OK, atencao, divergente ou pendente.

O fechamento deve buscar consistencia entre data, tag, fonte e familia. Divergencia sem evidencia deve virar pendencia ou proposta.

## 7. Checklist Diario

O checklist pode continuar sendo importado, mas a aplicacao deve substituir gradualmente o preenchimento manual quando os dados ja existirem em XML, MPFM, laboratorio ou exports.

Abas principais:

- **Occurrences**: ocorrencias operacionais. Pular quando ja houver modulo proprio de ocorrencias.
- **Lab-Report/API**: qualidade, API, densidade, BSW e analises fisico-quimicas.
- **Tank**: estoque, movimentacao, tanque, agua/oleo e volumes associados.
- **Off Spec Tank**: volumes e eventos fora de especificacao.
- **MPFM Subsea x Fiscal - Oleo**: comparacao de medicao multifasica com fiscal/topside/separador.
- **Balanco de Gas**: gas produzido, gas lift, separacao, reconciliacao e pendencias.

Para cada aba, preservar:

- Data operacional.
- Tag, ponto, poco ou sistema.
- Valor numerico e unidade.
- Status de validacao.
- Evidencia ou arquivo de origem.
- Observacao tecnica quando houver exclusao, correcao ou ajuste.

## 8. Limites, PAM e CV

Esta area deve responder a duas perguntas:

- O ponto operou dentro da faixa calibrada e da PAM?
- O flow computer/CV mudou parametros entre um dia e outro?

Campos de parametrizacao:

- **Tag**: instrumento ou ponto de medicao.
- **Metrica**: pressao, temperatura, vazao, densidade, BSW, GVF, WLR ou outra variavel controlada.
- **Faixa calibrada**: minimo e maximo validos por certificado/calibracao.
- **PAM**: limite operacional/regulatorio aplicado ao ponto.
- **Validade**: inicio e fim da faixa.
- **Evidencia**: certificado, folha de dados, PAM, PDF ou configuracao aprovada.
- **Status de aprovacao**: rascunho, aprovado, revisao ou inativo.

Mudancas de CV devem ser comparadas por data, computador, parametro e valor. Alteracao sem evidencia deve gerar proposta ou pendencia.

## 9. Comparacao, calendario, propostas e dossies

- **Comparacao**: use para fiscal x ANP x MPFM no mesmo periodo/tag/familia.
- **Calendario**: use para acompanhar dias sem carga, dias parciais e pendencias.
- **Propostas**: use para transformar achados em decisao rastreavel antes de alterar cadastro.
- **Dossies**: use para ver historico do ponto de medicao, evidencias, limites, falhas, checklist e comparacoes.

## 10. Criterio de exibicao no topo

Uma informacao deve aparecer no topo se responder pelo menos uma destas perguntas:

- O fechamento do dia ou mes esta completo?
- Existe XML oficial esperado faltando?
- Existe divergencia entre fiscal, ANP, MPFM ou checklist?
- Algum limite, PAM ou CV coloca a medicao em risco?
- Existe pendencia que bloqueia ou condiciona o fechamento?

Se a informacao responde apenas "quantos arquivos existem no disco", ela pertence ao inventario tecnico.
