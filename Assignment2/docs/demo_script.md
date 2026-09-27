# 0:00–0:30 — Problem

“Where should FlashEats operations focus to reduce late deliveries, and is the available data trustworthy enough to identify the responsible workflow stage?” Point to the [README](../README.md) and define the KPI as late completed deliveries against the **original** promised ETA, among eligible orders.

# 0:30–1:00 — Source reasoning

Open [source_map.md](source_map.md). Show the four canonical sources: read-only SQL orders, two CSV files for app actions and interventions, and the paginated dispatch REST API. Explain that Phase 0 audited overlapping tickets, telemetry, events and outcomes, but different grains and unclear lineage mean they are comparison evidence, not extra runtime rows to merge.

# 1:00–1:40 — Run the pipeline

From `Assignment2/`, run:

```sh
python run_pipeline.py --run-date 2026-08-28
```

Walk through **Extract → Validate → Model → Metrics → Publish**. The bundled local API starts automatically when needed. Show `data/run_manifest.json`: a new run ID, stage statuses, relative artifact locations and hashes. Explain that attempts stage under `data/.runs/` and only complete checked outputs publish.

# 1:40–2:20 — Validation judgment call

Open `data/raw/run_date=2026-08-28/validation_report.json`. Raw status remains FAIL due to conflicting duplicate orders and impossible chronology. Do not silently keep the first version, invent chronology, or fill missing completion from another source. Only four explicit handled readiness FAIL IDs may proceed; other FAILs block the model.

# 2:20–2:50 — Workflow model

Open `data/processed/run_date=2026-08-28/order_journey.csv` and its manifest. One row equals one included canonical order. Actions and interventions aggregate before joining; conflicting parent IDs are excluded with provenance; eligibility flags preserve what can be measured. The join checks prevent fan-out, and SQL/dispatch driver identities stay separate.

# 2:50–3:30 — Metrics

Open `data/gold/run_date=2026-08-28/metrics.json` and `evidence_table.csv`. Show the four definitions: 56.37% eligible late-delivery rate, 7.99-minute median among late orders, 26.15-minute broad creation-to-pickup median, and the descriptive intervention cohorts (56.62% versus 56.29%). Show counts and exclusions beside values. Two evidence rows represent the one intervention comparison, not a fifth metric. Do not infer intervention effectiveness.

# 3:30–4:00 — Main FDE judgment call

“We do not observe `driver_arrived_at_restaurant`, so I cannot defensibly split restaurant preparation delay from driver travel or waiting. I treat that as an instrumentation gap rather than inventing a timestamp.” Conclude: monitor measurable lateness, investigate the broad pre-pickup workflow, and improve milestone capture before assigning blame. The [decision output](decision_output.md) records this recommendation.

## Likely viva questions

1. **Why exclude conflicting duplicates instead of keep-first?** There is no trustworthy version order; choosing one would fabricate authority.
2. **Why not fill missing completion from telemetry?** Source precedence for the missing SQL value has not been approved; preserve the gap.
3. **Why aggregate children before joining?** App and intervention records are 1:N; pre-aggregation keeps one model row per order.
4. **Why is intervention comparison not causal?** Actions are assigned to risk, not randomly; exposed orders may already be delayed.
5. **Why is creation-to-pickup not restaurant prep?** It includes assignment, travel and waiting, and restaurant arrival is unobserved.
6. **Why can validation FAIL while modelling proceeds?** Only four named raw defects have explicit model handling; all other FAILs block.
7. **How are reruns safe?** Each attempt stages independently; verified directories publish with rollback and latest-success-only manifest.
8. **What happens on API 429/500?** Bounded transient retries and wait intervals apply; permanent ordinary 4xx fail immediately.
9. **What prevents stale outputs?** Whole run-date directories replace prior versions after checks; old API pages and metric rows cannot append.
10. **What would you improve next?** Establish source timezone/capture contracts and add an observed restaurant-arrival milestone.
