## 1. Configure OpenSpec Project Context

- [x] 1.1 Update `openspec/config.yaml` with pipeline domain context: tech stack (Python 3.14, python-pptx, Copilot SDK), domain (AI opportunity tracking for Electronics AI Working Group), key constraints (no full transcript to LLM, draft-only output, human review required before SharePoint push)

## 2. Publish Baseline Capability Specs

- [x] 2.1 Copy `openspec/changes/integrate-openspec-governance/specs/transcript-ingestion/spec.md` to `openspec/specs/transcript-ingestion/spec.md`
- [x] 2.2 Copy `openspec/changes/integrate-openspec-governance/specs/opportunity-extraction/spec.md` to `openspec/specs/opportunity-extraction/spec.md`
- [x] 2.3 Copy `openspec/changes/integrate-openspec-governance/specs/opportunity-classification/spec.md` to `openspec/specs/opportunity-classification/spec.md`
- [x] 2.4 Copy `openspec/changes/integrate-openspec-governance/specs/trend-reporting/spec.md` to `openspec/specs/trend-reporting/spec.md`
- [x] 2.5 Copy `openspec/changes/integrate-openspec-governance/specs/meeting-presentation/spec.md` to `openspec/specs/meeting-presentation/spec.md`

## 3. Update Operating Procedure

- [x] 3.1 Add an "OpenSpec Change Workflow" section to `Operating Procedure/operating_manual.html` covering: when to create a change, the four CLI commands (`openspec new change`, `openspec instructions`, `openspec status`, `/opsx:apply`), and the rule that all `src/`, `skills/`, and `config/` changes require a preceding spec
- [x] 3.2 Add a reference to `openspec/specs/` as the canonical location for current system behavior documentation

## 4. Verify Integration

- [x] 4.1 Run `openspec status --change "integrate-openspec-governance"` and confirm all artifacts show `done`
- [x] 4.2 Confirm pipeline still runs end-to-end: `.\.venv\Scripts\python.exe src\main.py --mode weekly --input <latest transcript>` completes with no errors
- [x] 4.3 Run `openspec new change "test-governance-check"` and confirm the new change inherits updated project context from `openspec/config.yaml`, then delete it
