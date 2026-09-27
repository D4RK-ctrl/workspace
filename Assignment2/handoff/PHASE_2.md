# STATUS

Phase 2 extract-and-validate implementation complete. The supplied snapshot correctly produces overall FAIL; downstream modelling/KPI publication is blocked pending business and data remediation. Awaiting orchestrator review.

# FILES CREATED OR CHANGED

Created `pipeline/validate.py`, `tests/test_validate.py`, `docs/validation_contract.md`, and this handoff. Updated `run_pipeline.py` and `README.md`. Made a narrow change to `pipeline/extract.py` so invalid/duplicate dispatch IDs remain in preserved raw pages and receive validation FAIL instead of being rejected before the report. No other project, Phase 0, or instructor files changed.

# COMMANDS RUN

Read Phase 1 handoff, proposed validation contracts and current extraction code. Ran `python -B -m unittest discover -s tests -v`, then `python -B run_pipeline.py --run-date 2026-08-28` using the available bundled Python. Read the resulting report with strict JSON parsing and checked the Git file scope and reference repositories. The final full command was rerun after the narrow dispatch-ID change. Generated raw-directory access required sandbox escalation.

# TEST RESULTS

25 tests passed: six existing extraction tests and 19 Phase 2 synthetic validation tests. Coverage includes required schema, exact/conflicting duplicates, malformed timestamps, chronology, cancellations, orphan and mismatched links, child timing, dispatch duplication/invalid ID preservation, driver mismatch, new categories, future records, UNKNOWN semantics, overall precedence and CLI exit codes. A non-failing socket ResourceWarning appeared once during the combined suite; no test failed.

# VALIDATION SUMMARY

`data/raw/run_date=2026-08-28/validation_report.json` is strict JSON, about 32 KB. Final snapshot result: 54 PASS, 8 WARN, 4 FAIL, 4 UNKNOWN; overall FAIL. Profiles cover 1,603 order rows, 2,365 app actions, 430 interventions and 1,600 dispatch records. No fixed classroom count is an assertion.

# FAIL CHECKS

- `orders_conflicting_duplicate_ids`: 3 order IDs have conflicting rows (`O00120`, `O00723`, `O01302`).
- `orders_promise_chronology`: 4 rows promise delivery before creation.
- `orders_milestone_chronology`: 5 rows deliver before pickup.
- `orders_parent_grain`: 3 conflicting IDs prevent an approved one-order parent grain. This reflects the duplicate conflict through a separate modelling-readiness check, not an additional set of bad orders.

# WARN CHECKS

Five `Delivered` status values and three `HIGH` traffic values are outside provisional exact vocabularies; 37 delivered rows lack completion. One app action precedes order creation and 32 follow delivery. One intervention precedes creation and 45 follow delivery. SQL versus current dispatch driver differs on 95 linked orders, with 3 missing on one side; reassignment can explain differences. No values were normalized or repaired.

# UNKNOWN CHECKS

Four app actions link to orders with conflicting parent versions, so their parent-based comparison is unresolved. `business_milestone_driver_arrival` is UNKNOWN because selected sources lack an observed restaurant-arrival event. Timezone definition and production freshness SLA are also UNKNOWN. UNKNOWN entries do not crash validation or become PASS.

# OBSERVED DATA QUALITY

All four sources have the required schema in this snapshot. Timestamp parsing reports zero malformed non-null values for selected fields. Raw API pagination rechecks eight preserved pages; page progression, termination and reported total reconcile. Source row counts and available SHA-256 hashes agree with the raw manifest. The report includes bounded examples, field null counts, unique-key counts and duplicate-key counts.

# EXIT CODE CHECK

The real command returned `2` after writing the FAIL report. Synthetic CLI tests verify `2` for FAIL and `0` for WARN/UNKNOWN. Extraction/configuration failures return `1`. No later-stage output was produced.

# KNOWN

Only preserved Phase 1 raw artifacts were read for validation. The validator never contacted the API, loaded the instructor repositories, filled missing completion times, deduplicated orders or built an order journey.

# UNKNOWN

Canonical order conflict precedence, timezone, milestone instrumentation, source coverage and production freshness SLA remain unresolved. The raw report preserves these distinctions.

# ASSUMPTIONS

The listed category sets are provisional observed vocabularies, not approved normalization mappings. `final_status` is stripped and lowercased only in memory for the delivered-completion check. The run date is logical, and source timestamp dates are compared to it without assigning a timezone.

# LIMITATIONS

Phase 2 reports data fitness; it does not publish a clean cohort, repair source values or calculate business metrics. Because source times lack an approved timezone, cross-source timing conclusions need that contract. A same-date extraction replaces prior raw output before validation; stronger publication transaction is deferred.

# MANUAL ACTION REQUIRED

None to reproduce Phase 2. An operational owner must eventually resolve the conflicts and semantic contracts before later publication.

# BLOCKERS

No implementation blocker. The observed FAIL checks block downstream modelling/KPI publication under this contract.

# QUESTIONS FOR ORCHESTRATOR

Who owns resolution of the three conflicting order IDs and five impossible milestone rows? What exclusion/repair provenance is acceptable? Approve the timezone and source freshness contract, and decide whether driver arrival should be instrumented before attributing delay to restaurant versus driver stage.

# PROPOSED PHASE 3

Only after separate authorization, address approved conflict/eligibility rules and build a one-row-per-order workflow model. Keep child event aggregation and metrics out of Phase 2.
