# Review Log

Independent agents reviewed the work in two passes. This log records what they found and what changed. Pass 2 is the most recent.

## Pass 1 (v0 → v1)

Headline values in this section use seed 42.

### Reviewers
| Reviewer | Brief | Outcome |
|---|---|---|
| Research agent | Validate the "Chartis" meaning and the problem list, and source the statistics | Confirmed that Chartis means The Chartis Group, while noting Chartis Research as the alternative. Kept all five problems. Advised folding the OBBBA policy shock into #3 and #4, presenting #5 as the platform, and keeping ambulatory access as the alternate. |
| Red-team agent ("ex-health-system CFO") | Check economic soundness, double counting and the commercial model | 7 High, 3 Medium and 2 Low findings (below) |
| Code-review agent | Check correctness, seed robustness (1–20), dashboard escaping, and render at 1280px and 400px | 4 High, 4 Medium and 3 Low findings, plus weak tests (below) |

### Findings → fixes

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

## Pass 2 (v2)

Pass 2 added value ranges, a sensitivity analysis per module and the one-client value ledger. Two more agents then reviewed the result.

| Reviewer | Brief | Outcome |
|---|---|---|
| Fact-check agent | Verify every external statistic and every claim about Chartis in the business case | 27 claims checked; 13 text corrections applied. Publisher sites were unreachable, so the check rests on search-result summaries. |
| Red-team agent, pass 2 | Challenge the ledger scaling, the sensitivity analysis and the commercial model | 4 High, 7 Medium and 3 Low findings (below) |

### Fact-check corrections applied
| Claim in v1 | Correction |
|---|---|
| OBBBA adds 11.8M uninsured (CBO) | **10M** for the enacted law; 11.8M was the Senate-bill estimate |
| Initial denial rate 11.8% (Premier) | 11.8% is **Kodiak**; Premier reports about 15% |
| Rework cost "$43.84–$57.23" | Not a range: the average rose from $43.84 (2022) to $57.23 (2023) |
| "$25–$118 depending on when it is worked" | The spread is by setting (practices vs hospitals, 2016 data), not timing; marked verify |
| Kaufman Hall: 1-day LOS worth ">$20M in margin" | >$20M in **operating expense**; a similar margin only if beds are backfilled |
| Travel RN 13% premium (SIA/NATHO) | $90.54 bill rate is SIA/NATHO; the $80 staff cost is a vendor estimate, and NATHO puts staff cost higher ($94) |
| "KLAS IT-planning leader" | Overall Best in KLAS for IT Services 2025–26; most-selected firm in the 2025 IT planning report |
| Chartis "Policy Institute" | It is NRHA's Rural Health Policy Institute, where Chartis presents |
| KFF Health News as OBBBA source | Pre-enactment article; replaced with KFF and Georgetown CCF |
| AHA and NSI links | Links now serve the 2026 editions; pinned to the 2025 reports and noted the 2026 figures |
| Boarding cost $1,856 vs $993 per day | Added the caveat: single-centre study of 25 stroke patients |
| Blackstone "since Aug 2024" | Announced Aug 2024, closed Sept 2024 |

### Red-team pass 2: findings → fixes
| # | Severity | Finding | Fix in v2.1 |
|---|---|---|---|
| 1 | High | The headline range was data noise only, and its width depended on sample size. With each module's top assumption at its worst, the total was far lower. | The ledger now reports an **assumption range** (every module's most sensitive assumption at its worst and best value) beside the data-noise range. The business case leads with it. |
| 2 | High | Workforce line rested on an unsourced $105 agency rate and was scaled by 800/298 beds although the modeled units sit inside a 500-bed hospital | Scaling changed to beds/500. Sensitivity now uses sourced values ($90.54 bill rate; $94 NATHO staff cost). The offer includes Workforce only where a premium is confirmed. |
| 3 | High | Denials took 100% of modeled value from day one while rural and AI were haircut | `REALIZATION = 0.75` added to denials and to its sensitivity list. |
| 4 | High | Rural price ($300–600K) failed the doc's own 5:1 rule | Price cut to $200–300K/yr; a higher price is stated to depend on unmodeled grant capture. |
| 5 | Medium | `EFFECT_SCALE = 1.0` was capped at 0.99 as if it were a share, so "+30%" showed −1% | Only values strictly between 0 and 1 are capped. Test added. |
| 6 | Medium | Tornado rows that could not move the answer; overtime rate and AI budget frozen at import; licence price missing | Dead rows removed. Overtime is derived at call time. Budget is read at call time. A licence-price lever was added. A test asserts every listed assumption moves hard value. |
| 7 | Medium | Patient flow was gross of program cost while other lines were net | $600K/yr program cost subtracted. The exclusion of unconstrained beds is labelled conservative. |
| 8 | Medium | The AI line's sign depended on one-time costs shrinking with client size; "moved to other lines" was wrong | One-time costs are held fixed. Wording changed to "removed and not added elsewhere". AI's own hard value is now reported as about zero. |
| 9 | Medium | Residual overlaps (rural operational improvement vs denials/workforce) | The ledger states that rural affiliates' revenue sits outside the $2.0B and that lines are additive with no synergy. |
| 10 | Medium | Commercial model: unclear who pays the partner, no ramp behind payback, ROI quoted on the wrong total | §6 rewritten: the client pays the partner, a ramp and platform run cost sit behind payback (now year 3–4), and ROI is quoted on the offer's own lines. |
| 11 | Medium | "Two offers, not five" is a packaging judgment, not a modeled result | Said so explicitly in §1. |
| 12 | Low | §5 used seed 42 while §3 used P50; rural assumption text said 50% where the constant is 40% | Labelled; text corrected. |

### Effect of pass 2 on the one-client ledger
| | First ledger (v2 draft) | After red-team pass 2 (v2.1) |
|---|---|---|
| Hard value, central | $14.0M | **$9.4M** |
| Range shown | $12.9M–$15.2M (data noise) | **$4.3M–$14.0M** (assumptions) |
| Supportable fees at 5:1 | $2.8M | **$1.9M** ($0.9M worst case) |
| Denials share | 65% | about 70% |
| AI's own hard value | $0.6M | about $0 |

## What the pass-1 fixes changed (v0 → v1 hard value, seed 42)
See business_case.md §1. The main lesson: **once value is honest, it is much smaller and more defensible.**
- Workforce forecasting alone saves little now that agency premiums have fallen. The case rests on retention and on cutting structural agency reliance.
- AI's hard ROI is thin. Ambient documentation does not pay back on hard dollars alone, which is consistent with current market debate.
- These results strengthen the case for Chartis selling **measured, governed value** (the AI Value Office) rather than vendor-style promises.

## Not yet done (see agent_handoff.md)
- Calibrate on real or public data; every number here is still synthetic.
- Price rural access and grant capture.
- Read the primary sources in full; publisher sites were unreachable, so the fact-check used search summaries.
- Model two bad assumptions at once per module (the worst case moves one per module).
