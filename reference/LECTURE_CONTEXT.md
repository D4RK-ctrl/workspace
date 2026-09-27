[LECTURE CONTEXT GIST — Class 1: FDE Mindset and Stakeholder Discovery]
Core Concepts:
- Forward Deployed Engineer (FDE) vs. Traditional Software Engineer (SWE) & Solutions Engineer (SE).
- The Builder's Trap: Jumping to technical architectures (RAG, Chatbots, Agents) before diagnosing the root-cause business problem.
- Macro AI Market Shift: The decline of generic, one-size-fits-all B2B SaaS vs. hyper-custom AI-driven solutions adapted to unique client data, workflows, and constraints.
- The Discovery Ladder: Client Request (hypothesis) -> User Pain -> Operational Workflow -> Business Impact -> Empirical Evidence -> Real Root Problem.
- Stakeholder Mapping: Triangulating 6 organizational roles (VP/Outcome Owner, Managers, Users/Reps, CRM/Data Owners, Upstream Marketing, IT/Security Blockers).
- Claimed vs. Actual Workflow: The divergence between theoretical management processes and messy, frontline shadow-IT realities.
- The FDE Execution Loop: Listen -> Observe -> Question -> Structure -> Validate (KPIs) -> Build -> Measure -> Iterate.
- First Rule of Discovery: "Are you ready to build? Not yet."

Important Definitions:
- FDE: An embedded, client-facing software and AI engineer who owns customer business outcomes end-to-end.
- KPI (Key Performance Indicator): The primary quantifiable scorecard metric used to measure business success/failure.
- CRM (Customer Relationship Management): The core operational customer database (e.g., Salesforce, HubSpot).
- RevOps (Revenue Operations): The technical team managing software pipelines, CRM data schemas, and sales tooling.
- Discovery Ladder: The systematic process of peeling back human assumptions to reach empirical operational bottlenecks.

Key Tools & Frameworks Introduced:
- Stakeholder Matrix Room Map.
- Claimed vs. Actual Workflow Diagramming.
- The Discovery Interview technique: "Show me what happened with the very last customer."
- The 5 Discovery Note Buckets: Facts, Assumptions, Unknowns, Stakeholders, Problem Interpretation.

Future Dependencies:
- Class 2 (Shruti Sagar) directly depends on this session to take the unorganized discovery data and formalize it into structured computational Workflow Maps.
- Class 3 directly builds on the KPI and Discovery Ladder rungs to define formal Project Scope Boundaries and quantitative baseline contracts.

[LECTURE CONTEXT GIST — Class 2]
Core Concepts:
- The FDE Discovery Loop: "Don't build the request. Discover the problem."
- Anti-Patterns: The CID Loop (repeating symptoms) and Knee-Jerk Levers (pulling price/cost levers blindly).
- The Locked Room / 1,000 Keys Analogy: Why brute force fails at scale; the necessity of context observation and mechanical filtering.
- The ASSUME Rule: "Never assume; it makes an ASS of U and ME." Clients omit constraints due to the Curse of Knowledge.
- 8-Step Problem Solving Framework (Steps 1–4 covered in Class 2; Steps 5–8 in Class 3).
- Step 1: S.M.A.R.T. Problem Definition (Specific, Measurable, Actionable, Realistic, Time-bound). Parable of the Blind Men & the Elephant (zooming out to see systemic reality).
- Step 2: Logic Trees (Issue Trees for Day-1 zero context vs. Hypothesis Trees for Day-5+ solution testing). Must be M.E.C.E. (Mutually Exclusive, Collectively Exhaustive). Set Theory 2x2.
- Step 3: Prioritizing Issues via 2x2 Matrix (Impact vs. Feasibility). Focusing strictly on P0 (High Impact, High Feasibility) to avoid "boiling the ocean."
- Step 4: Planning Analyses via the 6-Column Engine (Issue, Hypothesis, Analysis, Sources of Insight, End Product, Timeline/Owner).

