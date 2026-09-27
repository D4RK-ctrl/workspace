# Final source map

The pipeline retrieves exactly four logical runtime sources from the tracked `data/source/` fixtures. Organizational source owners were not established; the authority below is fact-specific, not a claim of verified ownership.

| Source | Retrieval mode | Grain | Important fields | Role / authority | Known quality concerns | Used in final pipeline? |
|---|---|---|---|---|---|---|
| SQLite `orders` | Read-only SQL `SELECT * FROM orders` | Intended one row per order; raw repeated IDs | `order_id`, `created_at`, original `promised_eta`, `pickup_at`, `actual_delivery_at`, `final_status`, customer/restaurant/driver IDs | Original promise and recorded order lifecycle; owner unknown/not established | Three conflicting IDs in supplied snapshot; malformed/impossible chronology; missing completion; timezone unknown | Yes, parent source |
| `customer_app_actions.csv` | CSV file copy and parse | One action, 1:N per order | `action_id`, `order_id`, `customer_id`, `action_type`, `action_at` | Recorded customer app behavior; owner unknown/not established | Capture completeness unknown; some actions outside recorded lifecycle | Yes, aggregated child context |
| `order_interventions.csv` | CSV file copy and parse | One action, treated as 1:N per order | `intervention_id`, `order_id`, `intervention_type`, `intervention_at` | Recorded operational intervention; owner unknown/not established | Timing can be pre-order/post-delivery; selection is non-random; capture completeness unknown | Yes, aggregated child context |
| Dispatch REST API | Paginated HTTP `/dispatch/orders` with bounded transient retries and preserved page bodies | At most one dispatch snapshot per order, checked before join | `order_id`, `driver_id`, `original_driver_id`, assignment times, `current_delivery_eta` | Current assignment and estimate; owner unknown/not established | No full assignment history or observed restaurant arrival; current ETA is not original promise | Yes, checked child snapshot |

SQL orders define the model parent and original delivery promise. App actions and interventions aggregate to order grain before joining. Dispatch cardinality must be unique. Its current ETA and driver identities stay distinct from SQL lifecycle fields. The API is started locally from the tracked fixture when the configured default endpoint is not already healthy; the instructor repositories are not runtime dependencies.

## Audited but not canonical runtime sources

Phase 0 also inspected support tickets, restaurant-status updates, driver telemetry, mixed customer interactions, compiled order events, and precomputed outcomes. They provide useful comparison or reconciliation evidence but have overlapping semantics, different grains, or unclear derivation lineage. App support openings must not be counted again as tickets, and compiled intervention-like events must not be added to the intervention CSV without source-event reconciliation. A missing restaurant-arrival milestone cannot be inferred simply because telemetry exists. The final pipeline does not re-ingest or merge these exports into runtime truth. See [source_audit.md](source_audit.md) for the historical audit.
