import json
import time
import uuid

from app.config import REPORTS_DIR


def create_handoff(reason: str, message: str, email: str, summary: str = "") -> str:
    ticket = uuid.uuid4().hex[:8].upper()
    REPORTS_DIR.mkdir(exist_ok=True)
    with open(REPORTS_DIR / "handoffs.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"ticket": ticket, "ts": time.time(), "reason": reason,
                            "customer": email, "message": message, "summary": summary}) + "\n")
    return ticket
