# Radar ANP - Fluxo de informação, tratamento e rastreabilidade

Este documento descreve como a informação deve fluir do dado bruto até o alerta auditável.

## 1. Princípio de rastreabilidade

Cada valor exibido no dashboard deve responder a cinco perguntas:

1. Qual é o valor?
2. De onde veio?
3. Quando foi gerado/coletado?
4. Qual regra transformou ou comparou esse valor?
5. Qual evidência comprova a conclusão?

Nenhum alerta crítico deve depender apenas de interpretação por IA. A IA pode explicar, correlacionar e sugerir ação, mas a conclusão de conformidade deve vir de regra objetiva.

## 2. Camadas do dado

| Camada | Descrição | Exemplo |
|---|---|---|
| Bronze | Arquivo original sem alteração | TXT CV, XML, ZIP, PDF, XLSX |
| Silver | Extração estruturada | tabela de medições por tag/data |
| Gold | Indicadores e regras | XML x ANP OK, certificado vencido, evento sem laudo |
| Evidência | Ponte auditável para origem | caminho do arquivo, aba, linha, página, timestamp |

## 3. Fluxo raw -> XML -> ANP

1. Ler relatórios `Run_Daily` dos computadores de vazão.
2. Extrair tag, data operacional, volume bruto, volume corrigido, volume líquido, pressão, temperatura e duração.
3. Ler XML gerado/enviado: 001 óleo, 002 gás linear, 003 gás diferencial, 004 alarmes/eventos.
4. Normalizar unidade, especialmente gás em `10³ m³` quando aplicável.
5. Ler exportações do Painel ANP.
6. Comparar por chave `data + família XML + tag`.
7. Gerar status:
   - OK: raw, XML e ANP batem dentro da tolerância.
   - Atenção: ANP bate com XML, mas raw direto não foi localizado ou precisa fonte alternativa.
   - Crítico: XML não bate com ANP ou envio esperado não existe.

## 4. Fluxo alarmes/eventos -> evidência técnica

Quando um evento indicar alteração de parâmetro, o radar deve criar uma obrigação de evidência.

| Evento detectado | Evidência esperada | Divergência |
|---|---|---|
| alteração de densidade | boletim/lab report com densidade e data compatível | evento sem laudo |
| alteração de cromatografia | laudo cromatográfico, composição completa e versão | cromatografia alterada sem análise |
| alteração de PVT | relatório PVT, versão, banco/poço/ponto e validade | PVT atualizado sem documento |
| alteração de BSW/fator BSW | boletim BSW ou XML 040 compatível | BSW atualizado sem evidência |
| alteração de range/PAM | datasheet/PAM/revisão aprovada | faixa alterada sem documento |
| alteração de MF/KF | certificado, provação, calibração ou justificativa | fator alterado sem calibração |
| alteração de limite de alarme | procedimento, gestão de mudança ou cadastro aprovado | limite alterado sem aprovação |

A implementação v1 desse fluxo está documentada em `docs/CORRELACIONADOR_EVENTO_EVIDENCIA.md`.

## 5. Fluxo limites e faixas

1. Ler limites do cadastro e Painel ANP.
2. Ler faixa calibrada do certificado.
3. Ler PAM/datasheet do equipamento.
4. Montar envelope por variável:
   - operação/PAM;
   - faixa calibrada;
   - limite inferior/superior de alarme;
   - limite normativo/metrológico.
5. Comparar medição diária com cada envelope.
6. Classificar:
   - OK: dentro de todas as faixas aplicáveis.
   - Atenção: falta faixa/evidência para validar.
   - Crítico: valor fora de limite ou certificado vencido.

## 6. Fluxo de incerteza

1. Ler incerteza máxima permitida no cadastro/norma.
2. Ler memória/certificado de incerteza do sistema.
3. Para cada data/ponto, calcular ou carregar a incerteza operacional diária.
4. Comparar `incerteza diária <= limite permitido`.
5. Guardar componentes e versão do cálculo para auditoria.

Enquanto o cálculo diário não estiver implantado, o radar mostra o limite cadastral e sinaliza a ausência da fonte de cálculo diário.

## 7. Fluxo físico-químico

1. Ler plano de coleta para saber o que era esperado.
2. Ler resultados laboratoriais: API, densidade, BSW, cromatografia, PVT.
3. Relacionar amostra ao ponto/corrente, data operacional e fluido.
4. Comparar contra:
   - dados usados no CV/XML;
   - eventos de alteração;
   - BSW online;
   - periodicidade esperada.
5. Alertar:
   - análise vencida ou ausente;
   - evento de atualização sem laudo;
   - lab x online divergente;
   - cromatografia/PVT não compatível com período.

## 8. Estrutura do registro de auditoria

Cada regra deve gerar um registro com:

| Campo | Descrição |
|---|---|
| `rule_id` | identificador estável da regra |
| `severity` | OK, atenção ou crítico |
| `date_ref` | data operacional |
| `tag` | ponto/equipamento afetado |
| `value_observed` | valor observado |
| `value_expected` | valor esperado ou limite |
| `tolerance` | tolerância aplicada |
| `source_files` | arquivos usados |
| `evidence_refs` | aba/linha/página/evento |
| `calculation` | fórmula ou regra |
| `recommendation` | ação recomendada |
| `ai_summary` | explicação textual opcional |

## 9. Papel da IA

A IA deve:

- ler documentos nas pastas configuradas;
- extrair candidatos a dados estruturados;
- apontar evidência objetiva;
- explicar alertas;
- sugerir atualização de cadastro;
- preparar dossiês e relatórios.

A IA não deve:

- alterar cadastro sem aprovação;
- concluir conformidade sem regra objetiva;
- esconder falta de evidência;
- substituir o arquivo original.
