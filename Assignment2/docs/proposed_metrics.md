# Candidate metrics for orchestrator review

These five candidates are not finalized. Proposed common delay cohort: unique delivered orders with valid original promise/completion and approved chronology, source precedence and timezone rules. Conflicting records and exclusions must be reported; no first-row policy is approved. The >0-minute definition below is a candidate reflecting Operations, while Support's >10-minute definition remains an alternative for review. Refund exclusion cannot be enforced from the inspected fields alone.

## 1. Late completed-delivery rate

Business question: How often do measurable completed orders miss the original promise?

Numerator: Eligible orders with `actual_delivery_at > promised_eta`.

Denominator: All orders in the approved delay cohort.

Exclusions: Cancellations, unresolved status/duplicate conflicts, invalid/missing required timestamps and unapproved lifecycle violations; report each reason and overlap.

Required fields: `order_id`, `final_status`, `promised_eta`, `actual_delivery_at`; `created_at`, `pickup_at` for lifecycle checks.

Source: SQL `orders`; outcome CSV is a comparison only.

Grain: One order, summarized overall and by approved operational dimensions.

Interpretation: Outcome measure linked directly to reducing late deliveries; report numerator, denominator and percentage together.

Bias / limitation: Excludes unmeasurable deliveries; threshold and refund policy unresolved. Replacing promise with current dispatch ETA would change the question.

## 2. Median lateness among late completed deliveries

Business question: How severe is lateness when a delivery misses its promise?

Numerator: Not a ratio; median of positive `(actual_delivery_at - promised_eta)` in minutes.

Denominator: Not used mathematically; report count of eligible late orders as sample size.

Exclusions: Same as candidate 1, plus on-time/early deliveries. Empty sample returns null.

Required fields: Candidate 1 fields.

Source: SQL `orders`.

Grain: One late order before median aggregation.

Interpretation: Separates severity from frequency; minutes of lateness, not total delivery duration.

Bias / limitation: Median conceals extreme delays and missing completions; the lecture's approximate median is not a target.

## 3. Median time from order creation to pickup

Business question: Is the broad pre-pickup interval a priority for operational investigation?

Numerator: Not a ratio; median of `(pickup_at - created_at)` in minutes.

Denominator: Not used mathematically; report sample size of eligible completed orders with valid creation/pickup/completion chronology.

Exclusions: Cancelled or unresolved-status orders; missing/unparseable or impossible lifecycle times; unresolved duplicate precedence.

Required fields: `order_id`, `final_status`, `created_at`, `pickup_at`, `actual_delivery_at`.

Source: SQL `orders`; telemetry used only for disclosed reconciliation.

Grain: One order before aggregation.

Interpretation: Broad workflow duration that can guide investigation, not proof that a restaurant caused lateness.

Bias / limitation: Combines dispatch, driver travel, restaurant work and waiting. No observed restaurant-arrival milestone supports splitting these components. This measures duration, not delay against a stage-specific promise.

## 4. Recorded support-opened share among late orders

Business question: What proportion of late orders have a recorded customer attempt to reach support?

Numerator: Eligible late orders with at least one valid `SUPPORT_OPENED` action between creation and delivery.

Denominator: Eligible late orders in a declared complete app-capture window; if capture completeness is unconfirmed, report only an explicitly labeled recorded-action share over the late cohort.

Exclusions: Unlinked/invalid actions, unresolved action timing, actions outside the specified window; eligibility exclusions from candidate 1.

Required fields: `action_id`, `order_id`, `action_type`, `action_at`; order `created_at`, `actual_delivery_at`, `promised_eta`, `final_status`.

Source: `data/customer_app_actions.csv` and SQL orders; do not combine with mixed interactions or ticket exports.

Grain: Aggregate action flag to one row per order, then calculate share.

Interpretation: Customer interaction signal linked to late-delivery experience; opening support is not a confirmed ticket.

Bias / limitation: Incomplete instrumentation and other support channels may undercount. Missing actions do not establish satisfaction; time exposed to delay affects opportunity to act.

## 5. Late rate by recorded pre-completion intervention exposure

Business question: What outcomes are associated with operations acting before delivery?

Numerator: Eligible late orders in each of two cohorts: at least one valid intervention between creation and completion, versus no such recorded intervention.

Denominator: All eligible measurable delivered orders in the respective cohort; report both cohort sizes and late counts.

Exclusions: Candidate 1 exclusions; invalid intervention timestamps, pre-creation records and unresolved links. Post-delivery actions are recorded separately and do not qualify as rescue exposure. Unknown source coverage must not be labeled untreated.

Required fields: `intervention_id`, `order_id`, `intervention_at`, `intervention_type`; order `created_at`, `actual_delivery_at`, `promised_eta`, `final_status`.

Source: `data/order_interventions.csv` and SQL orders.

Grain: One intervention-exposure flag per order before cohort aggregation.

Interpretation: Descriptive outcome comparison that helps identify cases for review; optional type breakdown only after overlap handling is approved.

Bias / limitation: Reverse causality, severity selection and intervention timing prevent claims of causal benefit/harm. A higher late rate among intervened orders does not show that interventions caused delay. Snapshot data cannot reliably evaluate refunds or cancellation rescue.
