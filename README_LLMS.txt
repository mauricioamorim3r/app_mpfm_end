╔═══════════════════════════════════════════════════════════════╗
║           GUIA RAPIDO - DeepSeek e Kimi K3                   ║
╚═══════════════════════════════════════════════════════════════╝

[1] EDITE O ARQUIVO .env
    - Abra .env no seu editor
    - Localize estas linhas:
        DEEPSEEK_API_KEY=COLE_SUA_CHAVE_DEEPSEEK_AQUI
        KIMI_API_KEY=COLE_SUA_CHAVE_KIMI_AQUI
    - Substitua pelos valores reais

[2] TESTE AS APIs
    python test_llm_quick.py

[3] TESTE INDIVIDUAL
    python test_llm_quick.py deepseek
    python test_llm_quick.py kimi

[4] OBTER API KEYS

    DeepSeek:
    - Site: https://platform.deepseek.com
    - Login/Registro
    - API Keys -> Create New Key

    Kimi (Moonshot AI):
    - Site: https://platform.moonshot.cn
    - Login/Registro (requer numero chines ou WeChat)
    - API Keys -> Nova Chave

[5] EXEMPLO DE USO EM PYTHON

from openai import OpenAI
import os

# DeepSeek
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "Ola!"}]
)
print(response.choices[0].message.content)

# Kimi K3
client = OpenAI(
    api_key=os.getenv("KIMI_API_KEY"),
    base_url="https://api.moonshot.cn/v1"
)
response = client.chat.completions.create(
    model="moonshot-v1-8k",
    messages=[{"role": "user", "content": "你好!"}]
)
print(response.choices[0].message.content)

[6] SOLUCAO DE PROBLEMAS

Erro 401 Unauthorized:
  -> Verifique se a API key esta correta no .env
  -> Confirme que copiou a key completa

Erro de conexao:
  -> Verifique sua internet
  -> Teste: ping platform.deepseek.com

Rate limit:
  -> Aguarde alguns segundos entre requisicoes
  -> Verifique limites na dashboard da API

[7] DOCUMENTACAO

DeepSeek: https://platform.deepseek.com/docs
Kimi:     https://platform.moonshot.cn/docs/intro

