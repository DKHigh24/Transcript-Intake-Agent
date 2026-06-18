## ADDED Requirements

### Requirement: Send chunks to LLM for extraction
The system SHALL send each transcript chunk to the configured LLM backend with the extraction system prompt and return a list of candidate AI opportunities.

#### Scenario: Candidates returned
- **WHEN** the LLM responds with a valid JSON array of candidates
- **THEN** the system SHALL parse and return that array

#### Scenario: Empty chunk response
- **WHEN** the LLM returns an empty array `[]`
- **THEN** the system SHALL treat it as valid and contribute zero candidates from that chunk

#### Scenario: LLM failure on a chunk
- **WHEN** the LLM call raises an exception or returns unparseable output
- **THEN** the system SHALL log a warning and continue processing remaining chunks without halting

### Requirement: Never send full transcript to LLM
The system SHALL only send keyword-filtered, size-bounded chunks to the LLM — never the full raw transcript text.

#### Scenario: Full transcript blocked
- **WHEN** the pipeline runs in any mode
- **THEN** no single LLM call SHALL contain the entire transcript text

### Requirement: Deduplicate candidates by title
The system SHALL deduplicate extracted candidates by case-insensitive exact title match before persisting.

#### Scenario: Duplicate title removed
- **WHEN** two candidates share the same title (case-insensitive)
- **THEN** only the first occurrence SHALL be retained

### Requirement: Persist candidates to disk
The system SHALL write the deduplicated candidate list to `output/candidates.json`.

#### Scenario: Candidates saved
- **WHEN** extraction completes
- **THEN** `output/candidates.json` SHALL exist and contain a JSON array (empty array is valid if no candidates found)

### Requirement: Support pluggable LLM backends
The system SHALL support OpenAI (via `OPENAI_API_KEY`) and GitHub Copilot SDK (via `GITHUB_TOKEN`) as interchangeable backends, selected by environment configuration.

#### Scenario: OpenAI selected
- **WHEN** `OPENAI_API_KEY` is set in the environment
- **THEN** all LLM calls SHALL route through the OpenAI API

#### Scenario: Copilot SDK selected
- **WHEN** `OPENAI_API_KEY` is absent and `GITHUB_TOKEN` is set
- **THEN** all LLM calls SHALL route through the GitHub Copilot SDK using a fine-grained PAT
