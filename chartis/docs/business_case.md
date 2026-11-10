# Business Case: Five Healthcare Problems Chartis Can Reasonably Solve

_Draft v1, 2026-11-10. Built with AI research agents. Every external figure carries its source; anything marked **verify** came from secondary coverage and must be checked before client use. The dollar values for the prototypes come from **synthetic data** and show how the method works. They are not forecasts._

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

**Recommendation:** package each problem as a productized **"diagnostic, then implement, then sustain"** offering with a working analytic accelerator, and put the **AI Value Office** (#5) at the center as the platform that measures value for the other four. Start with **Rural (#3)** and **Patient Flow (#2)**, which have the strongest moat and the fastest value, then **AI Value (#5)**. Build **Denials (#4)** with a partner, because Chartis is weakest there against revenue-cycle outsourcers.

| # | Problem | Chartis fit | Prototype | Illustrative annual value / reference client* |
|---|---|---|---|---|
| 1 | Workforce shortage, burnout & premium labor | Strong (workforce practice + Jarrard) | Staffing forecast + float pool + retention risk | **$3.1M** (500-bed hospital) |
| 2 | Capacity & patient flow (ED boarding, avoidable days) | Strong (acute care / periop throughput) | Discharge-barrier "capacity ledger" | **$8.2M** (500-bed hospital) |
| 3 | Rural hospital distress & service-line loss | **Strongest** (Center for Rural Health) | Transparent vulnerability score + policy stress test | **$7.4M** (20-hospital rural network) |
| 4 | Denials, prior auth & MA friction | Moderate (HealthScape, CDI/UM; RCM outsourcers compete) | Pre-bill denial-risk worklist + payer scorecard | **$11.2M** ($1B NPR system) |
| 5 | AI spend without measurable value | **Strong and strategic** (Leap AI, KLAS IT-planning leader) | AI portfolio prioritization + value tracking | **$23.8M** ($3B system; includes capacity/"soft" value) |

\*From the synthetic prototypes run with seed 42. These are demonstration figures, not client results, and they cannot be added together because the reference clients differ.

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
- **Value: $2.3M labor + $0.8M net retention = $3.1M/yr.**

**Key sensitivity:** the agency premium. The 2025 travel premium (~13%) is much lower than the 2022 peaks, so the case now rests on **overtime, turnover and burnout** more than on cutting travel nurses.

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
- **Value: about 7,500 days freed, about 21 staffed beds released, about 25K ED boarding hours avoided, $8.2M/yr.**

**Key sensitivity:** whether freed beds can be backfilled with paying cases (occupancy, demand, OR capacity).

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
  - 21 hospitals have a strategy option that improves their margin.
- **Value: $7.4M/yr for a 20-hospital network** (35% of shock losses avoided).

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
- **Value: $11.2M/yr, about 1.1% of NPR for a $1B system.**

### Problem 5: AI and digital spend without measurable value

**Size**
- Only **4%** of health systems have scaled AI with measurable ROI, and **4 in 5** struggle to measure it ([Becker's / Qventus](https://www.beckershospitalreview.com/healthcare-information-technology/ai/only-4-of-health-systems-achieve-scaled-ai-roi-report/)).
- **91%** of executives say they need fundamental change within 5 years (Chartis Digital Transformation Survey, [HIT Consultant](https://hitconsultant.net/2025/11/03/the-end-of-incrementalism-why-91-of-health-executives-demand-fundamental-change-with-ai)).

**Why Chartis:** Leap AI Studio (Mar 2026), the Chartis Center for AI, Healthlink's implementation capacity and its KLAS IT-planning leadership. This is its newest growth bet and the cleanest fit.

**Prototype (`ai_portfolio.py`)**
- Scores 25 use cases on risk-adjusted 3-year NPV (adjusted for evidence, data readiness and adoption).
- A governance gate sorts each into **Fund / Pilot / Hold**: high clinical risk with weak evidence is never funded.
- Picks a portfolio under a $12M budget.
- Tracks value against plan: realized value is **70%** of promised, and ambient documentation and coding assist are flagged.
- **Value: $23.8M/yr steady-state risk-adjusted benefit.** Much of this is **capacity value** (clinician hours) and not hard P&L savings; see the sensitivity note.

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

**Rule for client conversations:** lead with hard dollars and present soft value separately. Never add them together.

---

## 5. Commercial model for Chartis (illustrative, **assumption-heavy**)

Chartis' pricing and financials are private. Every number below is an assumption to replace with Chartis data.

| Offer tier | Description | Assumed price | Duration |
|---|---|---|---|
| **Diagnostic** | Accelerator run on client data; value baseline + roadmap | $150K–$350K | 6–10 weeks |
| **Implementation** | Process redesign, tech deployment, change management | $0.8M–$3M | 6–18 months |
| **Sustain (subscription / managed analytics)** | Hosted model, value tracking, quarterly reviews | $120K–$450K / yr | Annual |

**Illustrative year-3 portfolio, all five offers:** 45 diagnostics (~$11M), 18 implementations (~$27M), 35 subscriptions (~$9M), giving **about $47M/yr in revenue**.
- **Assumptions behind it:** diagnostic-to-implementation conversion of about 40%, implementation-to-subscription about 60%, plus some subscription-only rural network deals (state hospital associations).
- **Cost to build:** about $3.5–5M over 18 months (Section 6 of the plan).
- **Payback** is therefore likely within year 2 if conversion holds. **Validate against Chartis pipeline data.**

**Client ROI test:** every engagement should target at least **5:1** documented client value to fees within 12 months. The prototypes suggest that is plausible for #2, #4 and #5, but #1 and #3 depend more on assumptions.

---

## 6. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Synthetic results over-promise | Calibrate on 2–3 design-partner clients before marketing any number; publish ranges, not point estimates |
| Competition (Kaufman Hall/Vizient, Huron, Advisory Board, Big 4, RCM outsourcers) | Lead with moats (rural data, AI build + governance, communications); partner on RCM |
| PHI / data access delays | Standard data request + BAA templates; start with public data (HCRIS, CMS) where possible |
| AI model risk / bias | Governance gate in #5; human-in-the-loop; NIST AI RMF / CHAI-aligned documentation |
| Policy volatility (OBBBA timing, site-neutral payment, MA rules) | Keep scenarios as parameters; refresh quarterly |
| Advisor-to-software shift strains the delivery model | Product owner per accelerator; shared platform (#5) to avoid five one-off tools |

---

## 7. How this was produced and checked

- **Research agent:** sourced statistics, verified that Chartis means The Chartis Group, and flagged that it could mean Chartis Research.
- **Two builder agents and the lead:** built the five prototypes against a shared result contract.
- **Independent reviewer agents:** challenged the logic, the numbers and the code. Their findings and the fixes made are in `docs/review_log.md`.
