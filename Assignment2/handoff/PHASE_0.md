# STATUS

Phase 0 analysis/documentation complete; awaiting orchestrator review. No Phase 1 implementation. Business contracts remain proposals.

# FILES CREATED OR CHANGED

- `docs/source_audit.md`
- `docs/business_question_map.md`
- `docs/proposed_architecture.md`
- `docs/proposed_validation_contracts.md`
- `docs/proposed_metrics.md`
- `handoff/PHASE_0.md`

# REPOSITORIES INSPECTED

- Local `refrence/flasheats-classroom-pack`: READMEs, manifests, four available notebooks, SQL schema/data, relevant CSV/JSON inputs and mock API source.
- Local `refrence/flasheats-data-pipeline/Class8_Project` only: README, configuration, requirements, runner, pipeline modules, readiness/troubleshooting documents.
- Supplied attachment, `refrence/LECTURE_CONTEXT.md` and two-page `refrence/FDE_Assignment2.pdf`.
- No web browsing, clones, instructor-repository writes or inspection of `.git`.

# COMMANDS RUN

- PowerShell `Get-ChildItem` for targeted directory/file listings; `rg --files` with relevant extensions and excluded metadata/environments; `Get-Content` for selected instructions/source/configuration.
- `Get-Command` and Python availability checks: `python` missing from PATH; `py` reported no installed Python.
- Located existing bundled runtime through its manifest. Used `C:/Users/vimal/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -B -` with inline, in-memory profiling: SQLite `mode=ro`, schema/count queries, pandas counts/types/nulls/keys/timing, small samples and targeted joins; JSON notebook-cell inspection and pypdf extraction. Initial PDF output hit console encoding error; rerun with UTF-8 succeeded. PDF reader reported repaired object-offset warnings.
- Applied Markdown-only patches and ran a final bounded file/heading/content check. No packages installed, pipeline/notebook executed, data artifacts produced or tests added.

# SOURCE INVENTORY SUMMARY

SQL orders plus customer/driver/restaurant entities; support and restaurant status CSVs; nested driver JSON; dispatch API/backing JSON; app actions, mixed interactions, interventions, compiled events and derived outcomes. Proposed backbone is one row per order; aggregate all 1:N children before joins. Source-specific authority is proposed, not formally documented.

# IMPORTANT OBSERVED DATA FACTS

- 1,603 order rows / 1,600 IDs; all three repeated orders conflict on traffic. No exact duplicate order rows.
- Diagnostic classroom-style cohort: 68 cancelled, 37 delivered missing completion, 1,495 measurable, 843 late (56.388%); median late delay 8.027 minutes versus lecture ~7.9. Not an approved lifecycle-clean cohort.
- Four promises precede creation; five deliveries precede pickup. Three order restaurant links and three driver links are missing.
- Telemetry contains no restaurant-arrival event, but has 3,639 GPS pings between recorded pickup/delivery, contradicting the lecture gist. It records completion for 37 SQL-missing orders.
- Dispatch versus SQL current-driver differences: 95. App-action rows: 2,365; intervention rows: 430; mixed interactions reuse three IDs across different orders/types.
- One exact duplicate ticket, three unlinked tickets; two exact duplicate status rows. Complaint median changes from ~14.11 to ~14.78 minutes when category trimming changes the matched cohort.
- Compiled events and intervention CSV differ in vocabulary/counts; do not combine them without lineage.

# DECISIONS PROPOSED

Small Python pipeline; SQL + files + API retrieval; order-grain journey; five candidate outcome/workflow/interaction/intervention metrics; raw evidence and explicit contracts; strict machine-readable metrics/validation; logs, nonzero failure exit, repeatable logical-date output and consistent publication manifest. All remain documentation proposals.

# KNOWN

Assignment requires at least two retrieval modes, 3-5 metrics and a repeatable pipeline. Local student notebooks contain substantial TODOs. Class 8 demonstrates useful patterns but only its CSV write is atomic; its metrics, duplicate handling and retrieval/cardinality checks need adaptation.

# UNKNOWN

Canonical KPI owner, threshold/refund policy, timezone, source SLAs, conflict precedence, event-export lineage and capture completeness. Full source mappings are in `docs/source_audit.md`.

# ASSUMPTIONS

Proposed source ownership follows business object and inspected fields, pending confirmation. Keep-first deduplication was used only to compare lecture checkpoints, not approved for production. Historical snapshots are treated as historical evidence, not live operational truth.

# LIMITATIONS

No observed restaurant arrival means no defensible separation of driver travel-to-restaurant and waiting/preparation. Intervention associations are not causal effects. API code/backing data were inspected without live HTTP execution; Class 8 was reviewed statically to avoid generated writes. Referenced Class 6 solution and Class 7 concept notebooks are absent. No automated evaluator contract beyond the supplied brief is available.

# MANUAL ACTION REQUIRED

None to complete Phase 0. No installation or repository download is needed for this review.

# BLOCKERS

No blocker to documentation completion. Official metric publication and implementation choices depending on unresolved business meaning must await orchestrator decisions below.

# QUESTIONS FOR ORCHESTRATOR

1. Who owns the KPI, and should late mean >0 or >10 minutes? What population/refund policy is approved given missing refund evidence?
2. How should conflicting order traffic values and reused mixed-interaction IDs be handled? No reliable version/precedence field was found.
3. May telemetry completion fill SQL gaps, or should those 37 orders remain unmeasurable? Which driver field owns historical versus current assignment?
4. What timezone, lifecycle exclusion policy and category aliases are approved, especially `handoff` versus `handed_off` and `ETA issue` versus `eta_changed`?
5. Can app actions and intervention CSVs be the canonical child sources, leaving overlapping exports as reconciliation evidence? What are their capture windows/completeness guarantees?
6. How should pre-creation and post-delivery actions/interventions be classified, and what freshness SLA applies to this historical snapshot?
7. How should source snapshots/mock API be distributed for clean-clone evaluation? Confirm the proposed five metrics and the exact next-phase scope before implementation.

# PROPOSED PHASE 1

Orchestrator to define and authorize the next phase after reviewing source authority, metric/validation contracts and source-distribution choice. Suggested first scope: approved project skeleton and selected-source extraction with completeness/raw-preservation evidence. This is a proposal only; no Phase 1 files or code exist.
