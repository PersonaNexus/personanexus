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
- List every new assumption in the module's `SENSITIVITY` list if it can move hard value; a test fails if a listed assumption does not.
- Rerun `python3 -m chartis_proto --json ../dashboard/results.json --dashboard ../dashboard/index.html` and update the numbers in `docs/business_case.md` when values change.

## Done so far
| Was | Task | Where |
|---|---|---|
| T1 | One reference client and one value ledger, with overlap counted once | `chartis_proto/bundle.py` |
| T2 | P10/P50/P90 seed ranges, one-at-a-time sensitivity, and a worst/best assumption range for the ledger | `chartis_proto/sensitivity.py` |
| T3 | Hard and soft value split in the result contract | `chartis_proto/common.py` |
| T10 | Fact-check of the business case (from search summaries; 13 corrections) | `docs/review_log.md` |
| T11 | Second independent red-team | `docs/review_log.md` |

## Task queue (in priority order)

| ID | Task | Inputs | Done when | Suggested agent |
|---|---|---|---|---|
| N1 | **Calibrate denials on public data.** Denials are about 70% of ledger value and rest on hand-set coefficients. Use CMS public data (e.g. MA prior-authorization and appeal data, the Transparency in Coverage public use file) to anchor denial rates, overturn rates and write-off share by payer type. | `denials.py`, business_case §3 P4 | `WRITE_OFF_SHARE`, `FIX_SUCCESS` and payer offsets each cite a source or are marked assumption; value range reported before and after | general-purpose (needs network access to cms.gov) |
| N2 | **Rural calibration on public data and grant capture.** Replace synthetic hospitals with CMS HCRIS cost reports for one state, back-test the transparent score against known closures and REH conversions, and add a Rural Health Transformation funding-capture option. | CMS HCRIS, the CMS REH list, state RHT plans | Score AUC on historical closures reported; grant capture appears as hard value with a source | general-purpose (needs cms.gov) |
| N3 | **Joint worst case.** The ledger's worst case moves one assumption per module. Add a Monte Carlo over all listed assumptions (triangular between low and high) and report P10/P50/P90 of the ledger total. | `sensitivity.py`, `bundle.py` | Ledger shows a simulated range; dashboard shows it beside the worst/best case | general-purpose |
| N4 | **Workforce soft value and ambient AI link.** Add physician and nurse burnout and documentation-time value as soft value (JAMA Netw Open 2025: burnout 51.9% to 38.8%, pre-post), linked to the ambient documentation use case in `ai_portfolio.py` so it is counted once. | business_case P1 and P5 | Workforce reports non-zero soft value; overlap test passes | general-purpose |
| N5 | **Patient flow for unconstrained hospitals.** The ledger gives the 300 community beds zero. Model them explicitly: no refill, lower program cost. | `patient_flow.py`, `bundle.py` | Ledger line covers all 800 beds with the rule stated | general-purpose |
| N6 | **Denials: CARC/RARC taxonomy and payer scorecard.** Map root causes to real CARC codes and add a payer scorecard (denial rate, days in A/R, overturn rate). | X12 835 code lists | Payer scorecard table in the output | general-purpose |
| N7 | **Ambulatory access / referral leakage (alternate module).** New `access.py`: referral leakage by specialty, third-next-available appointment, value of retained referrals. | business_case §2 | Module + tests + dashboard tab + ledger line | general-purpose |
| N8 | **Client intake.** Let `python -m chartis_proto --client client.json` override `bundle.CLIENT` and the five most sensitive assumptions, so a diagnostic can start from a one-page data request. | `bundle.py`, business_case §5 | A sample `client.json` reproduces the default ledger; changed inputs change it | general-purpose |
| N9 | **Hosted app spike.** Wrap the package in a small FastAPI service with CSV upload per module, using the static dashboard as the front-end. | plan Phase 2 | Runs locally; uploading a sample CSV re-scores | general-purpose |
| N10 | **Primary-source read.** Open each cited page in full (publisher sites were unreachable from the build environment) and confirm the figures still marked **verify**. | business_case, `review_log.md` | Each figure confirmed or corrected with a URL | web research agent with open network access |
| N11 | **Persona definitions.** Use PersonaNexus (this repo) to define agent identities for each module's "AI analyst" under `chartis/personas/*.yaml`, validated with `personanexus validate`. | repo README | Valid YAML; compiled prompts | general-purpose |
| N12 | **Third red-team.** After N1–N3, have a fresh "health system CFO" agent critique the ledger again and log it. | all docs | New entry in `review_log.md` | general-purpose |

## Suggested sequencing
`(N1 ∥ N2 ∥ N10) → N3 → (N4 ∥ N5 ∥ N6 ∥ N8) → N12`. N7, N9 and N11 can run any time.
