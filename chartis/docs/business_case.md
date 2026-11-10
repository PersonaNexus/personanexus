# Business Case: Five Healthcare Problems Chartis Can Reasonably Solve

_v2.1, 2026-11-10. Built and checked by AI agents (research, build, red-team, code review, fact-check). External figures carry their source. The prototype dollar values come from **synthetic data**: they show how the method works and how sensitive it is, and they are not forecasts for any client._

**What changed in v2:** every value is now a range, each module has a sensitivity analysis, all five modules are rescaled to one client so they can be compared and totalled, an independent fact-check led to 13 text corrections, and a second red-team review cut the combined value by about a third. Details are in `review_log.md`.

---

## 0. Assumptions to confirm first

| # | Assumption | Why it matters | If wrong |
|---|---|---|---|
| A1 | "Chartis" means **The Chartis Group**, the US healthcare advisory firm (majority owner Blackstone; deal announced Aug 2024, closed Sept 2024). | Everything below is built on its capabilities. | If you mean **Chartis Research** (risk-tech analyst firm) or another entity, the problem list changes completely. |
| A2 | The audience is Chartis leadership or a practice lead deciding which **productized offerings** to build. | Shapes the commercial model: advisory, then implementation, then subscription. | If the audience is a single client health system, read §3–4 as "client ROI" and skip §6. |
| A3 | "Reasonably solve" means Chartis can deliver it with current or recently acquired capabilities: strategy, operations, workforce, Center for Rural Health, Digital & Technology (incl. Healthlink, Oct 2025), HealthScape (payer strategy), Jarrard (communications), Leap AI Studio (Mar 2026). It does **not** mean becoming an EHR vendor or a revenue-cycle outsourcer. | Rules out problems like drug pricing or the clinician pipeline itself. | We would add "build vs. partner" options. |
| A4 | Prototypes use **synthetic data** and **hand-set, interpretable models**. | Keeps the work shareable without PHI. | Production needs client data, a BAA, model validation and governance. |
| A5 | The one-client ledger (§4) uses an **illustrative regional health system**: $2.0B net patient revenue (NPR), 800 staffed beds (500 capacity-constrained), 2,400 RNs, 8 affiliated rural hospitals whose revenue sits outside the $2.0B. Module outputs are scaled to it linearly and added with no synergy. | It is the only place values are comparable and summed. | Change `CLIENT` in `chartis_proto/bundle.py` and rerun. |
| A6 | No Chartis internal data, pricing or proprietary IP was used. The rural score is deliberately **not** Chartis' INDEX. | Avoids misrepresenting proprietary products. | Swap in Chartis' real methods and data in Phase 1. |

**Research limits.** chartis.com and most publisher sites could not be opened from the build environment. The fact-check therefore rests on search-result summaries of the cited pages, not on reading them in full. The Leap AI acquisition (19 Mar 2026, terms undisclosed) is confirmed from trade press only.

---

## 1. Executive summary

US health systems face five interlocking problems: a shrinking, burned-out workforce; hospitals that are full but slow to discharge; rural providers losing money and services under the 2025 Medicaid changes; revenue lost to payer denials and Medicare Advantage (MA) friction; and AI spending that rarely shows measurable return.

Chartis is well placed on all five. It has the leading rural health research franchise, operations and workforce practices, a growing digital and AI build capability (Healthlink, Leap AI Studio), a payer-strategy arm (HealthScape) and a communications arm (Jarrard).

**What the prototypes show for one illustrative $2B health system (§4):**

| | Central estimate | Assumption range | Data-noise range |
|---|---|---|---|
| Hard (P&L) value per year, all five modules | **$9.4M** | $4.3M – $14.0M | $8.7M – $10.6M |
| Annual fees that hard value supports at 5:1 | **$1.9M** | $0.9M – $2.8M | $1.7M – $2.1M |
| Soft value per year (beds, clinician time), reported separately | $6.9M | not run | $6.3M – $7.5M |

