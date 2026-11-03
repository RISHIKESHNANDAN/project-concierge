import json
import re
import time

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, MAX_OUTPUT_TOKENS

STATS = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "seconds": 0.0}
_client = None


class LLMError(Exception):
    pass


def _get():
    global _client
    if _client is None:
        from openai import OpenAI
        # max_retries=0: we handle retries ourselves below so we control the waiting
        _client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=30, max_retries=0)
    return _client


def chat_json(system: str, user: str, model: str | None = None) -> dict:
    t = time.time()
    r = None
    for attempt in range(3):
        try:
            r = _get().chat.completions.create(
                model=model or LLM_MODEL, temperature=0, max_tokens=MAX_OUTPUT_TOKENS,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            )
            break
        except Exception as e:
            msg = str(e)
            rate_limited = "429" in msg or "rate" in msg.lower()
            if rate_limited and attempt < 2:
                time.sleep(5 * (attempt + 1))  # wait 5s, then 10s
                continue
            raise LLMError(f"API call failed: {msg[:250]}") from e

    STATS["calls"] += 1
    STATS["seconds"] += time.time() - t
    if r is not None and r.usage:
        STATS["prompt_tokens"] += r.usage.prompt_tokens
        STATS["completion_tokens"] += r.usage.completion_tokens

    if r is None:
        raise LLMError("API call returned no response")

    choice = r.choices[0]
    content = choice.message.content or ""

    if choice.finish_reason == "length":
        # reasoning models can spend the whole budget thinking and never finish the JSON
        raise LLMError(f"output cut off at max_tokens={MAX_OUTPUT_TOKENS}; raise MAX_OUTPUT_TOKENS")

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", content, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    raise LLMError(f"model did not return valid JSON: {content[:150]!r}")