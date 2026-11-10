# Chartis: Five Healthcare Problems (Business Case, Plan, Prototypes)

Answers the question: *"What are the five biggest problems in healthcare that Chartis could reasonably solve?"*

> **Key assumption:** "Chartis" means **The Chartis Group**, the US healthcare advisory firm. If you meant Chartis Research (risk-tech) or another entity, see `docs/business_case.md` §0.
> **All prototype data is synthetic.** Dollar values show how the method works; they are not forecasts.

| Problem | Prototype | Illustrative annual value* |
|---|---|---|
| 1. Workforce shortage & premium labor | `chartis_proto/workforce.py` | see dashboard |
| 2. Capacity & patient flow | `chartis_proto/patient_flow.py` | |
| 3. Rural hospital distress | `chartis_proto/rural.py` | |
| 4. Denials / prior auth / MA friction | `chartis_proto/denials.py` | |
| 5. AI spend without measurable value | `chartis_proto/ai_portfolio.py` | |

\*Each module uses a different reference client, so the values cannot be added together.

## Contents
- `docs/business_case.md`: assumptions, problem sizing with sources, Chartis fit, value logic, commercial model, risks
- `docs/plan.md`: phased delivery plan, team, milestones, decisions for leadership
- `docs/agent_handoff.md`: standalone tasks for follow-on agents
- `docs/review_log.md`: what the independent reviewer agents found and what was changed
- `prototypes/`: Python package (stdlib only) + tests
- `dashboard/index.html`: self-contained dashboard (open in a browser); `dashboard/results.json` holds the raw output

## Run it
Print all five results:

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
