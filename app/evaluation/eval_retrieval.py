"""Measures retrieval ALONE (no LLM). Usage: python -m app.evaluation.eval_retrieval [--mode dense|hybrid]"""
import argparse
import json
import statistics

from app.config import EVAL_FILE, REPORTS_DIR, RETRIEVAL_MODE
from app.retrieval.retriever import retrieve


def load():
    return [json.loads(l) for l in open(EVAL_FILE, encoding="utf-8") if l.strip()]


def main(mode):
    qs = load()
    ans = [q for q in qs if q["behavior"] == "answer" and q["sources"]]
    res = {}
    for k in (1, 3, 5):
        hit_all = hit_any = 0
        for q in ans:
            docs = {p["meta"]["doc_id"] for p in retrieve(q["question"], k=k, mode=mode)}
            hit_all += all(s in docs for s in q["sources"])
            hit_any += any(s in docs for s in q["sources"])
        res[f"recall@{k}_all_sources"] = round(hit_all / len(ans), 3)
        res[f"hit@{k}_any_source"] = round(hit_any / len(ans), 3)
    print(f"mode={mode} n={len(ans)}", json.dumps(res, indent=1))
    print("\nMISSES at k=3 (look at these!):")
    for q in ans:
        got = [p["meta"]["doc_id"] for p in retrieve(q["question"], k=3, mode=mode)]
        if not all(s in got for s in q["sources"]):
            print(f"  {q['id']} {q['question']!r} expected={q['sources']} got={got}")
    d_ans = [retrieve(q["question"], k=1, mode="dense")[0]["distance"] for q in ans]
    d_no = [retrieve(q["question"], k=1, mode="dense")[0]["distance"] for q in qs if q["behavior"] == "abstain"]
    print(f"\ntop-1 distance answerable: mean={statistics.mean(d_ans):.3f} max={max(d_ans):.3f}")
    print(f"top-1 distance unanswerable: mean={statistics.mean(d_no):.3f} min={min(d_no):.3f}")
    print("-> pick ABSTAIN_DISTANCE between these (overlap = some abstention errors are unavoidable)")
    REPORTS_DIR.mkdir(exist_ok=True)
    (REPORTS_DIR / f"retrieval_{mode}.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default=RETRIEVAL_MODE)
    main(ap.parse_args().mode)
