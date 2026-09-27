# Decision output

**Observed on supplied classroom snapshot for logical run date 2026-08-28.** Values below come from `data/gold/run_date=2026-08-28/metrics.json`; counts, exclusions and caveats remain in that file and `evidence_table.csv`. These observations are not hard-coded pipeline expectations. The two intervention rows are cohorts of one primary metric, so the primary metric set still contains exactly four definitions.

| Metric | Observed value | What it means | Decision use | Limitation |
|---|---:|---|---|---|
| Late completed-delivery rate | **56.37%** | 836 of 1,483 delay-eligible completed deliveries missed the original promise | Treat measurable lateness as a material operating issue; monitor this denominator consistently | Ineligible orders and conflicting parent IDs are excluded; it does not locate the responsible stage |
| Median lateness among late orders | **7.99 minutes** | Median severity among the 836 eligible late deliveries | Track severity alongside frequency | Applies only to late eligible orders |
| Median creation-to-pickup interval | **26.15 minutes** | Broad elapsed time from order creation to pickup | Investigate the pre-pickup workflow and instrumentation | Combines preparation, assignment, travel and waiting; not restaurant prep or driver wait alone |
| Late rate, recorded pre-delivery intervention exposed | **56.62%** | 201 late among 355 eligible exposed orders | Describe the observed exposed cohort | Exposure is non-random and capture may be incomplete; no causal effectiveness conclusion |
| Late rate, no recorded pre-delivery intervention | **56.29%** | 635 late among 1,128 eligible unexposed orders | Compare descriptively with the exposed cohort | “Unexposed” means no recorded pre-delivery action, not proof none occurred |

The exposure rates are nearly similar, but that difference does not show whether intervention helped or hurt: higher-risk or already-delayed orders may be more likely to receive an intervention. Lateness is material in the measurable completed-delivery cohort, and the broad pre-pickup interval warrants operational investigation. The pipeline cannot isolate kitchen preparation from driver travel or waiting because `driver_arrived_at_restaurant` is not observed. Improve that milestone and its capture contract before assigning workflow-stage responsibility. Keep the original promise, eligibility exclusions and raw validation FAILs visible when communicating the KPI.
