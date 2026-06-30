# Workstream-Specific Process Stages and Relationship Model

## Why this is needed

The current taxonomy is strong for transactional opportunities, but it compresses engineering and product vitality work into labels that do not reflect how that work actually moves. This creates two issues:

1. `ProcessStage` behaves like a single transactional pipeline for all work.
2. `SubOrdinateFunction` is implicitly treated as stage-bound, even though the same function can appear in multiple workstreams and multiple stages.

This reduces classification precision and makes cross-functional recommendation logic weaker.

## Directional model

### 1) Separate lifecycle from flow

- Keep `WorkstreamType` as the lifecycle context (Transactional, Product Vitality, Governance, Support).
- Evolve stage modeling so each workstream can have its own stage vocabulary.

### 2) Make subordinate function orthogonal

- `SubOrdinateFunction` should be selected independent of a single stage pipeline.
- Validation should ensure function compatibility rules by workstream, not hard stage coupling.

### 3) Add relationship layer

Introduce explicit links between opportunities so the system can represent:
- Upstream/downstream dependencies
- Parallel contributing efforts across teams
- Governance items enabling product vitality or transactional execution

## Proposed ProcessStage set for Engineering / Product Vitality (ADO PI/Sprint aligned)

This is a recommended future stage model for opportunities classified as:
- `OperatingBucket = Engineering / Product Vitality`
- `WorkstreamType = Product Vitality`

It is designed for teams planning by Program Increment (PI) and executing by Sprint in Azure DevOps.

1. **Intake and Framing**  
   Problem is clear enough to size and route to the correct product/engineering group.
2. **PI Candidate and Sizing**  
   Candidate work is scoped, dependencies identified, and rough effort/value sizing exists.
3. **PI Committed**  
   Work is accepted into a PI objective/backlog with ownership and target outcomes.
4. **Sprint Ready**  
   Stories/tasks are refined with acceptance criteria and are ready for sprint pull.
5. **In Sprint Execution**  
   Work is actively being implemented/tested in one or more sprints.
6. **Validation and Adoption**  
   Outcome is validated (quality/performance/usability), rollout behavior is observed, and enablement/support artifacts are prepared.
7. **Closed Loop Improvement**  
   Work is delivered and measured; follow-on improvements are captured as linked opportunities.

Recommended ADO alignment:
- PI-level stages: `PI Candidate and Sizing`, `PI Committed`
- Sprint-level stages: `Sprint Ready`, `In Sprint Execution`
- Value-realization stages: `Validation and Adoption`, `Closed Loop Improvement`

This should remain separate from ADO state (`To Do`, `Doing`, `Done`), which tracks execution status, while `ProcessStage` tracks lifecycle position for product vitality work.

## Staged execution plan

### Stage 1 - Config and schema foundation (next)

1. Add `config/workstream_stage_map.json`:
   - Allowed stage sets per `WorkstreamType`
   - Optional alias normalization per stage
2. Add optional relationship fields to schema:
   - `RelatedOpportunityIDs` (array)
   - `RelationshipType` (choice; e.g., Enables, Depends On, Blocks, Feeds, Duplicates)
3. Update validator:
   - Validate `ProcessStage` against `WorkstreamType`-specific allowed values
   - Keep backward-compatible alias handling for existing historical rows

### Stage 2 - Classification guidance and review UX

1. Update classifier prompt/skills:
   - Select stages from the active workstream stage set
   - Treat `SubOrdinateFunction` as cross-stage
2. Update review surfaces:
   - Show recommended related opportunities
   - Allow reviewer edits for relationship fields

### Stage 3 - Relationship graph and recommendations

1. Build deterministic relationship inference (rule-first, no auto-merge):
   - Shared entities, repeated pain points, handoff cues, dependency language
2. Add report views:
   - Cross-functional relationship matrix
   - Dependency chains and bottleneck hotspots
3. Add recommendation engine output:
   - "If you pursue X, these 2 upstream efforts should be aligned first."

## Recommended execution order

Execute Stage 1 first (low risk, high leverage), then Stage 2, then Stage 3.

This sequence preserves existing behavior while enabling better precision and a practical path to true cross-functional recommendation quality.
