# Execução sugerida

1. Copiar este pacote para a raiz do projeto no VSCode.
2. Copiar o template Excel para a pasta `templates/`.
3. Baixar os Excel recentes do Google Drive para `data/raw_drive/` ou configurar o conector Drive da aplicação.
4. Implementar os conectores em `etl/sources/` conforme a base real.
5. Executar:

```bash
python -m etl.ranp44_pe4 --well PE_4 --days 180 --end-date 2026-07-08
```

6. Conferir:
- workbook preenchido;
- log de validação;
- aba `14_Checklist_RANP44`;
- aba `15_Fontes_Evidencias`;
- divergências e bloqueios.

7. Somente gerar Word/PDF final quando o checklist estiver sem bloqueios críticos.
