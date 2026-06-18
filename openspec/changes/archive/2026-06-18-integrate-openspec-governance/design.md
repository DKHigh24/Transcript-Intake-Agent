## Context

The Transcript Intake Agent is a running Python pipeline that processes weekly meeting transcripts from the Electronics AI Working Group and produces classified AI opportunity rows, trend reports, and meeting presentations. The repo contains an `openspec/` directory with a minimal `config.yaml` stub but no active use of the OpenSpec framework.

The pipeline evolves regularly — new skills, schema changes, chunking logic fixes, and report format updates have all been made ad hoc. There is no structured way to propose, review, or trace these changes.

## Goals / Non-Goals

**Goals:**
- Activate OpenSpec as the change governance layer for all future pipeline modifications
- Establish baseline capability specs so future delta specs have a foundation to build on
- Configure `openspec/config.yaml` so AI-assisted artifact generation is grounded in pipeline context
- Keep the pipeline fully operational throughout — zero disruption to `--mode weekly` execution

**Non-Goals:**
- Automating OpenSpec artifact generation as part of the pipeline run (future work)
- Integrating OpenSpec with SharePoint or Power Automate at this time
- Retroactively writing change specs for past modifications

## Decisions

**1. Use `openspec/specs/` for baseline capability specs**
Each of the five pipeline capabilities (transcript ingestion, extraction, classification, trend reporting, presentation generation) gets a `spec.md` in its own subdirectory. This gives future delta specs a named target to reference.

*Alternative considered:* A single monolithic `pipeline-spec.md`. Rejected — too coarse for targeted delta specs when only one stage changes.

**2. Update `openspec/config.yaml` with pipeline domain context**
The config drives what AI tools see when generating OpenSpec artifacts. Adding the tech stack (Python, python-pptx, Copilot SDK), domain (AI opportunity tracking), and key constraints (no full transcript to LLM, draft-only output, human review required) ensures generated specs reflect actual constraints.

**3. Document the OpenSpec workflow in the Operating Procedure**
A new section in `Operating Procedure/operating_manual.html` explains when to create a change, how to run the CLI commands, and what artifacts are required before implementation. This makes the workflow accessible to non-developers on the working group.

**4. No changes to `src/` in this change**
This change is purely additive — config, specs, and docs only. The pipeline execution path is untouched.

## Risks / Trade-offs

- **Risk: Spec drift** — Baseline specs could fall out of sync with actual code as the pipeline evolves without a spec update.  
  → Mitigation: Each future change that modifies a capability is required to include a delta spec for that capability.

- **Risk: Workflow adoption friction** — Developers may skip the spec step under time pressure.  
  → Mitigation: Keep the spec authoring fast (CLI + AI assist). The barrier is low enough that one-liner changes can be proposed in under 5 minutes.

- **Trade-off: Lightweight specs over exhaustive ones** — Baseline specs describe behavior and contracts, not implementation. This keeps them durable as implementation details change.

## Migration Plan

1. Update `openspec/config.yaml` with project context
2. Create `openspec/specs/<capability>/spec.md` for each of the five capabilities
3. Add OpenSpec workflow section to the operating manual
4. This change serves as the first complete OpenSpec change artifact in the repo — demonstrating the workflow end-to-end

No rollback needed — all additions are inert to the pipeline runtime.

## Open Questions

- Should `input/presentations/` reference decks be spec'd as a dependency of the presentation capability, or treated as runtime data only? (Recommend: runtime data — no spec needed)