Important Case Studies Analyzed:
- E-Commerce Checkout Drop (S.M.A.R.T. framing: reducing 68% cart abandonment by 18% in 6 weeks without changing gateway).
- Rameshwaram Café Revenue Stagnation (Diagnosing Level-0 External Macro/Competition vs. Internal Ops/Pricing).
- Mars Refrigerator Light Bulb Puzzle (Deconstructing problems into physical first principles: Emits Light, Generates Heat, Consumes Electricity).
- Tracking-Page 42% Drop-off Funnel (Populating a full Analysis Plan across Customer Behavior, UX, and Backend Latency).

Future Dependencies:
- Class 3 directly builds on Step 4's Analysis Plan to cover Steps 5–8: Conducting quantitative/qualitative analyses, Synthesizing insights via "So What?", crafting actionable recommendations, establishing Leading vs. Lagging KPIs, and presenting to C-level executives using the Pyramid Principle.

[LECTURE CONTEXT GIST — Class 3]
Core Concepts:
- The 8-Step Problem Solving Framework completed: Conduct Analyses (Step 5), Synthesize via SCR / "So What?" (Step 6), Craft Recommendations (Step 7), and Executive Communication via Pyramid Principle (Step 8).
- Dual-Track Analysis: Combining Quantitative Data Segmentation ("Cuts" by device, geography, cohort) with Qualitative Human Shadowing & Journey Mapping.
- Cognitive Mind Traps: Confirmation Bias, Anchoring Bias, Availability Bias, Over-optimism Bias, and Escalation of Commitment / Sunk Cost Fallacy ("Not wrong to be wrong; wrong to be wrong for too long").
- KPI Architecture: Leading Indicators (agile, predictive early-warning test metrics measured over days in A/B cohorts) vs. Lagging Indicators (high-level scorecard business metrics confirmed over months).
- Case Study Mastered: Quick-commerce Warehouse Pick-and-Pack optimization (cutting fulfillment from 12 min to 6 min per order via barcode scanning pilots).
- Project Scoping Engine: The 8-field Project Scoping Worksheet (SMART question, Context, Constraints, Success Criteria, Scope boundaries, Stakeholders, Insights, Timeline).

Important Definitions:
- Leading Indicator: Predictive, fast-feedback metric used during pilot testing to catch failure early.
- Lagging Indicator: High-level business metric confirming ultimate ROI weeks or months later.
- Situation-Complication-Resolution (SCR): Structured 3-part narrative framework for synthesizing findings.
- The Pyramid Principle: Executive communication strategy that delivers the recommendation first before drilling into supporting data.
- Scope Creep: The uncontrolled expansion of project features and boundaries without adjustments to time, cost, or resources.

Future Dependencies:
- Phase 1 (Discovery & Scoping) concludes here.
- Phase 2 (Classes 4–8) begins next lecture with Manan Suri, transitioning from business discovery into hands-on Data Engineering: Client Data Schemas, SQL Data Extraction, APIs, Data Quality Profiling, and Dependable Pipelines.

[LECTURE CONTEXT GIST — Class 4]
Core Concepts:
- The Data Phase Kickoff: Transitioning from business discovery (Classes 1–3) to data architecture (Classes 4–8).
- The FDE Pipeline Law: "An FDE does not start by building the pipeline. First, they decide what truth the pipeline must carry."
- The Information Chain: Deconstructing problems backwards: Decision -> Question -> Information Need -> Field -> Source -> Owner.
- Data Shapes: Structured (SQL/CSV), Semi-Structured (APIs/JSON), Unstructured (PDF/Notes).
- System of Record (SoR): The authoritative system holding business ownership over an object's lifecycle.
- 4 Truth Criteria: Authority/Ownership, Freshness Cadence, Replication Lineage, Semantic Alignment.
- Core Trap: Freshness alone is not authority (newest timestamp != verified truth).
- Lean MVP Data: Ingesting minimal decision-critical fields vs. dangerous data hoarding.
- Workflow vs. Data Problems: Fixing missing join keys at the intake UI rather than writing brittle heuristic code.
- AI Feasibility Law: AI cannot predict operational labels that underlying systems fail to instrument.