- **Assumption range** puts each module's most sensitive assumption at its worst, then its best, value. This is the range to plan on.
- **Data-noise range** is P10–P90 across 30 synthetic datasets. It reflects sample size only and understates the real uncertainty.

**Three findings that shape the recommendation:**
1. **Denials carry about 70% of the hard value** ($6.5M of $9.4M, and more in the low case). It is also the area where Chartis is weakest against revenue-cycle outsourcers. The partner-or-build decision for denials is therefore the most important commercial decision.
2. **AI's own hard value is about zero** (−$0.4M to +$0.4M) once use cases already counted in other modules are removed. The AI Value Office earns its place as the **measurement and governance layer**, and through soft value ($4.6M of clinician and staff capacity), not as a profit line.
3. **Rural is a different sale.** Inside a health-system bundle it adds about $0.6M. Its buyers are rural networks and state hospital associations, and its value is access preserved and funding captured, which the prototype does not price.

**Recommendation: two offers, not five.** This is a packaging judgment: the ledger adds the modules with no synergy, so the case for bundling is one buyer and one value ledger, not extra value.
- **Health-system margin offer.** Core: Denials (with a partner) + Patient Flow. Add Workforce only where a first-week diagnostic confirms a real agency premium. The AI Value Office keeps one value ledger per client.
- **Rural sustainability offer.** Led by the Center for Rural Health for rural networks and state associations, built on the transparent stress-test.

---

## 2. Why these five (and what was left out)

**Selection criteria:** (1) size of the pain in dollars and access, (2) urgency in 2026–27, (3) Chartis' right to win, (4) measurable within 6–12 months, (5) demonstrable with analytics today.

| Candidate | Size | Urgency | Chartis right to win | Measurable | Verdict |
|---|---|---|---|---|---|
| Workforce & premium labor | Very high | High | High | High | **In** |
| Capacity & patient flow | Very high | Very high | High | High | **In** |
| Rural distress & access | High (access) | Very high (OBBBA) | **Very high** | Medium | **In** (separate offer) |
| Denials / prior auth / MA | Very high | High | Medium | Very high | **In, with partner** |
| AI value realization | High | Very high | **Very high** | Medium | **In, as platform** |
| Ambulatory access & referral leakage | High | High | Medium-high | High | **Swap-in candidate** for academic medical centers or ambulatory-heavy clients |
| Enterprise strategy, affiliations/M&A, cost transformation | Very high | Very high | **Very high (core franchise)** | Medium | **Adjacent:** already Chartis' core business. The five modules feed it with evidence. |
| Cybersecurity resilience | High | High | Medium (Healthlink) | Medium | Out: specialist firms dominate |
| Value-based care / MA risk | High | Medium | Medium (HealthScape) | Low-medium | Out for now; fold into denials payer strategy |
| Hospital-at-home / site-of-care shift | Medium | Medium | Medium | Low | Out: depends on policy timing |

---

## 3. The five problems

Each prototype below runs on its **own** reference client. The comparable, one-client view is in §4. Values are P50 with the P10–P90 range across 30 synthetic datasets (data noise only; assumption sensitivity is given under each problem).

| # | Problem | Chartis fit | Own reference client | Hard value / yr (P10–P50–P90) | Soft value / yr (P50) |
|---|---|---|---|---|---|
| 1 | Workforce | Strong | 10 units, ~300 beds, 1,100 RNs | $0.7M – **$0.9M** – $1.1M | not modeled |
| 2 | Patient flow | Strong | 500 beds at 88% occupancy | $0.7M – **$0.8M** – $0.9M | $2.4M capacity |
| 3 | Rural | **Strongest** | 20 most vulnerable of 120 hospitals | $1.2M – **$1.4M** – $1.8M | access (unpriced) |
| 4 | Denials | Moderate; partner | $1B NPR | $2.7M – **$3.1M** – $3.6M | not modeled |
| 5 | AI value | **Strong and strategic** | $3B NPR, $12M AI budget | $2.0M – **$2.8M** – $3.5M | $6.9M capacity |

