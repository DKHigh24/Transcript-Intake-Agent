## ADDED Requirements

### Requirement: Read DOCX transcript
The system SHALL read a `.docx` meeting transcript file and extract all paragraph text in document order.

#### Scenario: Valid DOCX file
- **WHEN** a valid `.docx` path is provided
- **THEN** the system SHALL return all non-empty paragraphs as an ordered list

#### Scenario: Missing file
- **WHEN** the provided path does not exist
- **THEN** the system SHALL raise an error and halt the pipeline

### Requirement: Clean transcript text
The system SHALL normalize transcript text by removing formatting artifacts, collapsing whitespace, and standardizing speaker labels.

#### Scenario: Cleaning applied
- **WHEN** raw paragraphs are passed to the cleaner
- **THEN** the system SHALL return paragraphs with consistent whitespace, no leading/trailing spaces, and no empty entries

### Requirement: Split into speaker turns
The system SHALL parse cleaned paragraphs into discrete speaker turns, each attributed to a named speaker.

#### Scenario: Speaker turn parsed
- **WHEN** a paragraph begins with a recognized speaker label pattern
- **THEN** the system SHALL assign that paragraph and subsequent non-labeled lines to that speaker

### Requirement: Keyword filter turns
The system SHALL filter speaker turns to retain only those containing terms relevant to AI opportunities.

#### Scenario: Relevant turn retained
- **WHEN** a speaker turn contains a keyword from the configured AI opportunity keyword list
- **THEN** the turn SHALL be included in the filtered set

#### Scenario: Irrelevant turn excluded
- **WHEN** a speaker turn contains no matching keywords
- **THEN** the turn SHALL be excluded from chunking

### Requirement: Pack turns into LLM-safe chunks
The system SHALL pack filtered turns into chunks not exceeding `MAX_CHUNK_CHARS` characters, and SHALL split any single turn that exceeds `MAX_CHUNK_CHARS` on sentence boundaries.

#### Scenario: Normal packing
- **WHEN** multiple turns fit within `MAX_CHUNK_CHARS`
- **THEN** they SHALL be packed into a single chunk

#### Scenario: Oversized single turn
- **WHEN** a single speaker turn exceeds `MAX_CHUNK_CHARS`
- **THEN** the system SHALL split it into multiple sub-chunks at sentence boundaries, each within the limit

### Requirement: Persist chunks to disk
The system SHALL write the final chunk list to `output/transcript_chunks.json` with character count and turn count metadata per chunk.

#### Scenario: Chunks saved
- **WHEN** chunking completes successfully
- **THEN** `output/transcript_chunks.json` SHALL exist and contain at least one chunk object with `text`, `char_count`, and `turn_count` fields
