"""End-to-end evaluation + regression gate.
Usage: python -m app.evaluation.eval_answers [--judge] [--min-score 0.8] [--tag name] [--delay 4]
Start the mock order service first with MOCK_FAIL_RATE=0 MOCK_SLOW_RATE=0 MOCK_MALFORMED_RATE=0.

Correctness is NOT a string match. For answerable questions an answer passes if
 (1) it was answered, (2) it cites at least one expected source document,
 (3) it contains every must_include fact (cheap deterministic check), and
 (4) with --judge, an LLM judge confirms it agrees with the required facts.
Abstain/escalate/order_error expectations are checked on the system outcome."""
import argparse
import json
import sys
import time
from collections import defaultdict

from app.config import REPORTS_DIR
from app.evaluation.eval_retrieval import load
from app.generation.llm import STATS, LLMError, chat_json
from app.services.concierge import handle

ABSTAIN_OK = {"abstained", "refused", "clarify"}
JUDGE = ('You grade a support answer. Given a question, required facts, and an answer, reply JSON '
         '{"correct": bool, "reason": str}. correct=true only if the answer is consistent with every required fact '
         'and does not contradict policy or promise anything extra.')


def score(q, r, use_judge):
    b, out, ans = q["behavior"], r["outcome"], r["answer"].lower()
    if b == "abstain":
        return out in ABSTAIN_OK
    if b == "escalate":
        return out == "escalated"
    if b == "order_error":
        return out == "order_error" and all(m.lower() in ans for m in q["must_include"])
    ok = out == "answered" and all(m.lower() in ans for m in q["must_include"])
    if ok and q["sources"]:
        ok = any(c["doc_id"] in q["sources"] for c in r["citations"])
    if ok and use_judge:
        try:
            ok = bool(chat_json(JUDGE, json.dumps({"question": q["question"], "required_facts": q["must_include"],
                                                   "answer": r["answer"]})).get("correct"))
        except LLMError:
            ok = False
    return ok


def main(judge, min_score, tag, delay):
    questions = load()
    rows, by = [], defaultdict(list)
    for q in questions:
        calls_before = STATS["calls"]
        r = handle(q["question"], q["email"])
        ok = score(q, r, judge)
        by[q["behavior"]].append(ok)
        rows.append({"id": q["id"], "type": q["type"], "ok": ok, "outcome": r["outcome"],
                     "latency_s": r["latency_s"], "answer": r["answer"], "detail": r.get("detail", "")})
        extra = "" if ok else f" | {r.get('detail', '')}"
        print(f"{'PASS' if ok else 'FAIL'} {q['id']} [{q['type']}] -> {r['outcome']}{extra}")
        if delay and STATS["calls"] > calls_before:  # only pause after questions that used the LLM
            time.sleep(delay)

    errors = sum(1 for row in rows if row["outcome"] == "error")
    allok = [o for v in by.values() for o in v]
    overall = sum(allok) / len(allok)
    bad_answers = sum(1 for q, row in zip(questions, rows) if q["behavior"] == "abstain" and row["outcome"] == "answered")
    summary = {"overall": round(overall, 3), "by_behavior": {k: round(sum(v) / len(v), 3) for k, v in by.items()},
               "error_outcomes": errors, "answered_when_should_abstain": bad_answers, "llm_stats": STATS,
               "mean_latency_s": round(sum(r["latency_s"] for r in rows) / len(rows), 2)}
    print(json.dumps(summary, indent=1))
    REPORTS_DIR.mkdir(exist_ok=True)
    (REPORTS_DIR / f"answers_{tag}.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1))

    why = []
    if overall < min_score:
        why.append(f"overall {overall:.2f} < {min_score}")
    if bad_answers:
        why.append(f"{bad_answers} should-abstain question(s) were answered")
    if errors:
        why.append(f"{errors} question(s) ended in 'error' (score is not trustworthy)")
    if why:
        print("REGRESSION GATE FAILED:", "; ".join(why))
        sys.exit(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", action="store_true")
    ap.add_argument("--min-score", type=float, default=0.8)
    ap.add_argument("--tag", default="latest")
    ap.add_argument("--delay", type=float, default=0, help="seconds to wait after each LLM-using question")
    a = ap.parse_args()
    main(a.judge, a.min_score, a.tag, a.delay)