Case Studies Analyzed:
- ShopKart: Dissecting "Where is my refund?" across 8 messy sources; resolving an 11:07 AM conflict between CRM, JSON, API, and Agent Notes; identifying missing customer_id join keys.
- FlashEats: Deconstructing 7 conflicting versions of late delivery reality; exposing the fatal absence of a driver_arrived_at_restaurant event; pivoting the client from naive AI prediction to operational instrumentation.

Future Dependencies:
- Class 5 directly relies on today's Source-of-Truth decisions to write extraction scripts in SQL, REST APIs, CSV, and JSON.

[LECTURE CONTEXT GIST — Class 5]
Core Concepts:
- Multi-Source Data Ingestion: Reconciling relational SQLite (orders), flat CSVs (tickets, restaurant statuses), nested JSON (driver telemetry), and REST APIs (dispatch service).
- Operational Data Profiling: Determining true data grain, removing duplicates (1603 -> 1600), excluding cancellations (68), and isolating missing timestamps (37).
- Defining the Late Delivery Baseline: Establishing that out of 1,495 valid completed deliveries, 843 were late (56.4% baseline late rate) with a 7.9-minute median delay.
- Hypothesis Testing & Segmentation: Using Pandas groupby/aggregations to test operational dimensions; proving traffic and heavy rain correlate with delays, whereas delivery distance does not.
- Perception vs. Reality: Merging support tickets via Left Join to verify customer complaints against system delays (validating that customers complaining of late delivery experienced a 14.1-minute median delay).
- Resilient API Ingestion: Building while-loops handling pagination, HTTP 500/429 retries with backoff, and preserving raw JSON responses on disk.
- Missing Milestone Problem: Discovering driver_events.json lacks a driver_arrived_at_restaurant event, leaving the system unable to separate kitchen prep time from driver transit time.
- Strategic FDE Recommendation: Advising the client to pause their AI model investment until tracking milestones and data logging issues are fixed.

Important Definitions:
- Data Grain: The atomic business reality represented by exactly one row in a dataset (e.g., 1 row = 1 unique customer order).
- Left Join: A database merge keeping all records from the primary focus table (left) while pulling in matching attributes from a secondary table (right).
- Observed Fact vs. Inferred Estimate: An observed fact is explicitly recorded by a system timestamp; an inferred estimate is a guess derived from secondary signals like GPS pings.
- Exponential/Linear Backoff: Pausing ingestion scripts between retries to allow struggling APIs to recover.

Key Code & Tools:
- SQLite (`sqlite3`, `pd.read_sql`), Pandas (`pd.to_datetime`, `errors='coerce'`, `drop_duplicates`, `groupby().agg()`, `pd.merge()`, `pd.cut()`), Flask/Requests mock API ingestion loop.

Future Dependencies:
- Class 6 directly builds on this multi-source dataset to define formal Data Validation Gates (PASS/WARN/FAIL contracts) and resolve semantic discrepancies across stakeholder metric definitions.

[LECTURE CONTEXT GIST — Class 6]
Core Concepts:
- FDE Data Validation Mindset: Profiling data to judge fitness for business decisions rather than cleaning columns to look pretty.
- 3-Pillar Validation Taxonomy: Structural Rules (physical bounds), Lifecycle Rules (event chronology), and Cross-Source Rules (join coverage).
- The Ghost Mile Telemetry Gap: Driver events lack GPS pings between pickup and delivery, rendering transit-delay AI impossible.
- The KPI Definition War: Deconstructing the "56% Late" metric; VP Ops (>0 min delay) vs Support (>10 min delay) vs Finance (cancelled orders excluded).
- The Validation Gate: Operational gatekeeper returning PASS, WARN, FAIL, or UNKNOWN.

Important Definitions:
- Validation Gate: An automated checkpoint verifying data against business contracts before publishing metrics or training models.
- Representation vs. Semantic Inconsistency: Typographical text differences (safe to lowercase) vs differing operational realities (requires owner clarification).
- Ghost Mile: Operational blind spot caused by uninstrumented field telemetry.

