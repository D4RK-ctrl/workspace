# Phase 2 validation contract

The command reads only the preserved Phase 1 raw run directory. Every check records its observed evidence in `validation_report.json`. The current run's checks assess whether source data is fit to proceed; they do not clean records or produce a final order table.

`PASS` means the stated condition holds. `WARN` means an observed limitation is retained and disclosed. `FAIL` blocks downstream modelling and KPI publication. `UNKNOWN` means available evidence or approved business semantics cannot settle the question. Overall status is FAIL if any check fails, otherwise WARN if any WARN or UNKNOWN exists, otherwise PASS. The CLI returns 2 for FAIL, 0 for PASS/WARN, and 1 for extraction or runtime failure.

| Check ID | Category | Rule | Severity | Downstream consequence |
|---|---|---|---|---|
| `raw_manifest_readable`, `raw_manifest_reconciliation`, `dispatch_raw_pagination` | Retrieval | Raw manifest and saved API pages are readable and agree on counts, progression, termination and reported total | FAIL on breach | Cannot trust retrieved population |
| `<source>_raw_readable`, `<source>_required_columns`, `<source>_row_fields` | Structural | Each selected raw source is readable with all required columns and per-record fields | FAIL on breach | Schema break blocks modelling |
| `<source>_key_presence` | Structural | Primary candidate key is a non-empty string | FAIL on breach | Cannot identify business records |
| `<source>_exact_duplicate_ids` | Structural | Same key repeats with identical full-row values | WARN | Retain repeats; future deduplication policy required |
| `<source>_conflicting_duplicate_ids` | Structural | Same key repeats with conflicting full-row values | FAIL | No defensible winner-selection rule |
| `dispatch_duplicate_order_id` | Structural | Dispatch has at most one row per order ID | FAIL | Raw dispatch would fan out a join |
| `<source>_<timestamp>_parse` | Structural | Non-null timestamp parses; null remains distinct from malformed | FAIL for orders; WARN for optional child/dispatch timestamps | Do not coerce malformed event time silently |
| `<source>_<field>_categories` | Structural | Values match provisional observed source vocabulary | WARN for unfamiliar values | Keep new values; no automatic representation or semantic mapping |
| `orders_negative_distance`, `orders_invalid_distance` | Structural | Present distance is finite numeric and non-negative | WARN | Distance analysis would need an exclusion policy |
| `orders_promise_chronology`, `orders_milestone_chronology` | Lifecycle | Promise is after creation; creation, pickup and delivery occur in order when comparable | FAIL on violation | Cannot safely assign lifecycle duration |
| `orders_timezone_comparison_coverage` | Lifecycle | Compared timestamps have compatible timezone awareness | WARN on skipped comparison | Chronology coverage is incomplete |
| `delivered_missing_promised_eta`, `delivered_missing_actual_delivery_at` | Lifecycle | Delivered records have recorded promise and completion | WARN | Later metric eligibility must state exclusions; cancelled records need no completion |
| `orders_future_created_at` | Lifecycle | Parsed creation date is no later than logical run date | WARN | Possible future-dated source record; no wall-clock staleness SLA inferred |
| `<child>_missing_order_id`, `<child>_orphan_order_id` | Cross-source | App actions and interventions link to known orders | WARN | Retain unlinked records and disclose coverage |
| `<child>_ambiguous_parent` | Cross-source | Linked parent has no conflicting source versions | UNKNOWN if ambiguous | Cannot choose a parent row for comparison |
| `app_customer_mismatch` | Cross-source | Linked app customer agrees with order customer when both exist | WARN | Customer attribution needs review |
| `<child>_before_order`, `<child>_after_delivery` | Lifecycle | Child event timing is within comparable order milestones | WARN | Post-delivery action may be legitimate but is not an in-flight rescue |
| `<child>_child_multiplicity`, `orders_parent_grain` | Cross-source | Profile child 1:N multiplicity and parent order key conflicts without joining | PASS for child profile; parent WARN on exact repeats or FAIL on conflicts | Prevent future fan-out and hidden duplicate decisions |
| `dispatch_orphan_order_id`, `orders_missing_dispatch` | Cross-source | Report unmatched records and distinct-order coverage dynamically | WARN on gaps | No fixed 100% threshold or silent inner join |
| `sql_dispatch_driver_consistency` | Cross-source | Report same, different and missing driver IDs | WARN on differences/missing | Current dispatch driver may reflect reassignment, not corruption |
| `business_milestone_driver_arrival` | Semantic | An observed restaurant-arrival milestone supports stage attribution | UNKNOWN | Preparation and driver travel/wait cannot be separated defensibly |
| `timestamp_timezone_definition` | Semantic | An approved timezone contract exists | UNKNOWN | No timezone is assigned by this pipeline |
| `production_freshness_sla` | Semantic | An approved operational freshness SLA exists | UNKNOWN | Historical run-date comparison is not a production SLA |

The report profiles each source with row count, columns, important-field null counts, unique key count, duplicate-key count, and malformed timestamp counts. Examples are bounded to five identifiers or category values. Provisional vocabularies are explicit in `pipeline/validate.py`; unexpected values are WARN and remain unchanged. Empty or unavailable evidence never becomes an automatic PASS for a business claim.
