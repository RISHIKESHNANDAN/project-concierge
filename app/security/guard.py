import re

from app.config import DOCS_DIR
from app.ingestion.ingest import parse_document

ORDER_RE = re.compile(r"\bORD-\d{3,}\b", re.I)

INJECTION = re.compile(
    r"(ignore|disregard|forget|override)\b.{0,30}\b(previous|prior|above|all|your)\b.{0,30}\b(instructions|rules|prompt)"
    r"|system prompt|developer mode|jailbreak|you are now|reveal.{0,25}(prompt|instructions|internal|notes|confidential)"
    r"|internal (notes|documents?)|i am (a|an) .{0,20}(employee|admin|developer)|print your (rules|instructions)",
    re.I)

PROMISE = re.compile(r"(promise|guarantee|confirm).{0,30}(refund|credit|compensation)|regardless of (the )?policy", re.I)

ESCALATION = {
    "crisis": re.compile(r"kill myself|want to die|end my life|suicid|self[- ]harm", re.I),
    "safety": re.compile(r"\b(fire|burn(ed|t)|injur(y|ed)|allergic reaction|hospital|choking|electric shock)\b", re.I),
    "legal": re.compile(r"\b(lawyer|attorney|sue\b|suing|legal action|court|chargeback|dispute (this|the) charge)", re.I),
    "fraud_security": re.compile(r"\b(hacked|fraud(ulent)?|unauthori[sz]ed (charge|order|access)|stolen|identity theft)\b", re.I),
    "emotional": re.compile(r"\b(furious|outraged|disgusting|scam|fed up|worst|unacceptable|sick of|ridiculous|so angry)\b", re.I),
}

REFUSAL = ("I can't help with that request. I can answer questions about ShopEase orders, "
           "shipping, returns, refunds and accounts.")


def check_injection(msg: str) -> str | None:
    if INJECTION.search(msg):
        return "prompt_injection"
    if PROMISE.search(msg):
        return "unauthorized_promise"
    return None


def check_escalation(msg: str) -> str | None:
    for reason, rx in ESCALATION.items():  # ordered by severity
        if rx.search(msg):
            return reason
    return None


def _internal_texts() -> list[str]:
    out = []
    for p in DOCS_DIR.glob("*.md"):
        meta, body = parse_document(p.read_text(encoding="utf-8"))
        if meta.get("visibility") == "internal":
            out.append(re.sub(r"\s+", " ", body.lower()))
    return out


def leaks_internal(answer: str, n: int = 6) -> bool:
    """Output filter: block any answer repeating n consecutive words from an internal document."""
    words = re.sub(r"\s+", " ", answer.lower()).split()
    for text in _internal_texts():
        for i in range(len(words) - n + 1):
            if " ".join(words[i:i + n]) in text:
                return True
    return False