Key Tools & Code:
- Python/Pandas: `pd.to_numeric(errors='coerce')`, `pd.to_datetime()`, `drop_duplicates(keep='first')`, boolean masks for lifecycle chronology, `.isin().mean()` for join coverage.

Future Dependencies:
- Class 7 builds directly on today's validated schemas to model the relational business workflow (Entities, Events, States, Actions) and link operational metrics to financial outcomes.

[LECTURE CONTEXT GIST — Class 7: Modelling the Business Workflow with Data]
Core Concepts:
- Workflow Data Modeling: Reorganizing technical source silos (SQL, CSVs, APIs) around the real-world operational order lifecycle.
- 5 Core Building Blocks: Entities (Nouns/Things), Events (Timestamped Verbs), States (Conditions), Interventions (Human/Ops Rescues), Outcomes (Final Scorecards).
- The Fan-Out Trap & Data Grain: Joining 1:N event tables directly to orders duplicates rows and corrupts financial/operational metrics; child tables must be aggregated to 1 row per order_id before joining.
- Behavioral Friction Signals: High customer ETA_VIEWED counts act as leading indicators of delivery distress before complaints occur.
- Intervention Evaluation & Reverse Causality: Interventions often fail if applied too late; high late rates on intervened orders reflect selection bias (severe orders attract support), not support causing delay.
- Assignment 2 Briefing: Deliver a dependable data pipeline across Track A (FlashEats), Track B (NYC TLC Taxi), or Track C (Custom Operational Domain).

Important Definitions:
- Data Grain: What one single row represents in an analytical table (e.g., exactly 1 unique customer order).
- Fan-out: The multiplication of primary table rows when joining to an unaggregated one-to-many child table.
- Intervention: An active operational action taken to rescue an in-flight failing process (e.g., driver reassignment).

Key Tools/Code:
- Python/Pandas: `groupby('order_id').agg()`, `.merge(how='left')`, `.fillna(0)`, `pd.to_datetime()`, SQLite (`sqlite3`).

Future Dependencies:
- Class 8 builds directly on today's unified order_journey table to construct a reliable, dependable, and automated production data pipeline.

[Cureent Inputs - Lec 8]
- Please follow system instructions
- give notes in plain english and layman terms only
- I have also attached the repo on which sir worked throughout the lecture as no PPT was used for this lecture
- remember to make a good context for this lecture as that will be used to solve a assignment related to this lecture.

[LECTURE CONTEXT GIST — Class 8: Building a Simple, Dependable Data Pipeline]
Core Concepts:
- Production Data Engineering: Transitioning from interactive Jupyter analysis to automated, dependable pipelines.
- The 5 Core Pipeline Stages: Extract -> Validate -> Clean -> Transform -> Save (supported by structured Logging & Config).
- Repeatability vs. Dependability: Running code on new dates (repeatable) vs. gracefully handling system failures, missing columns, and duplicates (dependable).
- Configuration Decoupling: Separating immutable application behavior (code) from environment-specific variables (.env/config.py); enforcing secrets management via .gitignore.
- Automated Validation Gates: Hard checks (required_columns, freshness, retrieval) that fail fast, and soft checks (uniqueness, critical_nulls) that flag warnings for downstream cleaning.
- Smart Retry Strategy: Handling transient errors (HTTP 500, 429) using bounded exponential backoff and Retry-After headers, while failing fast on permanent issues (HTTP 400, schema breaks).
- Idempotency & Safe Storage: Partitioning data by logical run date, replacing partitions cleanly on reruns, and using atomic file swaps (os.replace) to prevent partial write corruption.
- Storage Layering (Medallion Pattern): Storing raw responses in Bronze partitions, cleaned datasets in Silver partitions (order_journey.csv), and business metrics in Gold partitions (metrics.json).

Key Tools/Code:
- Python, Pandas, Requests, Argparse, Dataclasses, os.replace, Tempfile, Mock REST API.

Future Dependencies:
- Phase 2 (Data Engineering) concludes here with Gate 2 Data Readiness.
- Phase 3 begins in Class 9, building operational wireframes and deploying AI agents directly on top of this validated, dependable pipeline.
