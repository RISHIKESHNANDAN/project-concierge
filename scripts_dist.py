import json
from app.config import EVAL_FILE
from app.retrieval.retriever import retrieve

for line in open(EVAL_FILE, encoding="utf-8"):
    q = json.loads(line)
    if q["behavior"] == "abstain":
        p = retrieve(q["question"], k=1)[0]
        print(f'{p["distance"]:.3f}  {q["id"]}  {q["question"][:60]}  -> {p["meta"]["doc_id"]}')