## Why

The pipeline currently has no structured change management — modifications to extraction logic, classification schema, prompt skills, and report formats happen ad hoc with no traceable artifacts. OpenSpec is already present in the repo but unused; activating it gives the working group an auditable, spec-first workflow for evolving the pipeline over time without breaking the running prototype.

## What Changes

- Populate `openspec/config.yaml` with project context so all future OpenSpec artifacts are grounded in this pipeline's domain
- Establish `openspec/specs/` with baseline capability specs for the four core pipeline capabilities
- Adopt a convention: any change to `src/`, `skills/`, or `config/` is preceded by an OpenSpec change artifact
- Add `openspec/changes/` as the canonical location for in-flight and archived change specs
- Document the OpenSpec workflow in the Operating Procedure manual

## Capabilities

### New Capabilities

- `transcript-ingestion`: Reading, cleaning, chunking, and keyword-filtering DOCX transcripts into LLM-safe chunks
- `opportunity-extraction`: LLM-driven extraction and deduplication of AI opportunity candidates from transcript chunks
- `opportunity-classification`: LLM-driven classification of candidates into the SharePoint MVP schema with validation
- `trend-reporting`: Aggregating classified rows into weekly and monthly HTML trend reports with longitudinal history
- `meeting-presentation`: Auto-generating the upcoming session PPTX from opportunity history and LLM-derived slide content

### Modified Capabilities

<!-- None — this is initial baseline spec creation, not a requirement change -->

## Impact

- `openspec/config.yaml`: Updated with pipeline project context
- `openspec/specs/`: New directory with five capability spec files
- `Operating Procedure/operating_manual.html`: New section on OpenSpec change workflow
- No changes to `src/`, `skills/`, `config/`, or any pipeline execution path
