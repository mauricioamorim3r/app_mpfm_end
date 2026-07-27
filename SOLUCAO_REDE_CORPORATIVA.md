# SOLUÇÃO - DeepSeek e Kimi em Rede Corporativa Equinor

## 🔴 PROBLEMA DETECTADO

Sua rede corporativa Equinor está bloqueando acesso às APIs:
- ❌ `api.deepseek.com` - BLOQUEADO
- ❌ `api.moonshot.cn` - BLOQUEADO

Erro: `SEC_E_ILLEGAL_MESSAGE` (SSL/TLS handshake failed)

---

## ✅ SOLUÇÕES

### OPÇÃO 1: Configure Proxy Corporativo (Mais Comum)

Adicione ao `.env`:

```env
# Proxy Equinor (substitua pelos valores reais)
HTTP_PROXY=http://proxy.equinor.com:8080
HTTPS_PROXY=http://proxy.equinor.com:8080
NO_PROXY=localhost,127.0.0.1
```

**Como descobrir o proxy:**
1. Windows: `netsh winhttp show proxy`
2. Edge/Chrome: Configurações → Rede → Configurações de Proxy
3. Pergunte ao IT: suporte.ti@equinor.com

Depois teste: `python test_llm_quick.py`

---

### OPÇÃO 2: Use Fora da Rede Corporativa

**Teste em casa ou com hotspot 4G:**

```bash
# Conecte-se a outra rede (WiFi casa ou 4G do celular)
python test_llm_quick.py
```

Se funcionar → problema é o firewall Equinor

---

### OPÇÃO 3: Use VPN Reversa

Se você tem VPN pessoal ou servidor:

```bash
# Via SSH tunnel (se tiver servidor)
ssh -D 8080 seu_servidor.com

# Configure SOCKS proxy no .env
ALL_PROXY=socks5://127.0.0.1:8080
```

---

### OPÇÃO 4: Solicite Liberação ao IT

**Email para IT Equinor:**

```
Assunto: Liberação de acesso APIs - DeepSeek e Moonshot AI

Olá,

Preciso acessar as seguintes APIs para desenvolvimento:

1. api.deepseek.com (porta 443) - API de IA para análise de código
2. api.moonshot.cn (porta 443) - API de IA multilíngue

Erro atual: SEC_E_ILLEGAL_MESSAGE (TLS handshake)

Pode liberar esses domínios no firewall/proxy?

Obrigado!
```

---

### OPÇÃO 5: Use Modelos Locais (Alternativa)

Se não conseguir liberar, use **Ollama** (modelos locais):

```bash
# Instale Ollama
winget install Ollama.Ollama

# Baixe modelo similar ao DeepSeek
ollama pull deepseek-coder

# Use no Python
pip install ollama
python -c "import ollama; print(ollama.chat('deepseek-coder', 'Hello'))"
```

---

## 🔍 DIAGNÓSTICO DETALHADO

Execute para mais detalhes:

```bash
# Teste conectividade
curl -v https://api.deepseek.com/v1 2>&1 | findstr /i "connect proxy ssl"

# Veja configuração de proxy do Windows
netsh winhttp show proxy

# Teste com proxy manual
set HTTPS_PROXY=http://seu_proxy:porta
python test_llm_quick.py
```

---

## 📞 PRÓXIMOS PASSOS

1. **Teste em outra rede** (4G/casa) para confirmar que é o firewall
2. **Configure proxy** se souber qual é
3. **Solicite liberação** ao IT se for uso autorizado
4. **Use Ollama** como alternativa local

**Qual opção prefere tentar primeiro?**
