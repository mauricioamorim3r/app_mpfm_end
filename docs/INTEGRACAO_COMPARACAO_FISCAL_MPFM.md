# Integração Comparação Fiscal x MPFM - Status

**Data:** 2026-07-09  
**Objetivo:** Exibir tabela de comparação fiscal x MPFM no Painel Operador

---

## ✅ Implementações Realizadas

### 1. Backend - Integração com Checklist Diário

**Arquivo:** `routes/painel_operador_routes.py` (linhas 835-859)

```python
# Buscar dados da tabela painel_operador_mpfm_fiscal_oil
comparacao_raw = service.mpfm_fiscal_oil(
    db_conn,
    date_from=date_from,
    date_to=date_to[:10],
    limit=500
)

# Mapear para formato frontend
for item in comparacao_raw.get("items", []):
    fiscal = float(item.get("fiscal_oil_m3") or 0)
    mpfm = float(item.get("total_mpfm_oil_m3") or 0)
    delta_pct = float(item.get("variance_percent") or 0)
    
    comparacoes_mes.append({
        "data": item.get("production_date", ""),
        "tag": "Total FPSO",
        "familia": "a001",
        "fiscal": round(fiscal, 2),
        "mpfm": round(mpfm, 2),
        "delta_pct": round(delta_pct, 2),
        "delta_m3": round(mpfm - fiscal, 2),
        "status": item.get("status", ""),
        "comment": item.get("comment", ""),
    })
```

**Fonte de dados:**
- Tabela: `painel_operador_mpfm_fiscal_oil`
- Origem: Checklist diário Excel, aba "MPFM Subsea x Fiscal- Óleo"
- Campos: `production_date`, `fiscal_oil_m3`, `total_mpfm_oil_m3`, `variance_percent`, `status`

### 2. Frontend - Tabela Simplificada

**Arquivo:** `static/app.painel_operador.js` (linhas 380-440)

**Mudanças:**
- Removidas colunas "Tag" e "Família" (dados agregados diários)
- Adicionada coluna "Delta (m³)" para volume absoluto
- Totais calculados no rodapé
- Destaque visual:
  - Delta >5%: vermelho
  - Delta >2%: amarelo
  - Delta ≤2%: normal

**Layout final:**
```
| Data       | Fiscal (m³) | MPFM (m³) | Delta (m³) | Delta (%) |
|------------|-------------|-----------|------------|-----------|
| 2026-06-01 | 1.234,56    | 1.256,78  | 22,22      | 1,80%     |
| ...        | ...         | ...       | ...        | ...       |
| TOTAL      | 35.678,90   | 36.012,34 | 333,44     | 0,93%     |
```

---

## ⚠️ Pendências

### 1. Importar Checklist com Aba "MPFM Subsea x Fiscal- Óleo"

**Problema:**
- Tabela `painel_operador_mpfm_fiscal_oil` está vazia
- Checklists anteriores foram importados de caminho diferente
- Nenhum checklist com aba de comparação disponível no workspace atual

**Solução:**
1. Obter arquivo `.xlsm` do checklist diário mais recente
2. Verificar que contém aba **"MPFM Subsea x Fiscal- Óleo"**
3. Copiar para pasta `Painel_Operador/`
4. Na interface web:
   - Ir para aba "Checklist Diário"
   - Clicar em "Inspecionar" para verificar abas detectadas
   - Clicar em "Atualizar painel" para importar
5. Confirmar importação bem-sucedida:
   ```
   Módulo carregado e pronto para consulta
   Linhas checklist: [número] (deve aumentar)
   Abas importadas: [número] (deve incluir "MPFM Subsea x Fiscal- Óleo")
   ```

### 2. Verificar Estrutura da Aba no Excel

**Formato esperado:**
- Coluna "Data" ou "production_date": datas de produção
- Coluna "Fiscal" ou "fiscal_oil_m3": volume fiscal em m³
- Coluna "MPFM Total" ou "total_mpfm_oil_m3": volume MPFM em m³
- Coluna "Variação %" ou "variance_percent": percentual de diferença
- Opcional: "Status", "Comentário"

Se estrutura for diferente, ajustar parser em:
`services/painel_operador/daily_checklist_service.py` método `_parse_mpfm_fiscal_oil_sheet()`

---

## 📊 Estado Atual do Dashboard

**Componentes funcionando:**
- ✅ Alertas: 4 alertas exibidos (dados faltantes + comparação vazia)
- ✅ NFSMs Abertas: 39 notificações listadas com badges de criticidade
- ✅ Balanço de Tanques: dados disponíveis (30 registros)
- ❌ **Comparação Fiscal x MPFM**: tabela vazia aguardando dados
- ❌ Gráfico de Produção: sem dados para plotar (depende da comparação)
- ❌ Balanço de Gás: sem dados (aba não processada)

**APIs disponíveis:**
- `GET /api/painel-operador/dashboard-principal?month=YYYY-MM`
- `GET /api/painel-operador/nfsm-abertas-excel`
- `GET /api/painel-operador/mpfm-fiscal-oil?date_from=...&date_to=...`

---

## 🔄 Próximos Passos Recomendados

### Curto Prazo (Urgente)
1. [ ] Localizar checklist `.xlsm` com aba "MPFM Subsea x Fiscal- Óleo"
2. [ ] Importar checklist no sistema
3. [ ] Validar dados aparecem na tabela de comparação
4. [ ] Testar gráfico de produção populando automaticamente

### Médio Prazo (Melhorias)
1. [ ] Implementar controles interativos do gráfico (checkboxes de variáveis)
2. [ ] Adicionar overlays de limites (faixa calibrada, PAM)
3. [ ] Popular balanço de gás (precisa checklist com aba "Balanço de Gás")
4. [ ] Implementar filtros de data/tag na tabela de comparação

### Longo Prazo (Evolução)
1. [ ] Comparação por tag individual (desagregar "Total FPSO")
2. [ ] Drill-down para detalhes diários
3. [ ] Exportação Excel da comparação
4. [ ] Alertas automáticos para desvios >5%

---

## 📝 Notas Técnicas

**Agregação de dados:**
- Sistema retorna totais diários agregados (PE4 + PE2 Banks 10/15)
- Não há breakdown por tag individual no checklist
- Se necessário comparação por tag, precisa outra fonte de dados

**Performance:**
- Query limitada a 500 registros (ajustável)
- Filtros: data inicial/final, status, busca textual
- Índices criados em: `(import_run_id, production_date, status)`

**Validação de dados:**
- Status calculado automaticamente baseado em variance_percent
- Comentários vindos do checklist Excel preservados
- Datas filtradas para mês vigente por padrão

---

## 🐛 Problemas Conhecidos

1. **Latest run filter**: Query busca apenas última importação
   - Se última importação não tem aba MPFM, retorna vazio
   - Solução: modificar query para buscar todos os runs (ou usar `UNION`)

2. **Path mismatch**: Sistema espera arquivos em path diferente
   - Antigo: `C:\Users\mauri\OneDrive\Documentos\Painel_Operador\...`
   - Atual: `C:\Users\MAUAM\OneDrive - Equinor\Desktop\NOVO\Painel_Operador\`
   - Arquivos antigos não acessíveis

3. **Gas balance vazio**: Aba "Balanço de Gás" não processada
   - Checklist importado não tinha essa aba
   - OU parser não reconheceu formato da aba

---

**Autor:** GitHub Copilot  
**Revisão:** Aguardando validação com checklist importado
