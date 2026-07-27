# Guia: DeepSeek e Kimi K3 - Instalação e Uso

## 🚀 Instalação Rápida

### 1. Configure as API Keys
```bash
python setup_llms.py
```

Cole suas chaves quando solicitado:
- **DeepSeek API Key**: Sua chave da DeepSeek
- **Kimi K3 API Key**: Sua chave do Moonshot AI

### 2. Teste as APIs
```bash
python test_llms.py
```

## 📝 Configuração Manual (Alternativa)

Adicione ao arquivo `.env`:

```env
# DeepSeek
DEEPSEEK_API_KEY=sua_chave_deepseek
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# Kimi K3 (Moonshot AI)
KIMI_API_KEY=sua_chave_kimi
KIMI_MODEL=moonshot-v1-8k
KIMI_BASE_URL=https://api.moonshot.cn/v1
```

## 💻 Exemplos de Uso

### DeepSeek
```python
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "Você é um assistente especializado."},
        {"role": "user", "content": "Explique computação quântica em 50 palavras."}
    ],
    temperature=0.7,
    max_tokens=100
)

print(response.choices[0].message.content)
```

### Kimi K3
```python
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("KIMI_API_KEY"),
    base_url="https://api.moonshot.cn/v1"
)

response = client.chat.completions.create(
    model="moonshot-v1-8k",
    messages=[
        {"role": "system", "content": "你是一个专业的AI助手。"},
        {"role": "user", "content": "用中文解释人工智能。"}
    ],
    temperature=0.7,
    max_tokens=200
)

print(response.choices[0].message.content)
```

## 🔧 Modelos Disponíveis

### DeepSeek
- `deepseek-chat` - Modelo principal de chat
- `deepseek-coder` - Especializado em código

### Kimi K3 (Moonshot)
- `moonshot-v1-8k` - 8K contexto
- `moonshot-v1-32k` - 32K contexto
- `moonshot-v1-128k` - 128K contexto

## 🌐 URLs Base

- **DeepSeek**: `https://api.deepseek.com/v1`
- **Kimi/Moonshot**: `https://api.moonshot.cn/v1`

## 📚 Documentação Oficial

- DeepSeek: https://platform.deepseek.com/docs
- Kimi: https://platform.moonshot.cn/docs

## ❓ Solução de Problemas

### Erro de autenticação
- Verifique se a API key está correta no `.env`
- Verifique se a key não expirou

### Timeout ou conexão recusada
- Verifique sua conexão com internet
- Teste com `curl` se necessário:
  ```bash
  curl https://api.deepseek.com/v1/chat/completions \
    -H "Authorization: Bearer SUA_KEY"
  ```

### Rate limit
- DeepSeek e Kimi têm limites de requisições
- Aguarde alguns segundos entre chamadas
