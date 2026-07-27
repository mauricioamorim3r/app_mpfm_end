# Roadmap Técnico

## Fase 1
- Centralizar configuração do app.
- Introduzir schema `RAW` no SQLite.
- Remover hardcode de host/API no frontend.
- Atualizar README e documentação operacional.

## Fase 2
- Extrair backend para módulos `routes`, `services`, `repositories`.
- Criar camada de acesso a banco para consultas principais.
- Isolar exportações Excel/PDF em módulos específicos.

## Fase 3
- Dividir frontend em `app.js`, módulos por tela e CSS por domínio.
- Criar estado compartilhado menos acoplado.
- Reduzir uso de script inline.

## Fase 4
- Adicionar smoke tests e testes de regressão para parsing.
- Adicionar validações de schema de entrada e QA automatizado.
- Criar pacote de release local com setup previsível.

## Fase 5 - Radar ANP inteligente
- Consolidar o contrato operacional em `docs/RADAR_ANP_PLANO_MESTRE.md`.
- Usar `docs/RADAR_ANP_TEMPLATE_GERAL_INGESTAO.md` e `templates/Radar_ANP_Template_Geral_Ingestao.xlsx` como entrada manual/contingencia.
- Portar gradualmente regras do Radar ANP para servicos Python auditaveis.
- Evoluir IA para explicar alertas e gerar propostas aprovaveis, mantendo escrita direta bloqueada por padrao.
- Criar graficos interativos de limites, PAM, faixa calibrada, incerteza diaria e divergencias raw/XML/Painel ANP.
