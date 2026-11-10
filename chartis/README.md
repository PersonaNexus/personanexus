# Chartis: Five Healthcare Problems (Business Case, Plan, Prototypes)

Answers the question: *"What are the five biggest problems in healthcare that Chartis could reasonably solve?"*

> **Key assumption:** "Chartis" means **The Chartis Group**, the US healthcare advisory firm. If you meant Chartis Research (risk-tech) or another entity, see `docs/business_case.md` §0.
> **All prototype data is synthetic.** Dollar values show how the method works; they are not forecasts.

**One illustrative $2B health system, all five modules** (`chartis_proto/bundle.py`):

| | Central | If key assumptions are at their worst / best |
|---|---|---|
| Hard (P&L) value per year | **$9.4M** | $4.3M / $14.0M |
| Annual fees that supports at 5:1 | **$1.9M** | $0.9M / $2.8M |
| Soft value per year (never added to hard) | $6.9M | not run |

| Problem | Prototype | Hard value / yr in the ledger | Soft value / yr |
|---|---|---|---|
| 1. Workforce shortage & premium labor | `chartis_proto/workforce.py` | $1.6M | not modeled |
| 2. Capacity & patient flow | `chartis_proto/patient_flow.py` | $0.8M | $2.4M capacity |
| 3. Rural hospital distress | `chartis_proto/rural.py` | $0.6M | access (unpriced) |
| 4. Denials / prior auth / MA friction | `chartis_proto/denials.py` | $6.5M | not modeled |
| 5. AI spend without measurable value | `chartis_proto/ai_portfolio.py` | about $0 after overlap | $4.6M capacity |

## Contents
- `docs/business_case.md`: assumptions, problem sizing with sources, Chartis fit, value logic, commercial model, risks
- `docs/plan.md`: phased delivery plan, team, milestones, decisions for leadership
- `docs/agent_handoff.md`: standalone tasks for follow-on agents
- `docs/review_log.md`: what the independent reviewer agents found and what was changed
- `prototypes/`: Python package (stdlib only) + tests. `bundle.py` is the one-client ledger and `sensitivity.py` the ranges and sensitivity analysis
- `dashboard/index.html`: self-contained dashboard (open in a browser); `dashboard/results.json` holds the raw output

## Run it
Print all five results, their ranges and the one-client ledger (about 15 seconds; add `--fast` to skip the ranges):

```bash
cd chartis/prototypes && python3 -m chartis_proto
```

Run with a different seed and rebuild the dashboard and JSON:

```bash
cd chartis/prototypes && python3 -m chartis_proto --seed 7 --dashboard ../dashboard/index.html --json ../dashboard/results.json
```

Run the tests:

```bash
cd chartis/prototypes && uv run -q --no-project --with pytest python -m pytest
```
