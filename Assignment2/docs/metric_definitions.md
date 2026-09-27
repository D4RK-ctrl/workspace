# Phase 4 business metrics

All four primary metrics use the persisted one-row-per-order `order_journey.csv` and its `model_manifest.json`. The project KPI is `late_completed_delivery_rate`. Exclusion counts in `metrics.json` are mutually exclusive at the eligibility level: total model rows, ineligible rows, and eligible rows. Conflicting order versions were excluded before this model and are documented in the model manifest. Raw validation FAILs remain in the raw report.

## late_completed_delivery_rate

- **Business question:** How often do eligible completed deliveries miss the original promise?
- **Numerator:** `delay_metric_eligible` orders with `actual_delivery_at > promised_eta`.
- **Denominator:** All `delay_metric_eligible` orders.
- **Exclusions:** All rows with `delay_metric_eligible = false`; upstream conflicting orders are outside the model.
- **Source fields:** `order_id`, `delay_metric_eligible`, `actual_delivery_at`, original `promised_eta`.
- **Grain:** One eligible completed order; result is a percent.
- **Interpretation:** Share of eligible deliveries that arrived after the original promise.
- **Limitation:** This does not identify which workflow stage caused lateness; dispatch's current ETA never replaces the original promise.

## median_lateness_minutes_among_late_orders

- **Business question:** How severe is lateness when an eligible delivery is late?
- **Numerator:** Not a ratio; each sample is `actual_delivery_at - promised_eta` in minutes.
- **Denominator/sample:** Late orders from the Metric 1 eligible population; `sample_size` equals Metric 1's numerator.
- **Exclusions:** Delay-ineligible and on-time orders.
- **Source fields:** `order_id`, `delay_metric_eligible`, `actual_delivery_at`, original `promised_eta`.
- **Grain:** One late eligible order; median minutes, or null when there are no late orders.
- **Interpretation:** Typical lateness severity among late eligible deliveries.
- **Limitation:** The median does not represent all delivered orders or explain root cause.

## median_creation_to_pickup_minutes

- **Business question:** How long is the broad pre-pickup workflow interval?
- **Numerator:** Not a ratio; each sample is `pickup_at - created_at` in minutes.
- **Denominator/sample:** All `duration_metric_eligible` orders.
- **Exclusions:** Rows with `duration_metric_eligible = false`.
- **Source fields:** `order_id`, `duration_metric_eligible`, `created_at`, `pickup_at`.
- **Grain:** One eligible order; median minutes, or null when there are no eligible orders.
- **Interpretation:** Broad creation-to-pickup elapsed time across multiple stages.
- **Limitation:** This is not restaurant preparation time, driver waiting time, or kitchen delay. `driver_arrived_at_restaurant` is not observed, so those stages cannot be separated.

## late_rate_by_pre_delivery_intervention_exposure

- **Business question:** What lateness is observed among eligible delivered orders with versus without a recorded pre-delivery intervention?
- **Numerator:** Late eligible orders within each exposure cohort.
- **Denominator:** All `delay_metric_eligible` orders in that cohort; the two cohort denominators must sum to the full delay-eligible population.
- **Exclusions:** Delay-ineligible rows; eligible rows with an undefined intervention flag cause a metric error rather than a third invented cohort.
- **Source fields:** `order_id`, `delay_metric_eligible`, `actual_delivery_at`, original `promised_eta`, `has_pre_delivery_intervention`.
- **Grain:** One eligible completed order assigned to one definite boolean cohort; each cohort rate is a percent.
- **Interpretation:** Descriptive observed late rates for exposed and unexposed cohorts.
- **Limitation:** Interventions are not randomly assigned. Higher-risk or already-delayed orders may be more likely to receive intervention, so this comparison cannot establish causal effectiveness. Intervention capture completeness is unknown.

## Why support-opened share is not a primary metric

Customer-app capture completeness is unknown. `SUPPORT_OPENED` counts may provide supporting workflow context, but a support-opened share is not a reliable primary KPI.
