## ADDED Requirements

### Requirement: Within-session candidate deduplication
After LLM extraction and before classification, the pipeline SHALL compare all candidate titles and evidence summaries within the same session using fuzzy string matching. Candidate pairs with a combined similarity ratio at or above `DEDUP_SIMILARITY_THRESHOLD` (default 0.72, configurable via `.env`) SHALL be merged: the candidate with the longer `EvidenceSummary` is retained and the other is discarded. Discarded candidates SHALL be logged at DEBUG level with their similarity score.

#### Scenario: Near-duplicate candidates from different chunks are merged
- **WHEN** two candidates from the same session have a title+evidence similarity ratio ≥ 0.72
- **THEN** the candidate with the shorter EvidenceSummary is discarded and the retained candidate proceeds to classification

#### Scenario: Distinct candidates are preserved
- **WHEN** two candidates from the same session have a similarity ratio < 0.72
- **THEN** both candidates proceed to classification unchanged

#### Scenario: Dedup threshold is configurable
- **WHEN** `DEDUP_SIMILARITY_THRESHOLD` is set in `.env`
- **THEN** the pipeline uses that value instead of the default 0.72

### Requirement: Session candidate count guardrail
After deduplication, if the remaining candidate count exceeds `MAX_CANDIDATES_PER_SESSION` (default 20, configurable via `.env`), the pipeline SHALL emit a warning log line and route the lowest-confidence candidates above the limit to the Triage sheet rather than blocking execution.

#### Scenario: Candidate count within limit
- **WHEN** post-dedup candidate count is ≤ MAX_CANDIDATES_PER_SESSION
- **THEN** all candidates proceed to classification normally with no warning

#### Scenario: Candidate count exceeds limit
- **WHEN** post-dedup candidate count exceeds MAX_CANDIDATES_PER_SESSION
- **THEN** the pipeline logs a `[warning]` line stating count and limit, and excess candidates (lowest confidence first) are routed to the Triage sheet
