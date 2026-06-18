# Skill: Extract AI Opportunities

Identify candidate AI opportunities from transcript chunks.

Extract candidates when the transcript describes:
- AI demos
- AI workflows
- Copilot, Claude, ChatGPT, agents, skills, prompts, or automations
- knowledge base candidates
- access, licensing, token, or governance issues
- reusable patterns
- survey themes that require action
- repeated manual work that AI could reduce

Do not extract:
- greetings
- agenda transitions
- casual discussion
- one-off comments without a workflow
- duplicate mentions of an already captured item
- vague AI commentary without a process, owner, tool, or next step

Evidence summary rules:
- Preserve the speaker's EXACT phrasing in `evidence_summary`, especially maturity-signal language.
- Do NOT rephrase delivery confirmations ("we already have this running") as aspirational statements.
- Do NOT rephrase aspirational proposals ("I'd love to see us build...") as present-tense facts.
- The verbatim framing is critical — it will be used downstream to detect whether the opportunity
  is aspirational, in progress, or already delivered.

Return only valid JSON.

Output:
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
