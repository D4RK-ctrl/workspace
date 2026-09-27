# Problem and KPI

**Where should FlashEats operations focus to reduce late deliveries, and is the available data trustworthy enough to identify the responsible workflow stage?** The primary KPI is `late_completed_delivery_rate`: eligible completed orders delivered after the original SQL `promised_eta`, divided by all delay-eligible completed orders. Cancelled and unmeasurable orders are excluded.

# Source reasoning

Four runtime sources have distinct authority: SQLite orders for promise/lifecycle, app actions for recorded interactions, intervention CSV for recorded operational actions, and the dispatch API for current assignment/ETA. Phase 0 comparison exports are not blindly merged; see [source_map.md](source_map.md).

# Retrieval

One command queries read-only SQL, copies and parses two CSVs, and retrieves every dispatch API page with bounded transient retries. It preserves raw bytes/records and completeness evidence under `data/raw/`.

# Validation

Schema, keys, parseability, chronology, cross-source links and dispatch cardinality are checked with PASS/WARN/FAIL/UNKNOWN outcomes. Known raw conflicts and impossible chronology remain FAIL. Only four explicitly handled readiness FAIL IDs may proceed; all other FAILs block modelling. Defects are surfaced, not silently fixed.

# Workflow model

`order_journey.csv` has one row per included canonical order. Exact duplicate rows may collapse; conflicting versions are excluded. App/intervention children aggregate before joins, and every join checks unchanged parent grain. Raw values and eligibility flags remain visible; missing completion is never filled from another source.

# Metrics

Four primary definitions only: eligible late-delivery rate, median minutes late among late orders, median creation-to-pickup minutes, and descriptive late rates by recorded pre-delivery intervention exposure. `metrics.json` and a five-row `evidence_table.csv` expose counts, exclusions, interpretation and limitations. The original promise, not dispatch ETA, anchors lateness. See [metric_definitions.md](metric_definitions.md).

# Dependability

Attempt-scoped staging, structured logs, strict output checks, rollback publication, per-file SHA-256 hashes and a latest-success-only manifest make reruns inspectable. Exit codes distinguish source, validation, model, metric and publication failures. Tracked `data/source/` fixtures allow a clean clone to run without instructor repositories.

# Decision

On the supplied snapshot, about 56.37% of eligible completed deliveries missed the original promise; median lateness among late orders is 7.99 minutes. The broad creation-to-pickup median is 26.15 minutes, which merits investigation. The data do not observe `driver_arrived_at_restaurant`, so restaurant preparation versus driver travel/waiting cannot be separated defensibly. Intervention cohorts are descriptive, not causal. See [decision_output.md](decision_output.md).

# Known / Unknown / Assumptions / Limitations

**Known:** four runtime sources, original promise, visible raw defects, one-row-per-order model. **Unknown:** timezone contract, capture completeness, restaurant-arrival event, freshness SLA and causal intervention effect. **Assumptions:** trim/lowercase is representation-only; logical run date partitions outputs; missing child records do not prove complete capture. **Limitations:** conflicting parents and impossible chronology reduce eligibility; missing completion blocks delay measurement; local publication is not distributed; stage blame and intervention effectiveness are unsupported.
