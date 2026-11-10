# Business Case: Five Healthcare Problems Chartis Can Reasonably Solve

_v1 (post-review), 2026-11-10. Built with AI research agents. Every external figure carries its source; anything marked **verify** came from secondary coverage and must be checked before client use. The dollar values for the prototypes come from **synthetic data** and show how the method works. They are not forecasts._

---

## 0. Assumptions to confirm first

| # | Assumption | Why it matters | If wrong |
|---|---|---|---|
| A1 | "Chartis" means **The Chartis Group**, the US healthcare advisory firm (majority owner Blackstone since Aug 2024). | Everything below is built on its capabilities. | If you mean **Chartis Research** (risk-tech analyst firm) or another entity, the problem list changes completely. |
| A2 | The audience is Chartis leadership or a practice lead deciding which **productized offerings / accelerators** to build. | Shapes the commercial model: advisory, then implementation, then subscription. | If the audience is a single client health system, read Section 3 as "client ROI" and skip Section 5. |
| A3 | "Reasonably solve" means Chartis can deliver it with its current or recently acquired capabilities: strategy, operations, workforce, Center for Rural Health, Digital & Technology (incl. Healthlink, Oct 2025), HealthScape (payer/VBC), Jarrard (communications), Leap AI Studio (Mar 2026). It does **not** mean becoming an EHR vendor or a revenue-cycle outsourcer. | Rules out problems like drug pricing, payer consolidation and the clinician pipeline itself. | We would add "build vs. partner" options. |
| A4 | Prototypes use **synthetic data** and **hand-set, interpretable models**. Their job is to show the workflow and the value logic, not to predict accurately. | Keeps the work honest and shareable without PHI. | Production needs client data, a BAA, model validation and governance. |
| A5 | Each prototype has its own **reference client** (500-bed hospital, $1B NPR system, 20-hospital rural network, 1,000-bed / $3B system). | Value figures **cannot be added up** across problems. | Normalize to a single client archetype in the next phase (see plan). |
| A6 | No Chartis internal data, pricing or proprietary IP was used. The rural score is deliberately **not** Chartis' INDEX. | Avoids misrepresenting proprietary products. | Swap in Chartis' real methods and data in Phase 1. |

Research limitations: chartis.com could not be fetched from the build environment, so Chartis' practice details and 2026 rural figures come from press coverage (Fierce, Becker's, KFF Health News). Leap AI deal scope is only partly verified.

---

## 1. Executive summary

US health systems face five problems that interlock: a shrinking, burned-out workforce; hospitals that are full but slow to discharge; rural providers losing money and services under the 2025 Medicaid changes; revenue lost to payer denials and Medicare Advantage friction; and AI spending that rarely shows measurable return.

Chartis is unusually well placed on all five. It has the leading rural health research franchise, operations and workforce practices, a growing digital and AI build capability (Healthlink, Leap AI Studio), and a communications arm (Jarrard) for change management.

**Main finding after independent review:** once hard and soft value are separated and the double counting is removed, per-client hard value is **$0.7M–$4M a year**. That is real but modest. Chartis' edge is not giant ROI claims. It is **credible, measured, governed value**, which is exactly what most health systems lack today (only 4% have scaled AI with measurable ROI).

