# Review Log

Independent agents reviewed the first draft (v0, commit "WIP, pre-review"). This log records what they found and what changed in v1. Headline values below use seed 42.

## Reviewers
| Reviewer | Brief | Outcome |
|---|---|---|
| Research agent | Validate the "Chartis" meaning and the problem list, and source the statistics | Confirmed that Chartis means The Chartis Group, while noting Chartis Research as the alternative. Kept all five problems. Advised folding the OBBBA policy shock into #3 and #4, presenting #5 as the platform, and keeping ambulatory access as the alternate. |
| Red-team agent ("ex-health-system CFO") | Check economic soundness, double counting and the commercial model | 7 High, 3 Medium and 2 Low findings (below) |
| Code-review agent | Check correctness, seed robustness (1–20), dashboard escaping, and render at 1280px and 400px | 4 High, 4 Medium and 3 Low findings, plus weak tests (below) |

## Findings → fixes

| # | Severity | Finding | Fix in v1 |
|---|---|---|---|
| 1 | High | Hard and soft value were added together, against the doc's own rule | The result contract now carries `annual_value_usd` (hard only) and `soft_value_usd`. The dashboard and CLI show them separately. |
| 2 | High | Workforce savings came from annualizing a 4-week window near the winter peak. Moving the window to the seasonal trough turned savings from +$2.3M into −$1.2M. | Rolling-origin back-test over all 13 windows of a full year. The baseline now has overtime cover. The float pool is salaried (idle time is paid). Core staffing uses the newsvendor-optimal quantile. |
| 3 | High | Modeled turnover was 30%, against the 16.4% stated in the assumptions | Intercept calibrated by bisection to 16.4%. Tested across seeds 1–10. |
| 4 | High | Patient flow counted variable cost and refill margin on the same freed days | Hard value covers only days that are not refilled. Refill margin is soft. Readmission offset added. |
| 5 | High | The synthetic hospital ran at about 67% occupancy, so the capacity and boarding value could not hold | Discharges raised to 37K (88% occupancy, now shown as a metric). Capacity and boarding value apply only at 85% occupancy or above. |
| 6 | High | Variable cost of $800 per tail day was too high | Lowered to $450 (about 15% of full cost per day). |
| 7 | High | AI portfolio headline was $23.8M on $12M of spend, mostly clinician hours, and used promised rather than realized value | Headline is now realized hard value, net of licence, internal cost (50% of licence) and amortized one-time cost. 40% overlap haircut on stacked revenue-cycle use cases. Ambient documentation hours halved and its revenue lift dropped. |
| 8 | High | AI gate funded negative-NPV pilots, and the readiness rule could never trigger | Gate order fixed and matches the docstring. Readiness ≤2 means Hold. Pilots need positive upside. |
| 9 | High | REH conversion produced 30–49% margins | REH model rebuilt from the hospital's own cost structure, with uplift on Medicare outpatient (OPPS) revenue only and loss of critical access hospital cost-based payment. Margin is bounded (see the rural agent's notes). |
| 10 | Medium | Rural value was a hardcoded 35% of shock loss | Value is now derived from per-hospital option deltas × a 15% realization factor. An access-risk column was added. |
| 11 | Medium | Denials: 40% write-off rate (implies about 4% of NPR), uniform fix success, an undocumented ×2 multiplier, and no partner cost | Write-off rate 22%. Fix success by root cause (authorization 30%, coding 65%, eligibility 75%). The multiplier is now a named constant. $750K/yr partner cost subtracted. |
| 12 | Medium | Value counted twice across offers (#5 vs #1, #2, #4) | `overlaps_module` tags plus a "one value ledger per client" rule in ASSUMPTIONS and the business case. |
| 13 | Medium | The CLI swallowed import errors inside modules | Only a missing top-level module is skipped. |
| 14 | Medium | Commercial model compared revenue with build cost, and the build cost was low | §5 rewritten around contribution margin. Build cost raised to include HITRUST/SOC 2 and support. |
| 15 | Low | Dashboard showed `null` as text, used odd decimals, could divide by zero with all-zero values, and left `<!--` unescaped | All fixed. |
| 16 | Low | Missing risks: False Claims Act/upcoding, NLRA and disparate impact, independence conflict, payer AI counter-moves, community backlash, PHI hosting | Added to business case §6. Workforce ASSUMPTIONS note that risk scores are for unit-level use only. |
| 17 | Low | Leaves out Chartis' core franchise (strategy, M&A, cost transformation) | Named as adjacent in business case §2. |
| 18 | Tests | Range checks used seed 42 only, no brute-force AUC test, and duplicated setup | Seed sweeps 1–10 across modules, brute-force AUC check, invariants for the gate and REH margin, shared `conftest`. |

## What the fixes changed (v0 → v1 hard value, seed 42)
See business_case.md §1. The main lesson: **once value is honest, it is much smaller and more defensible.**
- Workforce forecasting alone saves little now that agency premiums have fallen. The case rests on retention and on cutting structural agency reliance.
- AI's hard ROI is thin. Ambient documentation does not pay back on hard dollars alone, which is consistent with current market debate.
- These results strengthen the case for Chartis selling **measured, governed value** (the AI Value Office) rather than vendor-style promises.

## Not yet done (see agent_handoff.md)
- Normalize every module to one reference client (T1).
- P10/P50/P90 sensitivity analysis (T2).
- Fact-check the figures marked "verify" against primary sources, since chartis.com was unreachable (T10).
