## ADDED Requirements

### Requirement: Generate upcoming session PPTX from opportunity history
The system SHALL generate a PowerPoint deck for the next session date using opportunity history and LLM-derived slide content, matching the established Acuity brand and slide structure.

#### Scenario: Presentation generated
- **WHEN** a weekly run completes with opportunity history available
- **THEN** the system SHALL write `output/meeting_presentations/Session_<N>_<YYYY-MM-DD>.pptx` with at least 10 slides

### Requirement: Match established slide structure
The generated presentation SHALL follow the consistent slide order used in Sessions 2–5: Title → Confidential → Agenda → What We Aligned On → Demo Backlog → Demo placeholder → KB Article Candidates → Next Steps.

#### Scenario: Slide order correct
- **WHEN** a presentation is generated
- **THEN** slides SHALL appear in the established order with correct titles

### Requirement: Use LLM for slide content with data fallback
The system SHALL attempt to use the configured LLM backend to generate aligned-on bullets, agenda items, and near-term asks. If the LLM call fails, the system SHALL fall back to data-derived bullets from opportunity history.

#### Scenario: LLM content generated
- **WHEN** the LLM is available and returns valid slide content
- **THEN** the presentation SHALL use LLM-generated bullets for aligned-on and next steps slides

#### Scenario: LLM unavailable — fallback applied
- **WHEN** the LLM call raises an exception
- **THEN** the system SHALL log a warning and populate slides from opportunity history data without halting

### Requirement: Handle file-lock gracefully
The system SHALL detect when the target PPTX file is open in another application and SHALL save to a timestamped alternate filename rather than failing.

#### Scenario: Target file locked
- **WHEN** `prs.save()` raises a `PermissionError`
- **THEN** the system SHALL save to `Session_<N>_<date>_<timestamp>.pptx` and log the alternate path

### Requirement: Auto-run on every weekly pipeline execution
The system SHALL automatically generate the upcoming presentation as the final step of every `--mode weekly` and `--mode rebuild` pipeline run.

#### Scenario: Presentation auto-generated
- **WHEN** `--mode weekly` or `--mode rebuild` completes
- **THEN** the presentation generation step SHALL execute without requiring a separate command
