"""Orchestrator. Order of decisions (cheap/safe checks first, LLM last):
 injection/promise guard -> human-escalation triggers -> order lookup -> retrieval gate -> LLM -> output checks
"""
import re
import time

from app.config import ABSTAIN_DISTANCE
from app.generation.answer import generate
from app.generation.llm import LLMError
from app.retrieval.retriever import retrieve
from app.security import guard
from app.services.handoff import create_handoff
from app.tools import eligibility
from app.tools.order_client import get_order

ABSTAIN_MSG = ("I couldn't find this in our help documentation, so I don't want to guess. "
               "I can connect you with a human support agent if you'd like.")
ESCALATE_MSG = {
    "crisis": ("I'm really sorry you're going through this. I can't help with this myself, so please contact your local "
               "emergency number or a crisis line right now. I've also asked a human member of our team to reach out (ref {t})."),
    "default": ("I'm sorry about this experience. This needs a person, so I've passed your case to a human agent "
                "(ref {t}). I haven't made any decision on refunds or compensation; they will follow up with you."),
}
ORDER_NEEDED = re.compile(r"where('?s| is) my (order|package|parcel)|track my (order|package)|status of my order", re.I)
REFUND_WORDS = re.compile(r"refund|return|money back", re.I)
CANCEL_WORDS = re.compile(r"cancel", re.I)


def _resp(outcome, answer, started, **kw):
    return {"outcome": outcome, "answer": answer, "citations": kw.pop("citations", []),
            "latency_s": round(time.time() - started, 2), **kw}


def handle(message: str, customer_email: str) -> dict:
    t0 = time.time()

    if guard.check_injection(message):
        return _resp("refused", guard.REFUSAL, t0, reason="guard")

    reason = guard.check_escalation(message)
    if reason:
        ticket = create_handoff(reason, message, customer_email)
        msg = ESCALATE_MSG["crisis" if reason == "crisis" else "default"].format(t=ticket)
        return _resp("escalated", msg, t0, reason=reason, ticket=ticket)

    facts, tools_used = {}, []
    m = guard.ORDER_RE.search(message)
    if m:
        order_id = m.group(0).upper()
        res = get_order(order_id, customer_email)
        tools_used.append(f"order_lookup:{res.outcome}")
        if res.outcome == "not_found":
            return _resp("order_error", f"I couldn't find order {order_id} on your account. Please check the order "
                         "number and that you're signed in with the email used at checkout.", t0, tools=tools_used)
        if res.outcome != "ok":
            return _resp("order_error", "I'm having trouble reaching our order system right now, so I can't check "
                         "your order. Please try again in a few minutes or ask for a human agent.", t0, tools=tools_used)
        o = res.order
        if o is None:
            return _resp("order_error", "I'm having trouble reaching our order system right now, so I can't check "
                         "your order. Please try again in a few minutes or ask for a human agent.", t0, tools=tools_used)
        facts["ORDER"] = (f"id={o.order_id} status={o.status} placed={o.placed_at} estimated_delivery={o.estimated_delivery} "
                          f"delivered={o.delivered_at} total=${o.total:.2f} items={', '.join(o.items)}")
        if REFUND_WORDS.search(message):
            facts["REFUND_CHECK"] = eligibility.refund_check(o)
        if CANCEL_WORDS.search(message):
            facts["CANCEL_CHECK"] = eligibility.cancel_check(o)
    elif ORDER_NEEDED.search(message):
        return _resp("clarify", "Happy to check. What's your order number (it looks like ORD-1234)?", t0)

    passages = retrieve(message)
    if not facts and (not passages or passages[0]["distance"] > ABSTAIN_DISTANCE):
        return _resp("abstained", ABSTAIN_MSG, t0, reason="low_retrieval_confidence", tools=tools_used)

    try:
        out = generate(message, passages, facts)
    except LLMError:
        return _resp("error", "Sorry, I'm having a technical problem. Please try again or ask for a human agent.", t0)

    if not out["can_answer"]:
        return _resp("abstained", ABSTAIN_MSG, t0, reason="unsupported", tools=tools_used)
    if guard.leaks_internal(out["answer"]):
        return _resp("refused", guard.REFUSAL, t0, reason="internal_leak_blocked")
    if out["needs_human"]:
        ticket = create_handoff("conflicting_or_unclear_sources", message, customer_email, out["answer"])
        out["answer"] += f"\n\nI've also asked a human agent to double-check this for you (ref {ticket})."
    return _resp("answered", out["answer"], t0, citations=out["citations"], tools=tools_used)