### Problem 1: Clinical workforce shortage, burnout & premium labor

**Size**
- Labor is about **56% of hospital costs**, roughly $890B in 2024 ([AHA Costs of Caring, April 2025](https://www.aha.org/system/files/media/file/2025/04/The-Cost-of-Caring-April-2025.pdf)). The March 2026 edition reports about 60% and $1,009B for 2025.
- RN turnover was **16.4%** and RN vacancy **9.6%** in 2024, with **83 days** to recruit an experienced RN (NSI 2025 report, via [Becker's](https://www.beckershospitalreview.com/finance/the-cost-of-nurse-turnover-in-24-numbers-2025.html)). The NSI 2026 report shows 17.6% turnover, 8.6% vacancy and 78 days.
- The projected physician shortage is **13,500–86,000 by 2036** ([AAMC](https://www.aamc.org/news/press-releases/new-aamc-report-shows-continuing-projected-physician-shortage)).

**Benchmarks**
- Each RN who leaves costs **$61,110**, and each 1-point change in turnover is worth about **$289K/yr** for an average hospital (NSI 2025).
- The 2025 travel RN bill rate is **$90.54/hr** ([SIA/NATHO](https://www.staffingindustry.com/research/research-reports/healthcare/sia-natho-travel-nurse-benchmarking-survey-selected-findings-2026)). A vendor (Nursa) estimates loaded staff RN cost at about $80/hr, a 13% premium. NATHO's own study puts loaded staff cost **higher** than travel, at $94/hr. The premium is disputed, and it decides this business case.
- Ambient AI scribes cut burnout from **51.9% to 38.8%** at 30 days ([JAMA Netw Open 2025](https://pubmed.ncbi.nlm.nih.gov/41037268/); 263 clinicians, pre-post with no control group).

**Why Chartis:** workforce practice, Jarrard for labor relations and change management, and Leap AI for documentation burden.

**Prototype (`workforce.py`)**
- Forecasts unit census and back-tests across all 13 four-week windows of a full year (5.7% MAPE).
- Compares a budget-grid baseline (overtime and agency cover) with forecast-driven core staffing plus a salaried float pool.
- Sets core staffing at the newsvendor-optimal quantile (about P28 at the assumed rates).
- Scores RN turnover risk, calibrated to 16.4%. The top-risk decile leaves at about 2.5x the overall rate.

**Sensitivity:** the agency rate dominates. The model assumes a blended $105/hr. At the only sourced figure, the $90.54 travel bill rate, hard value falls to **$0.1M**. At $120/hr it is **$1.4M**. If loaded staff cost is $94/hr, as NATHO claims, it is $0.4M.

**Key finding:** better scheduling pays only where a real agency premium exists. Establish the client's true premium in the first week of a diagnostic. Otherwise position the work on **retention** and **documentation burden**, not on scheduling ROI.

### Problem 2: Capacity & patient flow

**Size**
- More than **25%** of admitted ED patients board **4 hours or more** in off-peak months and about **35%** in winter. Nearly **5%** wait **24 hours or more** in peak months. 2024's best months were worse than the worst of 2017–19 ([Health Affairs 2025 via Michigan Medicine](https://www.michiganmedicine.org/health-lab/wait-times-emergency-hospitalization-keep-getting-higher)).

**Benchmarks**
- A boarded patient costs about **$1,856/day** vs **$993/day** on med/surg, in a single-centre study of 25 stroke patients ([PubMed](https://pubmed.ncbi.nlm.nih.gov/38795079/)).
- Cutting LOS by 1 day at a 425-bed hospital saves more than **$20M/yr in operating expense**, with a similar additional margin if freed beds are backfilled (Kaufman Hall via [Becker's](https://www.beckershospitalreview.com/finance/the-cost-of-hospital-unnecessary-hospital-days-8-numbers); secondary source).

**Why Chartis:** its acute care and perioperative throughput offering, plus its operations practice.

**Prototype (`patient_flow.py`)**
- Attributes each patient's barrier-caused delay to discharge barriers: post-acute placement, payer authorization, diagnostics, transport, guardianship. Random variation stays "unexplained".
- Applies an intervention playbook and frees about 8,100 bed-days (about 22 staffed beds, about 27K ED boarding hours).
- **Hard value** is the variable cost of tail days on beds that are not refilled, net of a readmission offset and a $600K/yr program cost (weekend imaging, discharge lounge, payer escalation desk). **Soft value** is the margin on extra admissions in refilled beds, counted only at 85% occupancy or above.
- Adds an admission-time long-stay risk score (AUC 0.62; deliberately modest).

**Sensitivity:** the variable cost of a tail day and the share of freed beds that are refilled each move hard value between **$0.2M and $1.3M**.

**Key finding:** the value of patient flow is mostly **capacity**, and it is real only when the hospital is full. Sell it as "beds without building" and less boarding, not as cost reduction.

### Problem 3: Rural hospital distress, closures & service-line loss

**Size**
- **417** rural hospitals are vulnerable to closure and **41%** have negative operating margins ([Chartis 2026 State of the State via Fierce](https://www.fiercehealthcare.com/providers/417-rural-hospitals-risk-closing-rural-health-transformation-funds-may-be-too-late); [BusinessWire](https://www.businesswire.com/news/home/20260210178456/en)).
- **267** rural hospitals stopped OB services between 2011 and 2021 ([Chartis](https://www.chartis.com/insights/rural-americas-ob-deserts-widen-fallout-pandemic)).
- The 2025 OBBBA law cuts federal Medicaid spending by about **$0.9–1T over 10 years** ([KFF](https://www.kff.org/medicaid/issue-brief/allocating-cbos-estimates-of-federal-medicaid-spending-reductions-across-the-states-enacted-reconciliation-package/)) and adds about **10M uninsured** by 2034 (CBO estimate for the enacted law; [Georgetown CCF](https://ccf.georgetown.edu/2025/08/14/new-cbo-health-coverage-estimates-of-budget-reconciliation-law/)). It also funds a **$50B**, five-year Rural Health Transformation Program.

**Why Chartis:** this is its moat. The Center for Rural Health, the vulnerability INDEX, the annual State of the State report and its yearly presentation at NRHA's Rural Health Policy Institute make Chartis the reference voice.

**Prototype (`rural.py`)**
- Builds a **Transparent Rural Vulnerability Score** with published weights. It is not Chartis' INDEX.
- Stress-tests 120 synthetic hospitals with a Medicaid cut and a site-neutral change: 30 are at risk today and the shock pushes **20 more** into the at-risk band, at a cost of **$126M/yr**.
- Evaluates options per hospital: operational improvement, OB consolidation and conversion to a Rural Emergency Hospital (REH). **Options that create access loss are rejected** (10 rejected at seed 42).
- Hard value is 15% realization of the best access-safe option for the 20 most vulnerable hospitals.

**Sensitivity:** the realization rate and the size of operational improvement move value between **$1.1M and $2.1M**, and a 30% higher REH facility payment lifts it to $2.2M. The size of the Medicaid cut barely moves it, because the options do not depend on the cut.

**Key finding:** Chartis cannot "avoid" a Medicaid cut. Its value lies in helping boards choose **access-preserving** options early and in capturing Rural Health Transformation funds. Grant capture and access are not yet priced (hand-off task T4), so the prototype understates this offer.

### Problem 4: Revenue cycle leakage (denials, prior auth, MA friction)

**Size**
- Providers lost more than **$48B** to final denials and bad debt in 2025, up 25% ([Kodiak via BusinessWire](https://www.businesswire.com/news/home/20260331038554/en/)).
- The initial denial rate is about **11.8%** ([Kodiak, 2024 claims](https://www.businesswire.com/news/home/20250521892947/en/Rate-of-initial-denials-of-medical-insurance-claims-continued-to-rise-in-2024-Kodiak-Solutions-proprietary-data-show)). Premier's survey puts it near 15%, with MA plans at **15.7%** ([Premier, 2022 claims](https://hcinnovationgroup.com/population-health-management/payers-providers/news/53099677/premier-survey-15-percent-of-claims-to-private-payers-are-initially-denied)).
- MA plans overturned **95%** of appealed SNF prior-auth denials, though only 18% of denials were appealed ([HHS OIG 2026](https://oig.hhs.gov/reports/all/2026/medicare-advantage-organizations-overturned-nearly-all-appealed-prior-authorization-denials-for-skilled-nursing-facility-admission-raising-concerns-about-initial-denials/)).

**Benchmarks:** the average cost of reworking a denial rose from **$43.84** (2022) to **$57.23** (2023) per claim ([Premier](https://premierinc.com/newsroom/blog/claims-adjudication-costs-providers-25-7-billion)). Older estimates run from about $25 (physician practices) to $118 (hospitals, 2016 data; **verify**).

**Why Chartis (partial):** HealthScape for MA contracting strategy, and AI-enabled CDI and utilization management. Revenue-cycle outsourcers (Ensemble, R1) and the Big 4 run claims operations better.

**Prototype (`denials.py`)**
- An interpretable logistic model scores 5,000 claims (AUC 0.70; denial rate 10.8%; MA 14.4% vs 6.7% for traditional Medicare).
- A pre-bill worklist ranks claims by expected recoverable dollars, net of rework cost and of how fixable each root cause is (authorization 30%, coding 65%, eligibility 75%).
- Only **75%** of modeled prevention is counted as realized, to allow for ramp-up, adoption and prevention the client already does.
- Hard value is net of a $750K/yr partner cost, paid by the client, and equals about **0.31% of NPR**.

**Sensitivity:** pre-bill fix success and the write-off share each move value between **$1.7M and $4.3M**.

**Key finding:** this is the largest and most measurable hard-dollar pool, and the one where Chartis most needs a partner. See §6.

### Problem 5: AI and digital spend without measurable value

**Size**
- Only **4%** of health systems have scaled AI with measurable ROI, and **4 in 5** struggle to measure it ([Becker's / Qventus](https://www.beckershospitalreview.com/healthcare-information-technology/ai/only-4-of-health-systems-achieve-scaled-ai-roi-report/); survey of 60+ IT leaders).
- **91%** of executives say they need fundamental change within 5 years (Chartis survey of 150 executives, [HIT Consultant](https://hitconsultant.net/2025/11/03/the-end-of-incrementalism-why-91-of-health-executives-demand-fundamental-change-with-ai)).

**Why Chartis:** Leap AI Studio, the Chartis Center for AI & Digital Transformation, Healthlink's implementation capacity and its KLAS standing (Overall Best in KLAS for IT Services 2025–26; most-selected firm in KLAS's 2025 IT planning report).

**Prototype (`ai_portfolio.py`)**
- Scores 25 use cases on risk-adjusted 3-year NPV and passes each through a governance gate: **Fund / Pilot / Hold**. High clinical risk with weak evidence is never funded.
- Picks a portfolio under a $12M budget and tracks realized against promised value (about 75% realized; 4 use cases flagged).
- Hard value is realized, net of licence, internal cost and amortized one-time cost, after a 40% haircut on overlapping revenue-cycle use cases.

**Sensitivity:** licence prices dominate. At 30% lower prices hard value is **$5.6M**; at 30% higher it is **$1.0M**.

**Key finding:** on hard dollars, **ambient documentation is put on Hold**. Its licence cost exceeds its hard savings, and its value is burnout and retention (soft). That is the conversation CFOs are having in 2026, and measurement and governance discipline is the product.

---

## 4. One client, one value ledger

`chartis_proto/bundle.py` rescales every module to the illustrative client in A5 and counts overlapping value once.

| Module | Hard value / yr (central) | Worst-case assumptions | Best-case assumptions | Soft value / yr | How it was scaled |
|---|---|---|---|---|---|
| Denials & prior auth | **$6.5M** | $3.7M | $9.0M | not modeled | Gross value × NPR; partner cost half fixed |
| Workforce | **$1.6M** | $0.3M | $2.3M | not modeled | Labor savings × beds / 500 (unmodeled units count as zero); retention × RN headcount |
| Patient flow | **$0.8M** | $0.2M | $1.3M | $2.4M | × capacity-constrained beds; the 300 unconstrained beds are excluded |
| Rural sustainability | **$0.6M** | $0.4M | $0.8M | access (unpriced) | × 8 affiliated rural hospitals |
| AI value (after overlap) | **$0.0M** | −$0.4M | $0.6M | $4.6M | Benefits and run costs × NPR; one-time costs fixed |
| **Total** | **$9.4M** | **$4.3M** | **$14.0M** | **$6.9M** | |

- Central hard value is about **0.47% of NPR**.
- At a 5:1 client-ROI rule it supports about **$1.9M of annual fees**, and **$0.9M** in the worst case.
- About $1.1M of funded AI use cases overlaps other modules. It is removed from the AI line and not added elsewhere, which is conservative.

**Limits**
- Scaling is linear, the client is invented and the lines are added with no synergy.
- Worst and best cases move one assumption per module. Two bad assumptions in the same module would go lower.
- Central values are P50 across 30 synthetic datasets; the worst and best cases are run at seed 42.
- Treat the total as an order of magnitude until it is calibrated on a real client.

**Rules the ledger enforces**
- Hard and soft value are never added together.
- Each dollar is counted once. Funded AI use cases that a module already claims are removed from the AI line.

---

## 5. What moves the numbers

Each assumption below was moved on its own, holding the rest fixed (`chartis_proto/sensitivity.py`). Moves are ±30%, or sourced low and high values where they exist. Values are for each module's own reference client at seed 42, so the base can differ slightly from the P50 in §3.

| Module | Most sensitive assumption | Low case | Base | High case |
|---|---|---|---|---|
| Workforce | Agency hourly rate ($90.54 sourced to $120) | $0.1M | $0.7M (at $105) | $1.4M |
| Patient flow | Variable cost per tail day (±30%) | $0.2M | $0.8M | $1.3M |
| Rural | Realization of option value (±30%) | $1.1M | $1.6M | $2.1M |
| Denials | Pre-bill fix success rates (±30%) | $1.7M | $3.0M | $4.3M |
| AI value | Licence prices (±30%) | $1.0M (prices up) | $2.8M | $5.6M (prices down) |

**Reading:** one assumption moves a module's value by 30% to 100%, several times more than data noise. The first job of any diagnostic is to replace these five assumptions with the client's own numbers.

---

## 6. Commercial model for Chartis (illustrative, **assumption-heavy**)

Chartis' pricing and financials are private. Every number below is an assumption to replace with Chartis data.

**Two offers, priced to pass 5:1 even in the worst case**

| Offer | Buyer | Contents | Modeled hard value | Assumed price |
|---|---|---|---|---|
| **Health-system margin offer** | CFO / COO of a $1–5B system | Denials (with partner) + Patient Flow, Workforce where the premium is confirmed; one value ledger | $8.9M central; $4.2M worst case (for a $2B system) | Diagnostic $200–300K, then **$0.6–0.9M/yr** |
| **Rural sustainability offer** | Rural networks, state hospital associations | Stress-test, access-safe options, Rural Health Transformation funding support | $1.4M for a 20-hospital network | **$200–300K/yr** per network |

- At $0.6–0.9M/yr the margin offer gives the client about 5–7:1 in the worst case and 10–15:1 in the central case.
- The rural price passes 5:1 on modeled value alone. A higher price would have to rest on grant capture, which is not modeled.
- The denials partner's cost ($1.1M/yr for a $2B client) is already subtracted from the client's value. The client pays the partner; Chartis' fee is separate.

**Illustrative year-3 revenue**

| Line | Count | Unit price | Revenue |
|---|---|---|---|
| Margin-offer subscriptions | 10 | $0.75M | $7.5M |
| Implementation projects (one-time) | 8 | $1.0M | $8.0M |
| Rural network deals | 10 | $0.25M | $2.5M |
| Standalone diagnostics | 30 | $0.2M | $6.0M |
| **Total** | | | **$24.0M** |

- At about 35% contribution margin, that is about **$8.4M/yr of contribution** in year 3.
- **Build cost** is about **$5–8M over 18 months**, plus about **$2M/yr** to run the platform (hosting, HITRUST/SOC 2, support).
- **Payback is in year 3 to 4**, assuming contribution ramps from about $1M in year 1 to $4M in year 2 and $8.4M in year 3 ($13.4M cumulative, against $11–14M of build and run cost).

**The denials decision**
- Denials are about 70% of modeled value, so the margin offer does not work without them.
- **Options:**
  - Partner with a revenue-cycle operator: fastest, and the client pays the partner.
  - Build a pre-bill prevention layer only: keeps Chartis in strategy and AI, where it is credible.
  - Leave denials out: client value falls to about $3.4M and supportable fees to about $0.7M.
- **Recommended:** partner for execution, and own the payer strategy, the model and the value ledger.

**Cautions**
- Health-system sales cycles are 6–12 months, so 10 subscription clients by year 3 is ambitious.
- Some revenue will **cannibalize** existing rural, workforce and AI advisory work. Count only incremental revenue.

---

## 7. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Synthetic results over-promise | Calibrate on 2–3 design-partner clients before marketing any number; publish assumption ranges, never point estimates or data-noise ranges alone |
| Bundle depends on denials, Chartis' weakest area | Decide partner vs build in Phase 0; without a partner, lead with Patient Flow + Workforce and price accordingly |
| Workforce value disappears where agency carries no premium | Measure the client's real premium in week one; sell Workforce only where it is confirmed, otherwise fall back to retention and documentation burden |
| Competition (Kaufman Hall/Vizient, Huron, Advisory Board, Big 4, RCM outsourcers) | Lead with moats (rural data, AI build + governance, communications); partner on RCM |
| PHI / data access delays | Standard data request + BAA templates; start with public data (HCRIS, CMS) where possible |
| AI model risk / bias | Governance gate in the AI module; human in the loop; NIST AI RMF / CHAI-aligned documentation |
| False Claims Act / upcoding exposure from coding and CDI AI | Compliance review of coding use cases; audit trails; never optimize for revenue alone |
| Nurse risk scoring raises NLRA/union and disparate-impact issues | Unit-level use only; bias testing; labor-relations review (Jarrard) |
| Independence conflict when the AI Value Office measures Chartis' own work | Client-owned value ledger; separate measurement team; third-party audit option |
| Payers respond with their own AI denial tools | Payer scorecard + contract strategy (HealthScape); refresh models quarterly |
| Community backlash to OB / REH recommendations | Access-safe options first (enforced in the prototype); Jarrard community engagement |
| Policy volatility (OBBBA timing, site-neutral payment, MA rules) | Keep scenarios as parameters; refresh quarterly |
| Cyber / liability from hosting PHI | HITRUST/SOC 2; minimum-necessary data; client-hosted option |

---

## 8. How this was produced and checked

- **Research agent:** sourced the statistics and confirmed which "Chartis" this is.
- **Builder agents and the lead:** built the five prototypes against a shared result contract.
- **Red-team ("ex-health-system CFO") and code-review agents, pass 1:** 18 findings. Every High finding was fixed, which cut headline values by about 70–90%.
- **Fact-check agent, pass 2:** checked 27 claims; 13 text corrections were applied in this version (for example, CBO's uninsured estimate for the enacted law is 10M, not 11.8M).
- **Red-team, pass 2:** reviewed the one-client ledger, the sensitivity analysis and this document. It made 14 findings, and the fixes cut the combined hard value from $14.0M to $9.4M. Findings and fixes are in `review_log.md`.
- **Tests:** automated tests cover seed sweeps, the governance gate, the REH margin bound, turnover calibration, the sensitivity patching and the ledger arithmetic.
