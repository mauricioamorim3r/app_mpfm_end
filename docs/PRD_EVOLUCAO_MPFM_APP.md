# PRD de Evolução do MPFM App

## Objetivo
Transformar o MPFM App em uma aplicação local auditável, modular e segura para operação diária de ingestão, reconciliação, QA e exportação.

## Problema atual
- Backend e frontend concentrados em poucos arquivos grandes.
- Regras operacionais importantes ainda estão implícitas no código.
- O banco local já suporta operação, mas precisa separar melhor rastros `RAW` e dados `CURATED`.
- A documentação não acompanha totalmente a aplicação atual.

## Escopo desta fase
- Centralizar configuração do app.
- Formalizar schema SQLite com base para `RAW` e `CURATED`.
- Registrar eventos de parsing/ingestão para rastreabilidade.
- Reduzir acoplamento do frontend com `localhost` hardcoded.
- Criar memória operacional e roadmap técnico.

## Fora de escopo desta fase
- Reescrever o parser MPFM.
- Migrar frontend para framework.
- Reestruturar todas as rotas em múltiplos módulos de uma vez.

## Requisitos funcionais
- O app deve continuar rodando localmente sem internet.
- A porta deve poder ser configurada por variável de ambiente.
- O frontend deve descobrir a API pelo host atual.
- O banco deve registrar arquivos recebidos e eventos de parsing.
- O sistema deve continuar preservando medições curadas e reconciliação existente.

## Requisitos não funcionais
- Mudanças devem manter compatibilidade com banco local antigo.
- Refatorações devem priorizar baixo risco operacional.
- O projeto deve ficar pronto para novas divisões de módulos.

## Critérios de aceite
- Aplicação sobe localmente com a estrutura atual.
- `server.py` passa a depender de configuração central.
- Novas tabelas `RAW` existem no SQLite sem quebrar dados anteriores.
- Frontend deixa de depender de URL fixa `http://localhost:8765/api`.
- README e memória do projeto refletem a aplicação real.
