# Agent Hand-off: Tasks Other Agents Can Pick Up

Each task stands alone. Every agent should first read `chartis/README.md`, `docs/business_case.md` §0 (assumptions) and `prototypes/chartis_proto/common.py` (the result contract). Run the tests with:

```bash
cd chartis/prototypes && uv run -q --no-project --with pytest python -m pytest
```

## Ground rules for every agent
- **Synthetic data only.** Never put PHI or real client data in the repo.
- Keep the `run(seed) -> common.result(...)` contract. The dashboard renders any module that follows it.
- Every new benchmark goes into the module's `ASSUMPTIONS` list, with a source or the label "assumption".
- Do not replicate Chartis proprietary methods (e.g. the INDEX); keep models transparent.
- Add or adjust tests for every change.

## Task queue (in priority order)

| ID | Task | Inputs | Done when | Suggested agent |
|---|---|---|---|---|
| T1 | **Normalize to one reference client.** Add `chartis_proto/reference.py` holding one archetype (e.g. a 600-bed, $2B system with 8 affiliated rural hospitals). Make all 5 modules read their sizing from it so the values can be compared. | business_case §0 A5 | Dashboard total becomes meaningful; tests pass | general-purpose |
| T2 | **Sensitivity / P10-P50-P90.** Add `chartis_proto/sensitivity.py`. It reruns each module across seeds 1–50 and across ±30% on its key assumptions, returns value ranges and a tornado chart dataset, and adds a range band to the dashboard. | the ASSUMPTIONS lists | Each module reports P10/P50/P90; dashboard shows ranges | general-purpose |
| T3 | ~~Hard vs soft split~~ **Done in v1.** Next: add an occupancy-aware soft value for workforce (burnout and retention from ambient AI) and grant capture for rural. | business_case §4 | Every module reports a non-zero soft value where it applies | general-purpose |
| T4 | **Public-data rural calibration.** Replace the synthetic rural hospitals with CMS HCRIS cost report data (public) for one state, keeping the transparent score, and back-test against known closures and REH conversions. | CMS HCRIS, the CMS REH list | Score AUC on historical closures reported | general-purpose (needs network access to cms.gov) |
| T5 | **Denials: CARC/RARC root-cause taxonomy.** Map simulated root causes to real CARC codes and add a payer scorecard (denial rate, days in A/R, overturn rate per payer). | X12 835 code lists | Payer scorecard table in the output | general-purpose |
| T6 | **Workforce: ambient AI documentation module.** Add physician burnout and documentation-time savings (JAMA Netw Open 2025: burnout 51.9% to 38.8%) as a linked use case with #5. | business_case P1 | New metrics + tests | general-purpose |
| T7 | **Ambulatory access / referral leakage (alternate #2).** New module `access.py`: referral leakage by specialty, third-next-available appointment, and the value of retained referrals. | business_case §2 | Module + tests + dashboard tab | general-purpose |
| T8 | **Hosted app spike.** Wrap the package in a small FastAPI service with CSV upload per module, using the static dashboard as the front-end. | Plan Phase 2 | Runs locally; upload of a sample CSV re-scores | general-purpose |
| T9 | **Persona definitions.** Use PersonaNexus (this repo) to define agent identities for each module's "AI analyst" (e.g. a Rural Strategy Analyst) under `chartis/personas/*.yaml`, validated with `personanexus validate`. | repo README | Valid YAML; compiled prompts | general-purpose |
| T10 | **Fact-check pass.** Re-verify every statistic in business_case.md marked **verify**, plus the Chartis acquisitions (Healthlink Oct 2025, Leap AI Mar 2026), against primary sources (chartis.com, which was unreachable from the build environment). | business_case | Each figure confirmed or corrected with a URL | web research agent |
| T11 | **Independent red-team (repeat).** After T1–T3, have a fresh agent acting as a "health system CFO" critique the numbers again and log the result in `review_log.md`. | all docs | New review entry | general-purpose |

## Suggested sequencing
`T10 ∥ T1 → T3 → T2 → (T4 ∥ T5 ∥ T6 ∥ T7) → T8 → T11`. T9 can run any time.
