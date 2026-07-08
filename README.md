# mcp-verify

A benchmarked hallucination detector. Give it a SOURCE (the source of truth) and a
DRAFT; it returns the specific claims the source doesn't support, each with
`{claim, reason, source_fact_checked, category, severity}`.

**Benchmarked:** 106 labeled cases across 4 domains + an adversarial red-team
tranche. Over 3 independent runs: precision 97.9% [96.6, 99.1], recall 99.1%,
F1 98.5% (95% CIs) — with every residual failure adjudicated and documented.
See [BENCHMARK.md](BENCHMARK.md).

```python
from mcp_verify import build_default_client, verify

client = build_default_client()  # reads ANTHROPIC_API_KEY
report = verify(client, source="...source of truth...", draft="...text to check...")
for f in report.failures:
    print(f.severity, "|", f.claim, "—", f.reason)

# Reliability mode: run N times, keep only majority-confirmed claims;
# unstable ones land in report.uncertain instead of report.failures.
report = verify(client, source="...", draft="...", consistency=3)
```

## Run as MCP server

One tool, `verify(source, draft, consistency=1)`, over stdio:

```bash
pip install mcp-verify   # or: pip install -e . from a checkout
claude mcp add verify -- mcp-verify
```

Two modes, auto-selected (`MCP_VERIFY_MODE=api|sampling` overrides):

- **sampling** (default, no key): the server asks the HOST's model to do the
  verification via MCP sampling — no ANTHROPIC_API_KEY, no extra cost.
- **api**: if `ANTHROPIC_API_KEY` is set in the server's environment, it calls
  the pinned benchmark model directly — the exact path BENCHMARK.md measures.
  `claude mcp add verify -e ANTHROPIC_API_KEY=sk-... -- mcp-verify`

Both return the same JSON: `{"passed", "failures": [...], "uncertain": [...], "mode"}`.

## The benchmark

The eval suite (106 labeled cases across 4 domains plus a red-team tranche, a
15-type hallucination taxonomy, and a confusion matrix) travels with the
detector. See [BENCHMARK.md](BENCHMARK.md).

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
