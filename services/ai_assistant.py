"""
services/ai_assistant.py
─────────────────────────────────────────────────────────────────────────────
Assistente IA multi-provider para o MPFM App.

Providers suportados
--------------------
- "azure"     → Microsoft Foundry (azure-ai-inference)
- "openai"    → OpenAI direto       (openai)
- "anthropic" → Anthropic Claude    (anthropic)
- "gemini"    → Google Gemini       (google-generativeai)

Uso
---
from services.ai_assistant import ask_ai

# Usa o provider padrão definido em AI_DEFAULT_PROVIDER (.env)
resp = await ask_ai("Por que a vazão de gás está elevada neste MPFM?")
print(resp.content)

# Força um provider específico
resp = await ask_ai("Analise estes dados", provider="openai")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal, Optional

logger = logging.getLogger(__name__)

Provider = Literal["azure", "openai", "anthropic", "gemini"]

SYSTEM_MPFM = (
    "Você é um especialista em sistemas MPFM (medidores multifásicos) para produção "
    "de petróleo e gás offshore. Responda em português, com linguagem técnica, clara, "
    "humana e orientada à operação."
)

RESPONSE_FORMAT_INSTRUCTIONS = """
=== Formato esperado da resposta ao usuário ===
Use Markdown limpo e estruturado. Organize respostas longas com títulos e subtítulos hierárquicos (`##`, `###`) para que a interface gere índice automaticamente. Prefira parágrafos curtos, bem separados e escritos em tom natural, sem parecer robótico. Quando houver dados comparáveis, use tabelas Markdown. Quando houver sequência operacional, use listas numeradas. Quando houver alertas, riscos ou pendências, crie uma seção própria. Use negrito apenas para termos, valores e conclusões importantes. Não use HTML bruto.
""".strip()


@dataclass
class AIResponse:
    content: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    extra: dict = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Provider helpers
# ─────────────────────────────────────────────────────────────────────────────

def _call_azure(user: str, system: str, model: str, max_tokens: int, temperature: float,
                history: list[dict] | None = None, attachments: list[dict] | None = None) -> AIResponse:
    from openai import AzureOpenAI
    from app_config import AZURE_AI_API_KEY, AZURE_AI_MODEL, AZURE_AI_PROJECT_ENDPOINT

    key = AZURE_AI_API_KEY
    endpoint = AZURE_AI_PROJECT_ENDPOINT
    if not endpoint or not key:
        raise RuntimeError("Azure Foundry: preencha AZURE_AI_PROJECT_ENDPOINT e AZURE_AI_API_KEY no .env")

    base_url = endpoint.split("/api/projects")[0] if "/api/projects" in endpoint else endpoint
    client = AzureOpenAI(api_key=key, api_version="2024-12-01-preview", azure_endpoint=base_url)
    target = model or AZURE_AI_MODEL
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    for h in (history or []):
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": user})

    resp = client.chat.completions.create(
        model=target, messages=messages, max_tokens=max_tokens, temperature=temperature,
    )
    usage = resp.usage
    return AIResponse(
        content=resp.choices[0].message.content or "",
        provider="azure", model=resp.model or target,
        input_tokens=usage.prompt_tokens if usage else 0,
        output_tokens=usage.completion_tokens if usage else 0,
    )


def _call_openai(user: str, system: str, model: str, max_tokens: int, temperature: float,
                 history: list[dict] | None = None, attachments: list[dict] | None = None) -> AIResponse:
    from openai import OpenAI
    from app_config import OPENAI_API_KEY, OPENAI_MODEL

    key = OPENAI_API_KEY
    if not key:
        raise RuntimeError("OpenAI: preencha OPENAI_API_KEY no .env")

    client = OpenAI(api_key=key)
    target = model or OPENAI_MODEL
    messages = [{"role": "system", "content": system}]
    for h in (history or []):
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": user})

    resp = client.chat.completions.create(
        model=target, messages=messages, max_tokens=max_tokens, temperature=temperature,
    )
    usage = resp.usage
    return AIResponse(
        content=resp.choices[0].message.content or "",
        provider="openai", model=resp.model or target,
        input_tokens=usage.prompt_tokens if usage else 0,
        output_tokens=usage.completion_tokens if usage else 0,
    )


def _call_anthropic(user: str, system: str, model: str, max_tokens: int, temperature: float,
                    history: list[dict] | None = None, attachments: list[dict] | None = None) -> AIResponse:
    import anthropic
    from app_config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

    key = ANTHROPIC_API_KEY
    if not key:
        raise RuntimeError("Anthropic: preencha ANTHROPIC_API_KEY no .env")

    client = anthropic.Anthropic(api_key=key)
    target = model or ANTHROPIC_MODEL
    messages = []
    for h in (history or []):
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": user})

    resp = client.messages.create(
        model=target, max_tokens=max_tokens, temperature=temperature,
        system=system, messages=messages,
    )
    return AIResponse(
        content=resp.content[0].text if resp.content else "",
        provider="anthropic", model=resp.model or target,
        input_tokens=resp.usage.input_tokens,
        output_tokens=resp.usage.output_tokens,
    )


def _call_gemini(user: str, system: str, model: str, max_tokens: int, temperature: float,
                 history: list[dict] | None = None, attachments: list[dict] | None = None) -> AIResponse:
    from google import genai
    from google.genai import errors
    from google.genai import types
    from app_config import GEMINI_API_KEY, GEMINI_MODEL

    key = GEMINI_API_KEY
    if not key:
        raise RuntimeError("Gemini: preencha GEMINI_API_KEY no .env")

    client = genai.Client(api_key=key)
    target = model or GEMINI_MODEL

    # Constrói histórico no formato Gemini
    contents = []
    for h in (history or []):
        role = "user" if h["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=h["content"])]))
    user_parts = [types.Part(text=user)]
    for item in (attachments or []):
        text = item.get("text")
        if text:
            label = item.get("name") or "anexo"
            user_parts.append(types.Part(text=f"\n\n=== Conteúdo extraído de {label} ===\n{text}"))
            continue
        data = item.get("data")
        mime_type = item.get("mime_type") or "application/octet-stream"
        if data:
            user_parts.append(types.Part.from_bytes(data=data, mime_type=mime_type))
    contents.append(types.Content(role="user", parts=user_parts))

    def _generate(target_model: str):
        return client.models.generate_content(
            model=target_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )

    try:
        resp = _generate(target)
    except (errors.ServerError, errors.ClientError) as exc:
        fallback = "gemini-2.5-flash"
        status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
        if (status_code in {400, 404, 503, 504} or any(str(code) in str(exc) for code in (400, 404, 503, 504))) and target != fallback:
            logger.warning("Gemini model %s unavailable; retrying with %s", target, fallback)
            try:
                resp = _generate(fallback)
                target = fallback
            except (errors.ServerError, errors.ClientError) as retry_exc:
                raise RuntimeError(f"Gemini indisponível no momento: {retry_exc}") from retry_exc
        else:
            raise RuntimeError(f"Gemini indisponível no momento: {exc}") from exc
    usage = resp.usage_metadata
    return AIResponse(
        content=resp.text or "",
        provider="gemini", model=target,
        input_tokens=int((getattr(usage, "prompt_token_count", 0) if usage else 0) or 0),
        output_tokens=int((getattr(usage, "candidates_token_count", 0) if usage else 0) or 0),
    )


_DISPATCH = {
    "azure": _call_azure,
    "openai": _call_openai,
    "anthropic": _call_anthropic,
    "gemini": _call_gemini,
}


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def ask_ai(
    user: str,
    system: str = SYSTEM_MPFM,
    provider: Optional[Provider] = None,
    model: Optional[str] = None,
    max_tokens: int = 1024,
    temperature: float = 0.3,
    history: list[dict] | None = None,
    attachments: list[dict] | None = None,
) -> AIResponse:
    """Envia uma pergunta ao provider configurado e retorna AIResponse.

    Parameters
    ----------
    user      : Pergunta ou texto do usuário.
    system    : Instrução de papel (system prompt).
    provider  : "azure" | "openai" | "anthropic" | "gemini".
    model     : Override do modelo.
    max_tokens: Limite de tokens na resposta.
    temperature: 0 = determinístico, 1 = criativo.
    history   : Lista de turnos anteriores [{role, content}, ...].
    """
    import asyncio
    from app_config import AI_DEFAULT_PROVIDER

    target_provider: Provider = provider or AI_DEFAULT_PROVIDER  # type: ignore[assignment]
    fn = _DISPATCH.get(target_provider)
    if fn is None:
        raise ValueError(f"Provider desconhecido: '{target_provider}'. Use: {list(_DISPATCH)}")

    logger.debug("ask_ai → provider=%s | model=%s | history=%d | user=%.80s",
                 target_provider, model, len(history or []), user)

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, lambda: fn(user, system, model or "", max_tokens, temperature, history or [], attachments or [])
    )


def ask_ai_sync(
    user: str,
    system: str = SYSTEM_MPFM,
    provider: Optional[Provider] = None,
    model: Optional[str] = None,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> AIResponse:
    """Versão síncrona (para scripts e notebooks)."""
    import asyncio
    from app_config import AI_DEFAULT_PROVIDER

    target_provider: Provider = provider or AI_DEFAULT_PROVIDER  # type: ignore[assignment]
    fn = _DISPATCH.get(target_provider)
    if fn is None:
        raise ValueError(f"Provider desconhecido: '{target_provider}'")
    return fn(user, system, model or "", max_tokens, temperature)


def providers_status() -> dict[str, bool]:
    """Retorna quais providers estão configurados (chave presente)."""
    from app_config import GEMINI_API_KEY

    def _key_ok(v: str) -> bool:
        return bool(v and "COLE_" not in v)

    return {
        "gemini": _key_ok(GEMINI_API_KEY),
    }


def is_configured() -> bool:
    """True se pelo menos um provider está pronto."""
    return any(providers_status().values())

