import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # keeps pure-logic unit tests runnable without extras
    pass

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "data" / "documents"
EVAL_FILE = ROOT / "data" / "evaluation" / "eval_set.jsonl"
REPORTS_DIR = ROOT / "reports"
CHROMA_DIR = ROOT / "chroma_db"
COLLECTION = "shopease_kb"

EMBED_MODEL = "all-MiniLM-L6-v2"
MAX_CHUNK_CHARS = 900
TOP_K = int(os.getenv("TOP_K", "4"))
RETRIEVAL_MODE = os.getenv("RETRIEVAL_MODE", "dense")
ABSTAIN_DISTANCE = float(os.getenv("ABSTAIN_DISTANCE", "0.62"))

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
MAX_OUTPUT_TOKENS = 400

ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://localhost:8001")
ORDER_TIMEOUT_S = 3.0
ORDER_RETRIES = 3
