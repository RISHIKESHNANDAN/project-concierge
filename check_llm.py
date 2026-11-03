from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

print("key starts with:", LLM_API_KEY[:6], "| length:", len(LLM_API_KEY))
print("base url:", LLM_BASE_URL)
print("model:", LLM_MODEL)

from app.generation.llm import chat_json

try:
    print("RESULT:", chat_json("Reply with JSON only.", 'Return {"ok": true}'))
except Exception as e:
    print("ERROR:", e)