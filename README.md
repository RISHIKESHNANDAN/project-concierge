# Project Concierge (ShopEase support assistant)

RAG + tool calling + safety for a **synthetic** e-commerce company. All documents, orders and customers are fictional.
Built with AI-assistant help (disclose this in your check-ins and be ready to explain every module).

## Architecture
message -> injection/promise guard -> human-escalation rules -> order lookup (if ORD-id) -> retrieval (+ abstain gate) -> LLM (JSON, cited) -> output checks (citations valid, no internal leak)

- Retrieval: ChromaDB + `all-MiniLM-L6-v2`, section-based chunking, metadata filter drops `superseded` and `internal` docs at query time.
- Conflicts: prompt prefers `authority: policy` over `faq`, then newest `effective_date`; unresolved -> human handoff.
- Abstention: (1) top-1 distance above `ABSTAIN_DISTANCE`, (2) model says it can't answer, (3) answer has no valid citation.
- Tools: order client (timeout, retries, schema validation, id-mismatch check). Orders are looked up only with the signed-in customer's email.
- Policy thresholds (return window, manual-review amount) come from policy-doc front matter, so a policy update changes behaviour.
- Deviation from the original plan: no LangChain/LangGraph; plain ChromaDB + OpenAI-compatible client keeps it small and explainable.

## Run (from a clean checkout)
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # add LLM_API_KEY (and LLM_BASE_URL/LLM_MODEL for non-OpenAI providers)
python -m app.ingestion.ingest --all                   # build the index
uvicorn mock_order_service.main:app --port 8001        # terminal 2 (chaotic by default)
uvicorn app.api.main:app --port 8000                   # terminal 3
streamlit run frontend/streamlit_app.py                # terminal 4
```
Try as alice@example.com: "Am I eligible for a refund on ORD-1002?" As mallory@example.com: "Where is ORD-1001?" (must fail).

## Evaluate
```bash
python -m pytest -q                                    # unit tests, no network/LLM needed
python -m app.evaluation.eval_retrieval --mode dense   # then --mode hybrid  (retrieval only, no LLM)
# for end-to-end runs, start the mock service with all chaos knobs at 0:
MOCK_FAIL_RATE=0 MOCK_SLOW_RATE=0 MOCK_MALFORMED_RATE=0 uvicorn mock_order_service.main:app --port 8001
python -m app.evaluation.eval_answers --judge --min-score 0.8 --tag dense
RETRIEVAL_MODE=hybrid python -m app.evaluation.eval_answers --judge --tag hybrid   # compare two configs
python -m app.evaluation.adversarial                   # attack log -> reports/attack_log.json
```
`eval_answers` exits non-zero if the score drops below the threshold or any should-abstain question gets answered: use it as the regression gate (e.g. in CI).

## Updating a policy without rebuilding
Edit the file (e.g. bump `version`, set old doc `status: superseded`), then:
`python -m app.ingestion.ingest --file data/documents/returns_policy.md` or `POST /admin/reindex/returns_policy.md`.

## Honest status
- This code was written but **not run end-to-end** by the author of this scaffold (no network/LLM key available). Expect to debug: run it, log what breaks in `FAILURES.md`.
- `ABSTAIN_DISTANCE` (0.62) is an untuned guess: tune it from `eval_retrieval` output.
- The 51-question eval set is synthetic and written by the same hand as the documents, so scores will flatter the system.
- Regex guards are brittle (false positives and bypasses are likely); the adversarial set is small.
- Not built yet: latency/cost optimization experiments, monitoring dashboards, auth, report and walkthrough: those you must write from your own results.
