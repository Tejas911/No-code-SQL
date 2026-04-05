import os
import httpx
from core.config_loader import load_config
from core.logger import get_logger

log = get_logger("llm")

_GROQ_EXCLUDE = {"whisper", "tts", "guard", "safeguard", "orpheus", "allam"}

# Static Gemini models (Google doesn't have a public list endpoint)
GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]

_cached_groq_models: list[str] = []


def fetch_groq_models(api_key: str) -> list[str]:
    global _cached_groq_models
    if _cached_groq_models:
        return _cached_groq_models
    try:
        r = httpx.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        all_models = [m["id"] for m in r.json().get("data", [])]
        _cached_groq_models = sorted([
            m for m in all_models
            if not any(ex in m.lower() for ex in _GROQ_EXCLUDE)
        ])
        log.info("Fetched %d Groq models", len(_cached_groq_models))
    except Exception as e:
        log.warning("Could not fetch Groq models: %s — using defaults", e)
        _cached_groq_models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    return _cached_groq_models


def get_all_models(groq_api_key: str) -> dict[str, list[str]]:
    """Returns {provider: [model_ids]} for the sidebar grouped selectbox."""
    return {
        "groq": fetch_groq_models(groq_api_key),
        "google": GEMINI_MODELS,
    }


def get_llm(overrides: dict = None):
    cfg = load_config()["llm"]
    ov = overrides or {}

    model       = ov.get("model",       cfg["model"])
    temperature = ov.get("temperature", cfg["temperature"])
    max_tokens  = ov.get("max_tokens",  cfg["max_tokens"])
    top_p       = ov.get("top_p",       cfg.get("top_p", 1.0))
    provider    = ov.get("provider",    cfg.get("provider", "groq"))

    log.info("LLM → provider=%s model=%s temp=%.2f max_tokens=%d",
             provider, model, temperature, max_tokens)

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            max_output_tokens=max_tokens,
            top_p=top_p,
            google_api_key=os.environ["GOOGLE_API_KEY"],
        )
    else:  # groq (default)
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            groq_api_key=os.environ["GROQ_API_KEY"],
            model_kwargs={"top_p": top_p},
            request_timeout=cfg.get("request_timeout", 30),
        )
