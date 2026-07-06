# mcp-verify

A benchmarked hallucination detector. Give it a SOURCE (the source of truth) and a
DRAFT; it returns the specific claims the source doesn't support, each with
`{claim, reason, source_fact_checked, category, severity}`.

```python
from mcp_verify import build_default_client, verify

client = build_default_client()  # reads ANTHROPIC_API_KEY
report = verify(client, source="...source of truth...", draft="...text to check...")
for f in report.failures:
    print(f.claim, "—", f.reason)
```

## The benchmark

The eval suite (82 labeled cases across 4 domains, a hallucination taxonomy, and a
confusion matrix) travels with the detector. See [BENCHMARK.md](BENCHMARK.md).

```bash
# Offline checks (no API key, no cost):
bash check.sh                      # lint + full test suite
python -m eval.analysis --sample   # failure analysis on a sample report

# Live eval (needs ANTHROPIC_API_KEY):
python -m eval.run                 # full suite
python -m eval.run --smoke         # 5 representative cases
python -m eval.run --judge         # LLM-judge matcher (meaning, not tokens)
python -m eval.ablation            # model/thinking/token-budget ablation
```