**Recommendation:** package each problem as a productized **"diagnostic, then implement, then sustain"** offering with a working analytic accelerator, and put the **AI Value Office** (#5) at the center as the platform that measures value for the other four. Start with **Rural (#3)** and **Patient Flow (#2)**, which have the strongest moat and the fastest value, then **AI Value (#5)**. Build **Denials (#4)** with a partner, because Chartis is weakest there against revenue-cycle outsourcers.

| # | Problem | Chartis fit | Prototype | Hard value / yr* | Soft value / yr* | v0 (pre-review) |
|---|---|---|---|---|---|---|
| 1 | Workforce shortage, burnout & premium labor | Strong (workforce practice + Jarrard) | Staffing forecast + float pool + retention risk | **$0.75M** (10 units, ~300 beds) | not modeled | $7.8M |
| 2 | Capacity & patient flow (ED boarding, avoidable days) | Strong (acute care / periop throughput) | Discharge-barrier "capacity ledger" | **$1.4M** (500 beds, 88% occupancy) | $2.3M capacity; 22 beds; 27K boarding hrs | $8.9M |
| 3 | Rural hospital distress & service-line loss | **Strongest** (Center for Rural Health) | Transparent vulnerability score + policy stress test | **$1.6M** (20 most vulnerable hospitals) | access preserved (unpriced) | $7.4M |
| 4 | Denials, prior auth & MA friction | Moderate (HealthScape, CDI/UM; RCM outsourcers compete) | Pre-bill denial-risk worklist + payer scorecard | **$4.2M** ($1B NPR; 0.42% of NPR, net of partner cost) | not modeled | $11.2M |
| 5 | AI spend without measurable value | **Strong and strategic** (Leap AI, KLAS IT-planning leader) | AI portfolio prioritization + value tracking | **$2.8M** ($3B system; realized, net of all costs) | $5.5M clinician/staff capacity | $23.8M |

\*From the synthetic prototypes run with seed 42. These are demonstration figures, not client results. They cannot be added together because each uses a different reference client. The "v0" column shows how much the first draft overstated value before the independent review (see `review_log.md`).

---

## 2. Why these five (and what we left out)

**Selection criteria:** (1) size of the pain in dollars and access, (2) urgency in 2026–27, (3) Chartis' right to win, (4) whether it can be measured within 6–12 months, (5) whether analytics can demonstrate it today.

| Candidate | Size | Urgency | Chartis right to win | Measurable | Verdict |
|---|---|---|---|---|---|
| Workforce & premium labor | Very high | High | High | High | **In** |
| Capacity & patient flow | Very high | Very high | High | High | **In** |
| Rural distress & access | High (access) | Very high (OBBBA) | **Very high** | Medium | **In** |
| Denials / prior auth / MA | Very high | High | Medium | Very high | **In, with partner** |
| AI value realization | High | Very high | **Very high** | Medium | **In, as platform** |
| Ambulatory access & referral leakage | High | High | Medium-high | High | **Swap-in candidate** for academic medical centers or ambulatory-heavy clients |
| Enterprise strategy, affiliations/M&A, cost transformation | Very high | Very high (OBBBA margin pressure) | **Very high (core franchise)** | Medium | **Adjacent:** already Chartis' core business, so not a new problem to productize. The five modules feed it with evidence. |
| Cybersecurity resilience | High | High | Medium (Healthlink) | Medium | Out: specialist firms dominate |
| Value-based care / MA risk | High | Medium | Medium (HealthScape) | Low-medium | Out for now; fold into #4 payer strategy |
| Hospital-at-home / site-of-care shift | Medium | Medium | Medium | Low | Out: depends on policy timing |

---

## 3. The five problems

### Problem 1: Clinical workforce shortage, burnout & premium labor

**Size**
- Labor is about **56% of hospital costs**, roughly $890B in 2024 ([AHA Cost of Caring 2025](https://www.aha.org/costsofcaring)).
- RN turnover is **16.4%** and RN vacancy **9.6%**; it takes **83 days** to recruit an experienced RN ([NSI 2025](https://www.nsinursingsolutions.com/Documents/Library/NSI_National_Health_Care_Retention_Report.pdf)).
- The projected physician shortage is **13,500–86,000 by 2036** ([AAMC](https://www.aamc.org/advocacy-policy/addressing-physician-workforce-shortage)).

**Benchmarks**
- Each RN who leaves costs **$61,110**, and each 1-point change in turnover is worth about **$289K/yr** for an average hospital (NSI 2025, via [Becker's](https://www.beckershospitalreview.com/finance/the-cost-of-nurse-turnover-in-24-numbers-2025.html)).
- Travel premium has dropped to about **13%** over loaded staff cost (~$90.5 vs $80/hr, SIA/NATHO, **verify**).
- Ambient AI scribes cut burnout from **51.9% to 38.8%** at 30 days ([JAMA Netw Open 2025](https://pubmed.ncbi.nlm.nih.gov/41037268/), pre-post study with no control group).

**Why Chartis:** workforce practice, Jarrard for labor relations and change management, and Leap AI for documentation burden.

**Prototype (`workforce.py`)**
- Forecasts unit census with a seasonal-naive + level blend (**6.5% MAPE** on the 4-week back-test).
- Sizes core staffing to the P60 of forecast demand, backed by an internal float pool, and compares that with reactive agency backfill.
- Scores each RN's turnover risk. The top-risk decile leaves at about 2x the overall rate.
- **v1 method (post-review):**
  - The back-test rolls across all 13 four-week windows of a full year.
  - The baseline is a budget grid with overtime and agency cover.
  - The float pool is salaried, so its idle time is paid.
  - Core staffing is set at the newsvendor-optimal quantile (about P28 at current premiums).
  - Turnover is calibrated to 16.4%.
- **Value: $0.49M labor + $0.26M net retention = $0.75M/yr** across 10 units. That is stable across seeds ($0.7–0.9M).

**Key finding:** with the agency premium down to about 13–31%, **better forecasting alone saves little**. In v0, savings flipped negative when the test window moved to the seasonal trough. The workforce case should therefore be repositioned around:
- **retention**, where each turnover point is worth about $289K/yr per hospital
- **structurally eliminating agency reliance**
- **cutting documentation burden** through ambient AI, linked to #5.

It should not be sold as a scheduling-optimization ROI.

### Problem 2: Capacity & patient flow

**Size**
- More than **25%** of admitted ED patients board **4 hours or more** in off-peak months and about **35%** in winter.
- Nearly **5%** wait **24 hours or more** in peak months.
- 2024's best months were worse than the worst months of 2017–19 ([Health Affairs 2025 via U-M IHPI](https://ihpi.umich.edu/news-events/news/wait-times-emergency-hospitalization-keep-getting-higher)).

**Benchmarks**
- A boarded patient costs about **$1,856/day** vs **$993/day** on med/surg ([Annals EM via JUCM](https://www.jucm.com/ed-boarding-costs-hospitals-twice-as-much-as-inpatient-care/)).
- Cutting LOS by 1 day at a 425-bed hospital is worth more than **$20M/yr in margin** (Kaufman Hall via [Becker's](https://www.beckershospitalreview.com/finance/the-cost-of-hospital-unnecessary-hospital-days-8-numbers)).

**Why Chartis:** its acute care and perioperative throughput offering ("break through capacity barriers"), plus its operations practice.

**Prototype (`patient_flow.py`)**
- Attributes each patient's excess days (LOS above GMLOS) to discharge barriers: post-acute placement, payer authorization, diagnostics, transport, guardianship.
- Applies an intervention playbook to those barriers.
- Values the freed bed-days at variable cost and as monetized capacity (50%).
- Adds an admission-time risk score for long stays (AUC 0.62; deliberately modest).
- Only barrier-caused delay is attributed to barriers: min(excess, delay). Random variation stays "unexplained".
- **Results:** about 8,100 days freed, about 22 staffed beds released and about 27K ED boarding hours avoided.
- **Value: hard $1.4M/yr** in variable tail-day cost on beds that are not refilled, net of a $0.46M readmission offset. **Soft $2.3M/yr** comes from the margin on extra admissions in refilled beds.

**Key finding:** the value of patient flow is mostly **capacity**, which is real only when the hospital is full (85% occupancy or more). Sell it as "beds without building" and less boarding, not as cost reduction.

### Problem 3: Rural hospital distress, closures & service-line loss

**Size**
- **417** rural hospitals are vulnerable to closure and **41%** have negative operating margins ([Chartis 2026 State of the State via Fierce](https://www.fiercehealthcare.com/providers/417-rural-hospitals-risk-closing-rural-health-transformation-funds-may-be-too-late)).
- **267** rural hospitals stopped OB services between 2011 and 2021 ([Chartis](https://www.chartis.com/insights/rural-americas-ob-deserts-widen-fallout-pandemic)).
- The 2025 OBBBA law cuts Medicaid by about **$1T over 10 years**, adds about **11.8M uninsured** by 2034 (CBO), and funds a **$50B** Rural Health Transformation Program ([KFF Health News](https://kffhealthnews.org/rural-health/rural-hospitals-battered-by-big-beautiful-bill-researchers/)).

**Why Chartis:** this is its moat. The Center for Rural Health, the vulnerability INDEX, the annual State of the State report and its Policy Institute make Chartis the reference voice.

**Prototype (`rural.py`)**
- Builds a **Transparent Rural Vulnerability Score**. The weights are published, and it is not Chartis' INDEX.
- Adds a scenario engine for a Medicaid cut, a site-neutral/340B change, closing a low-volume OB unit (flags access loss if the next hospital is more than 30 miles away) and conversion to a Rural Emergency Hospital.
- Results across 120 synthetic hospitals:
  - 30 are at risk today, and the shock pushes **20 more** into the at-risk band.
  - The shock costs **$126M/yr** across the portfolio.
- **v1 changes:**
  - The REH model was rebuilt from each hospital's own cost structure, with the margin capped at 10%.
  - **Options that create access loss are rejected** (10 rejected).
  - An access-safe operational-improvement option is always available.
- **Value: $1.6M/yr** = 15% realization × the best access-safe option for each of the 20 most vulnerable hospitals.

**Key finding:** Chartis cannot "avoid" a Medicaid cut. Its value lies in helping boards choose **access-preserving** options early and in capturing Rural Health Transformation funds. Grant capture is not yet modeled; it is task T4.

**Key sensitivity:** how Rural Health Transformation funds are distributed and when OBBBA takes effect (work requirements around 2027, provider-tax phase-down).

### Problem 4: Revenue cycle leakage (denials, prior auth, MA friction)

**Size**
- Providers lost more than **$48B** to final denials and bad debt in 2025, up 25% ([Kodiak via BusinessWire](https://www.businesswire.com/news/home/20260331038554/en/)).
- The initial denial rate is about **11.8%**; MA plans deny **15.7%** ([Premier via Fierce](https://www.fiercehealthcare.com/providers/providers-potentially-wasted-almost-18b-2023-overturning-claims-denials-premier-estimates)).
- MA plans overturned **95%** of appealed SNF prior-auth denials ([HHS OIG 2026](https://oig.hhs.gov/reports/all/2026/medicare-advantage-organizations-overturned-nearly-all-appealed-prior-authorization-denials-for-skilled-nursing-facility-admission-raising-concerns-about-initial-denials/)).

**Benchmarks:** reworking a denial costs **$43.84–$57.23** per claim (Premier), with a range of **$25–$118** depending on when it is worked.

**Why Chartis (partial):** HealthScape (MA contracting strategy) and AI-enabled CDI and utilization management. Revenue-cycle outsourcers (Ensemble, R1) and the Big 4 run claims operations better, so **position on payer strategy plus AI pre-bill prevention, with a partner**.

**Prototype (`denials.py`)**
- An interpretable logistic denial-risk model scores 5,000 claims (AUC 0.70; denial rate 10.8%; MA 14.4% vs 6.7% for traditional Medicare).
- A pre-bill worklist ranks claims by expected recoverable dollars net of rework cost.
- Root-cause mix: coding first, then authorization.
- **v1 assumptions:**
  - 22% of denied dollars are written off without intervention.
  - Fix success varies by root cause (authorization 30%, coding 65%, eligibility 75%).
  - Pre-bill capacity is 10% of claims.
  - A $750K/yr partner cost is subtracted.
- **Value: $4.2M/yr, about 0.42% of NPR for a $1B system.**

### Problem 5: AI and digital spend without measurable value

**Size**
- Only **4%** of health systems have scaled AI with measurable ROI, and **4 in 5** struggle to measure it ([Becker's / Qventus](https://www.beckershospitalreview.com/healthcare-information-technology/ai/only-4-of-health-systems-achieve-scaled-ai-roi-report/)).
- **91%** of executives say they need fundamental change within 5 years (Chartis Digital Transformation Survey, [HIT Consultant](https://hitconsultant.net/2025/11/03/the-end-of-incrementalism-why-91-of-health-executives-demand-fundamental-change-with-ai)).

**Why Chartis:** Leap AI Studio (Mar 2026), the Chartis Center for AI, Healthlink's implementation capacity and its KLAS IT-planning leadership. This is its newest growth bet and the cleanest fit.

**Prototype (`ai_portfolio.py`)**
- Scores 25 use cases on risk-adjusted 3-year NPV (adjusted for evidence, data readiness and adoption).
- A governance gate sorts each into **Fund / Pilot / Hold**: high clinical risk with weak evidence is never funded.
- Picks a portfolio under a $12M budget.
- Tracks value against plan: realized value is **75%** of promised, and 4 use cases are flagged for value leakage.
- **v1 headline basis:**
  - Realized hard value only.
  - Net of licence, internal cost (50% of licence) and one-time cost amortized over 3 years.
  - 40% overlap haircut on stacked revenue-cycle use cases.
- **Value: hard $2.8M/yr; soft $5.5M/yr** of clinician and staff capacity.

**Key finding:** on hard dollars, **ambient documentation is put on Hold**. Its licence cost exceeds its hard savings, and its value is burnout and retention (soft). That is exactly the conversation CFOs are having in 2026, and Chartis' measurement and governance discipline is the product.

**Strategic role:** the AI Value Office becomes the **measurement layer for #1, #2 and #4**. Each of their models becomes a tracked AI or analytics use case with a baseline KPI.

---

## 4. Client value: hard vs soft

| Problem | Hard $ (P&L) | Soft / capacity | Access / quality |
|---|---|---|---|
| Workforce | Premium labor, turnover cost | Manager time | Burnout, retention, safety |
| Patient flow | Variable cost of avoidable days | Beds released, extra admissions | ED boarding hours, LWBS (left without being seen) |
| Rural | Margin protected, grant capture | Board decision support | Services preserved (OB, ED) |
| Denials | Write-offs prevented, rework | Staff productivity | Fewer patient billing disputes |
| AI value | License rationalization, revenue lift | Clinician hours returned | Governed, safe AI use |

**Rule for client conversations:** lead with hard dollars and present soft value separately. Never add them together. The prototypes now enforce this: `annual_value_usd` is hard only and `soft_value_usd` is separate.

**One value ledger per client.** The AI portfolio overlaps #1, #2 and #4 (tagged `overlaps_module`). When one client buys several modules, each dollar is attributed exactly once.

---

## 5. Commercial model for Chartis (illustrative, **assumption-heavy**)

Chartis' pricing and financials are private. Every number below is an assumption to replace with Chartis data. The pricing is set so that **client hard value is at least 5:1 against fees**, based on the v1 values.

| Offer tier | Description | Assumed price | Duration |
|---|---|---|---|
| **Diagnostic** | Accelerator run on client data; value baseline + roadmap | $100K–$250K | 6–10 weeks |
| **Implementation** | Process redesign, tech deployment, change management | $0.4M–$1.5M (often **multi-module per client**) | 6–18 months |
| **Sustain (subscription / managed analytics)** | Hosted model, value ledger, quarterly reviews | $100K–$300K / yr | Annual |

**5:1 test with v1 values:**
- **Single modules:** passes for denials. It is marginal for patient flow and AI unless soft value or a capacity-constrained client is included.
- **Bundled:** a client buying 3 modules (about $5–8M hard value combined, after overlap) supports about $1–1.5M of annual fees.
- **Conclusion:** sell **bundles to one client**, priced against a single value ledger.

**Illustrative year-3 portfolio:**

| Line | Count | Revenue |
|---|---|---|
| Diagnostics | 40 | ~$7M |
| Implementations | 15 | ~$13M |
| Subscriptions | 35 | ~$7M |
| **Total** | | **~$27M** |

- At about 35% contribution margin, that is about **$9.5M/yr of contribution**.
- **Build cost** is about **$5–8M over 18 months**. That includes data engineering, HITRUST/SOC 2 and support for hosting PHI-bearing products.
- **Payback on contribution is therefore about year 3**, not year 2.

**Other cautions:**
- Health-system sales cycles are 6–12 months, so 40 diagnostics by year 3 is aggressive.
- Some revenue will **cannibalize** existing rural, workforce and AI advisory work. Count only incremental revenue.

## 6. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Synthetic results over-promise | Calibrate on 2–3 design-partner clients before marketing any number; publish ranges, not point estimates |
| Competition (Kaufman Hall/Vizient, Huron, Advisory Board, Big 4, RCM outsourcers) | Lead with moats (rural data, AI build + governance, communications); partner on RCM |
| PHI / data access delays | Standard data request + BAA templates; start with public data (HCRIS, CMS) where possible |
| AI model risk / bias | Governance gate in #5; human-in-the-loop; NIST AI RMF / CHAI-aligned documentation |
| Policy volatility (OBBBA timing, site-neutral payment, MA rules) | Keep scenarios as parameters; refresh quarterly |
| Advisor-to-software shift strains the delivery model | Product owner per accelerator; shared platform (#5) to avoid five one-off tools |
| False Claims Act / upcoding exposure from coding and CDI AI (DOJ is active on MA coding) | Compliance review of coding use cases; audit trails; never optimize for revenue alone |
| Nurse risk scoring raises NLRA/union and disparate-impact issues (commute as a proxy) | Unit-level use only; bias testing; labor-relations review (Jarrard) |
| Independence conflict when the AI Value Office measures Chartis' own implementations | Separate measurement team; client-owned value ledger; third-party audit option |
| Payers respond with their own AI denial tools | Payer scorecard + contract strategy (HealthScape); refresh models quarterly |
| Community backlash to OB / REH recommendations | Access-safe options first (enforced in the prototype); Jarrard community engagement |
| Cyber / liability from hosting PHI | HITRUST/SOC 2; minimum-necessary data; client-hosted option |

---

## 7. How this was produced and checked

- **Research agent:** sourced statistics, verified that Chartis means The Chartis Group, and flagged that it could mean Chartis Research.
- **Two builder agents and the lead:** built the five prototypes against a shared result contract.
- **Independent reviewer agents** (a red-team "CFO" and a code reviewer) challenged the logic, the numbers and the code. They made 18 findings. Every High finding was fixed, which cut headline value by about 70–90%. Details are in `docs/review_log.md`.
- **Tests:** 93 automated tests, including seed sweeps and invariants for the governance gate, the REH margin and turnover calibration.
