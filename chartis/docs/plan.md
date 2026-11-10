# Delivery Plan: From Prototypes to Productized Offerings

_v2, 2026-11-10. Read it together with `business_case.md`. Timelines and costs are assumptions to validate with Chartis leadership._

## Guiding principles
1. **Build one platform, not five tools.** The AI Value Office (#5) provides the shared pieces: data intake, the result contract (`common.result`), value tracking and governance. Each problem is a module on top of it.
2. **Calibrate before claiming.** No dollar figure goes into marketing until it has been reproduced on at least 2 design-partner clients.
3. **Two offers, not five.** A health-system margin offer (Denials with a partner + Patient Flow, plus Workforce where an agency premium is confirmed, on one value ledger) and a separate Rural sustainability offer. See business_case §1 and §6.
4. **Measure hard and soft value separately, and publish ranges, never point estimates.**
5. **Replace the five most sensitive assumptions first** (business_case §5): agency premium, variable cost per tail day, rural realization rate, pre-bill fix success, AI licence pricing.

## Phases

### Phase 0: Confirm & frame (weeks 0–3)
- Confirm assumptions A1–A6 (business_case §0) with the sponsor.
- Pick 2–3 **design-partner clients**: one rural network or state hospital association, one 400–800-bed community system, one academic medical center.
- Decide **partner vs build for denials**. Denials are about 70% of modeled value, so this decision gates the margin offer.
- Replace the illustrative client in `bundle.py` with each design partner's real size drivers.
- **Exit criteria:** signed design-partner letters, data-sharing agreements and BAAs, and a named product owner per module.

### Phase 1: Calibrate on real data (weeks 3–12)
| Module | Data needed | Calibration target |
|---|---|---|
| Workforce | Timekeeping (Kronos/UKG), HRIS, census by unit | Forecast MAPE ≤ 8%; actual agency/OT rates; turnover model AUC ≥ 0.65 |
| Patient flow | ADT, EDD, case management notes/barrier codes, GMLOS | Barrier attribution reviewed by case management; actual variable cost/day |
| Rural | HCRIS cost reports, payer mix, state Medicaid policy, Chartis INDEX (internal) | Back-test the score against historical closures and conversions |
| Denials | 837/835 claims, denial codes (CARC/RARC), prior-auth logs | Model AUC ≥ 0.70 on holdout; worklist precision at capacity |
| AI value | Inventory of AI pilots, contracts, EHR usage logs | Baseline KPI and value hypothesis for each live use case |
- Replace hand-set coefficients with models trained on client data (logistic or gradient boosting with SHAP explanations). Keep the interpretability.
- **Exit criteria:** value ranges (P10/P50/P90) per module, validated by the client CFO's office.

### Phase 2: Productize (months 3–9)
- Move from CLI + static dashboard to a hosted app: a data pipeline, a secure tenant-per-client store, role-based access and audit logging.
- Package each module as a **Diagnostic offer**: a standard data request, a 6–10 week runbook, a deliverable template and a value baseline.
- Use Jarrard for change-management and communications collateral for workforce and rural.
- Build a governance pack covering NIST AI RMF / CHAI alignment, model cards and bias testing for workforce and denials.
- **Exit criteria:** 5 paid diagnostics delivered, with documented client value of at least 5:1 against fees.

### Phase 3: Scale & sustain (months 9–18)
- Launch subscription tiers (managed analytics plus quarterly value reviews).
- Partner for denials execution.
- Make Rural a state-association offer that adds Rural Health Transformation grant narratives and policy scenario refreshes.
- Run a feedback loop: realized value from the sustain tier recalibrates the models.
- **Exit criteria:** 8+ margin-offer clients, 8+ rural network deals and a published anonymized benchmark report (thought leadership).

## Team (assumed)
| Role | FTE | Notes |
|---|---|---|
| Program lead (partner) | 0.5 | Owns the business case |
| Product owner per module | 5 × 0.5 | Practice leads (workforce, ops, rural, revenue/payer, digital/AI) |
| Data scientists | 3 | Calibration, model validation |
| Data / platform engineers | 3 | Pipelines, hosting, security |
| Clinical and finance SMEs | 2 | Case management, revenue cycle, nursing ops |
| Designer / front-end | 1 | Client-facing app |
| Governance / compliance | 0.5 | HIPAA, AI governance |

**Estimated build cost:** about $5–8M over 18 months, at blended internal rates, plus about $2M/yr to run the platform (assumption).

## Milestones & KPIs
| Milestone | Target date | KPI |
|---|---|---|
| Assumptions confirmed, partners signed | Week 3 | 3 design partners |
| Calibrated prototypes | Week 12 | All modules hit calibration targets |
| First paid diagnostic | Month 4 | ≥ $150K fee |
| 5 diagnostics | Month 9 | ≥ 5:1 documented client value |
| Subscription launch | Month 9 | ≥ 60% diagnostic-to-sustain conversion (assumption) |
| Scale | Month 18 | ~$8–12M run-rate revenue (assumption; ~$24M by year 3) |

## Decision points for leadership
1. Confirm that "Chartis" means The Chartis Group (A1).
2. Approve the two-offer structure: the health-system margin offer and the Rural sustainability offer.
3. Decide whether to partner or build for denials execution. This is the highest-value decision: without denials the offer supports about $0.7M of annual fees, not about $1.9M.
4. Confirm that the AI Value Office is the platform owner, aligned with Leap AI Studio.
5. Approve the Phase 0–1 budget (about $0.8–1.2M, assumption).
