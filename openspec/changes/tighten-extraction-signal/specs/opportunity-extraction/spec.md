## MODIFIED Requirements

### Requirement: Candidate substantiveness threshold
The extraction prompt SHALL require each candidate to meet all three of the following criteria before being emitted:
1. An actor (named speaker or implied team) is associated with the opportunity
2. A specific AI tool, technique, or domain is identified or strongly implied
3. At least one of: (a) active delivery confirmed in present tense, (b) active piloting/evaluation in progress, or (c) a concrete proposal with a plausible next step implied by the conversation

The prompt SHALL include an explicit exclusion list:
- Off-hand mentions with no elaboration ("we should try AI for that")
- Open-ended questions with no stated direction ("has anyone used X?")
- Purely aspirational statements with no specificity ("AI will transform everything")
- Restatements of an opportunity already captured in the same chunk

#### Scenario: Substantive candidate is extracted
- **WHEN** a speaker describes a specific AI tool they are actively using or piloting with named context
- **THEN** the extractor emits a candidate with Title, EvidenceSummary, and SourceSpeaker populated

#### Scenario: Off-hand mention is excluded
- **WHEN** a speaker makes an off-hand remark like "we should probably use AI for that someday" with no elaboration
- **THEN** the extractor does NOT emit a candidate for that remark

#### Scenario: Duplicate within same chunk is excluded
- **WHEN** the same idea is restated twice within the same chunk
- **THEN** only one candidate is emitted

### Requirement: Extraction count per chunk
The extraction prompt SHALL instruct the LLM to emit a maximum of 3 candidates per chunk. If more than 3 distinct, substantive opportunities are genuinely present in a single chunk, the extractor SHALL emit the 3 with the strongest evidence.

#### Scenario: Chunk with many weak mentions
- **WHEN** a chunk contains 5+ AI mentions but most are off-hand
- **THEN** the extractor emits ≤ 3 candidates, selecting only those meeting the substantiveness threshold

#### Scenario: Chunk with 2 strong opportunities
- **WHEN** a chunk clearly describes 2 distinct, substantive AI use cases
- **THEN** the extractor emits exactly 2 candidates
