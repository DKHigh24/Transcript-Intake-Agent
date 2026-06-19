# Skill: Extract AI Opportunities

Identify candidate AI opportunities from transcript chunks.

## Substantiveness Requirement

A candidate MUST meet ALL THREE of the following criteria before being emitted:

1. **Actor** — a named speaker or clearly implied team/role is associated with the opportunity
2. **Specific domain** — a specific AI tool, technique, or domain is identified or strongly implied (e.g., Copilot, Claude, a custom agent, a named workflow, a specific process)
3. **Maturity anchor** — at least ONE of:
   - Active delivery confirmed in present tense ("we already use", "this is live", "we built this")
   - Active piloting or evaluation in progress ("we're testing", "we have a pilot", "we started exploring")
   - A concrete proposal with a plausible next step implied by the surrounding conversation ("we should build X so that Y", "the plan is to automate Z")

## Explicit Exclusion List

Do NOT emit a candidate for any of the following:

- Off-hand mentions with no elaboration ("we should try AI for that", "AI will help here")
- Open-ended questions with no stated direction ("has anyone used X?", "I wonder if we could...")
- Purely aspirational statements with no specificity or actor ("AI will transform everything", "the future is AI")
- Restatements of an idea already captured in the same chunk — emit only once per distinct opportunity
- Greetings, agenda transitions, casual sidebar discussion
- Vague commentary without a process, owner, tool, or next step

## Per-Chunk Cap

Emit a **maximum of 3 candidates per chunk**. If more than 3 substantive opportunities are present, select the 3 with the strongest evidence (prefer Delivered > In Progress > Aspirational, then prefer the most specific).

## Evidence Summary Rules

- Preserve the speaker's EXACT phrasing in `evidence_summary`, especially maturity-signal language.
- Do NOT rephrase delivery confirmations ("we already have this running") as aspirational statements.
- Do NOT rephrase aspirational proposals ("I'd love to see us build...") as present-tense facts.
- The verbatim framing is critical — it will be used downstream to detect whether the opportunity is aspirational, in progress, or already delivered.

## Output

Return only valid JSON. Return an empty array `[]` if no candidates meet the substantiveness requirement.

[
  {
    "candidate_title": "",
    "candidate_summary": "",
    "source_speaker": "",
    "source_timestamp": "",
    "evidence_summary": "",
    "confidence": "High | Medium | Low"
  }
]
