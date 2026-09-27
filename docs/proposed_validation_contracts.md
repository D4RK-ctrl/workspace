# Proposed validation contracts

Proposals only; no validation code is implemented. FAIL means block the affected publication, retaining diagnostics; WARN means disclose the limitation and exclusion counts. PASS condition states a required invariant. Unknown business semantics stay unresolved and block claims that depend on them. Numeric quality tolerances and freshness SLAs require approval; lecture counts are not contracts.

## Structural

| Rule | Condition | Suggested severity | Business reason | Auto-repair safe? |
|---|---|---|---|---|
| Required inputs and columns | Every selected source exists and has the columns needed by its approved metrics | FAIL | Missing evidence cannot silently become zero or on-time | No |
| Parseable types | Required IDs are non-empty; numeric values are finite; timestamp parsing failures are separately counted from source nulls | FAIL | Silent coercion can change cohort membership | No; retain original value and diagnostic |
| Exact duplicate record | All fields match another record in the same source | WARN | Repeated transport records can inflate counts | Proposed yes with retained raw copy and removal count |
| Conflicting source key | Same intended key has different business fields, including orders and interaction IDs | FAIL | Keep-first is not a justified winner-selection rule | No; needs lineage/owner rule |
| Canonical order grain | Published journey has non-null unique `order_id` | PASS condition | One order must contribute at most once | No; prevent publication on failure |
| Representation normalization | Approved case/whitespace aliases normalize while originals remain preserved | WARN | Formatting should not split the same category | Only approved representation mappings; not semantic aliases |
| Unrecognized category | Status/category/action is outside approved vocabulary | WARN | Hidden input may introduce meaningful new states | No; retain unknown and block affected interpretation |
| Physical ranges | Distance is numeric and non-negative; GPS latitude/longitude are within geographic bounds | WARN | Invalid measures undermine segmentation/location evidence | No; quarantine from affected calculation |

## Lifecycle

| Rule | Condition | Suggested severity | Business reason | Auto-repair safe? |
| Promise chronology | `promised_eta >= created_at` for parseable values | FAIL | Impossible promises invalidate delay interpretation | No; block affected delay publication pending exclusion policy |
| Milestone chronology | `created_at <= pickup_at <= actual_delivery_at` where observed | FAIL | Negative stages cannot support workflow attribution | No; do not reorder or synthesize timestamps |
| Delivered completion evidence | Normalized delivered order has parseable promise and completion | WARN | Report missingness; exclude from delay denominator explicitly | No imputation; exclusions require approved contract |
| Cancellation eligibility | Cancelled orders are not treated as measured completed deliveries | PASS condition | Null completion is not zero delay | No; preserve cancellation population separately |
| Child-event timing | Action/intervention before creation or after completion is identified | WARN | Post-outcome actions cannot be credited with rescuing delivery | No; post-delivery support/credit can be legitimate |
| Restaurant update semantics | `last_updated_at` is checked against lifecycle and an approved use-specific SLA | WARN | Update time may be stale or refer to another process | No; not a substitute for observed readiness |
| Missing arrival milestone | Explicit restaurant-arrival event required for driver-wait/kitchen attribution | FAIL | Available milestones cannot isolate responsible stage | No; do not create arrival from GPS and call it observed |
| Timezone consistency | Sources have a documented common timezone or approved conversion | FAIL | Comparisons across ambiguous time bases can be wrong | No guessed timezone assignment |

## Cross-source

| Rule | Condition | Suggested severity | Business reason | Auto-repair safe? |
| Entity references | Report missing and unmatched order customer/restaurant/driver FKs separately | WARN | Missing dimension coverage biases attribution | No guessed links |
| Child references | Report null/unmatched order references for tickets, actions, events, interventions and dispatch | WARN | Inner joins otherwise silently lose records | No; retain unlinked evidence and coverage |
| Customer/restaurant consistency | Child customer/restaurant matches order when both are present | WARN | Wrong attribution can misdirect operations | No; owner reconciliation required |
| Join cardinality | Aggregate 1:N children first; enforce 1:1 joins and unchanged order key set/count | FAIL | Prevent event fan-out from inflating metrics | No deduplication after a bad join |
| Original versus current driver | Preserve SQL driver, dispatch original driver and current driver distinctly | WARN | Reassignment may explain disagreement | No automatic replacement |
| Completion disagreement | Compare telemetry completion with SQL; report conflicts and SQL gaps | WARN | A second source may own a different lifecycle fact | No automatic fill of the observed 37 gaps |
| Derived-outcome agreement | Compare nulls, statuses, late flags and delays under the same approved definition and rounding | WARN | Detect stale/independently defined outcome exports | No overwriting primary evidence |
| Overlapping event exports | No double counting mixed interactions, app actions, tickets or compiled intervention events | FAIL | Source copies are not independent business actions | No without documented lineage |
| KPI definition ownership | Approved threshold, eligible population, refund handling and source precedence exist | FAIL | Different valid definitions produce different rates | No; orchestrator/business owner decision |
| Zero-child interpretation | Only complete capture supports zero flags; otherwise represent unknown coverage | WARN | Missing source data is not absence of behavior | No unconditional `fillna(0)` |

## Retrieval / Pipeline

| Rule | Condition | Suggested severity | Business reason | Auto-repair safe? |
| Local snapshot retrieval | Record source identity, schema and full retrieved row count; read SQLite without mutation | PASS condition | Demonstrate complete repeatable extraction | No repairs needed |
| API envelope | Required metadata/types and row shape valid on every page | FAIL | Missing `has_more` or total must not mean completion | No defaults that hide malformed payloads |
| Pagination completeness | Consistent total, expected page progression, termination, unique keys and received counts reconcile, including zero total | FAIL | One successful page is not complete retrieval | No invented/missing records |
| Pagination progress | Repeated pages, non-progressing content, empty nonterminal pages or an exceeded bound fail | FAIL | Avoid infinite loops and repeated records | No; stop with evidence |
| Retry policy | Bounded attempts/timeouts for transient 429/5xx/network failures; permanent HTTP/schema errors stop | FAIL | Unavailable data must not be reported as success | Retry transient request only; validate/cap retry delays |
| Raw preservation | Exact selected local inputs/API payload evidence saved before transformation with per-run manifest | PASS condition | Trace metrics to original evidence | No rewriting raw evidence |
| Freshness contract | Compare appropriate source time to logical run date and approved SLA; historical mode explicit | WARN | Newest event is not extraction time or source authority | No automatic date shifting; future-dated input also reviewed |
| Failure diagnostics | Validation/extraction failure writes machine-readable stage/check evidence and nonzero exit | PASS condition | Evaluator must distinguish failed run from valid empty result | No suppressing failure |
| Publication integrity | Publish only validated outputs; all artifacts refer to same successful run; partial writes never appear current | FAIL | Mixed old/new metric and journey files mislead consumers | Safe bounded retry only after failed staging is isolated |
| Rerun determinism | Same inputs/config/logical date yield same metric values, key set and exclusions; no appending duplicates | PASS condition | Repeated runs must be comparable | Replace successful logical output; retain attempt provenance |
| Empty denominator | Emit null metric plus zero denominator/explanation; JSON contains no NaN/Infinity | PASS condition | No observations is not 0% late | Yes, explicit serialization rule |
| Hidden bad inputs | Contract handling is based on schema/grain/semantics, not expected classroom counts or order IDs | PASS condition | Unseen data must fail or exclude transparently | No forcing checkpoint values |
