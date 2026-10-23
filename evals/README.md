# Active evaluation datasets

## Evaluation Studio

Open **http://localhost:5173/evaluations** with the Vite frontend running.
Start its local control service from the repository root:

```sh
evals/.venv/bin/python evals/dashboard.py
```

Use the page to launch core regression, judge calibration, explanations/chat,
or PDF extraction. Model-backed buttons are labeled and use the backend's
existing credentials. Select a smoke test for two cases per dataset. Saved runs,
filters, expected/actual outputs, metric reasons and JSON export are available.
The UI updates after each completed case. Only one run can execute at a time.
The service binds to loopback and Vite proxies `/eval-api`; this is a local
development tool, not a public deployment endpoint. Retrieval still requires
recorded predictions through the CLI. Vite preview/production hosting does not
include this development proxy.

Use **[golden/v2](golden/v2/README.md)**. It contains only source-verifiable facts,
arithmetic, and explicit software contracts. `golden/ACTIVE.json` points to its
manifest. Do not discover datasets by recursively loading every JSONL file.

`golden/v1` is historical, unreviewed draft material retained as source provenance
for reproducibility; it is not the active benchmark. Its clinical and qualitative
labels are excluded from the active suite. The original PDF fixtures are reused.

From the repository root, no API keys or network calls are needed:

```sh
"Analyzer Service/backend/venv/bin/python" evals/curate_golden.py
"Analyzer Service/backend/venv/bin/python" evals/verify_golden.py
```

These commands need `pypdf` and `jsonschema`, already available in the backend
virtual environment. The old `generate_golden.py` builds the historical v1 PDFs;
it is not the active curation command and need not be run to use v2.

Dataset construction and verification are complete. The offline DeepEval runner
and application adapters are implemented; see [execution instructions](IMPLEMENTATION.md).
Live Langfuse dataset uploads and automatic online scoring remain separate work.
