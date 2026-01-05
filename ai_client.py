import os
import aiohttp
import asyncio
from loguru import logger
from config import settings
from typing import Optional
from templates import COMPLIMENT_PROMPT

OPENROUTER_URL = "https://api.openrouter.ai/v1/chat/completions"  # пример, уточните у провайдера

# Fallback local model using transformers (маленькая модель)
# WARNING: Для production требуется подходящая модель/развёртывание; здесь — простой пример.
local_model = None
local_tokenizer = None

async def call_openrouter(prompt: str, model: str = None):
    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("No OPENROUTER_API_KEY")
    model = model or settings.OPENROUTER_MODEL
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 200
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(OPENROUTER_URL, json=payload, headers=headers, timeout=30) as resp:
            text = await resp.text()
            if resp.status != 200:
                logger.error("OpenRouter error {}: {}", resp.status, text)
                raise RuntimeError(f"OpenRouter error: {resp.status} {text}")
            data = await resp.json()
            # Примерная структура: data['choices'][0]['message']['content']
            try:
                return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                logger.exception("Unexpected response format from openrouter: {}", data)
                raise

def init_local_model():
    global local_model, local_tokenizer
    if local_model is not None:
        return
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
        model_name = os.getenv("FALLBACK_MODEL", "gpt2")  # note: gpt2 плохо подходит, заменить на small instruct model
        logger.info("Loading local fallback model {}", model_name)
        local_tokenizer = AutoTokenizer.from_pretrained(model_name)
        local_model = AutoModelForCausalLM.from_pretrained(model_name)
        # Optionally use pipeline for text-generation
        logger.info("Local model loaded")
    except Exception as e:
        logger.exception("Failed to init local model: {}", e)
        local_model = None
        local_tokenizer = None

def generate_with_local(prompt: str, max_new_tokens: int = 120) -> str:
    # Synchronous generation (transformers); wrap as needed
    from transformers import pipeline
    model_name = os.getenv("FALLBACK_MODEL", "gpt2")
    try:
        pipe = pipeline("text-generation", model=model_name, device=0 if torch.cuda.is_available() else -1)
    except Exception:
        # fallback naive
        pipe = pipeline("text-generation", model=model_name)
    res = pipe(prompt, max_new_tokens=max_new_tokens, do_sample=True, top_p=0.95, temperature=0.8)
    return res[0]["generated_text"][len(prompt):].strip()

async def generate_compliment(user_id: str, compliment_type: str, context_messages: list):
    prompt = COMPLIMENT_PROMPT.format(type=compliment_type, context="\n".join([f"{m['role']}: {m['content']}" for m in context_messages]) or "Нет")
    logger.debug("Final prompt: {}", prompt[:1000])
    if settings.OPENROUTER_API_KEY:
        try:
            return await call_openrouter(prompt, settings.OPENROUTER_MODEL)
        except Exception as e:
            logger.exception("OpenRouter failed, will try fallback local model: {}", e)
    # fallback
    loop = asyncio.get_event_loop()
    init_local_model()
    if local_model is None:
        # As ultimate fallback, create a simple rule-based compliment
        logger.warning("Local model unavailable — using rule-based fallback")
        return rule_based_fallback(compliment_type, context_messages)
    # run blocking generation in thread
    def sync_gen():
        return generate_with_local(prompt)
    return await loop.run_in_executor(None, sync_gen)

def rule_based_fallback(compliment_type: str, context_messages: list) -> str:
    # Very simple template-based fallback
    context_text = " ".join([m["content"] for m in context_messages])[:200]
    if compliment_type == "appearance":
        base = f"Оля, у тебя удивительная внешность — твоя улыбка делает день ярче."
    elif compliment_type == "character":
        base = f"Оля, твоё доброе и внимательное отношение к людям действительно впечатляет."
    elif compliment_type == "achievements":
        base = f"Оля, твои достижения вдохновляют — видно, сколько сил ты вкладываешь в своё дело."
    else:
        base = f"Оля, ты замечательная и вызываешь восхищение."
    if "exam" in context_text.lower() or "экзам" in context_text.lower():
        base += " Уверена, ты отлично справишься с экзаменом."
    return base
