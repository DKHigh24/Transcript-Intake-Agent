# Skill: Classify Opportunity

Classify each candidate into the AI Acceleration MVP schema.

Use config/choice_values.json for allowed values.
Use config/mvp_output_schema.json for the expected structure.

Rules:
- Prefer Classification unless the item clearly creates, updates, triggers, sends, automates, or changes a system.
- Use Both when the workflow both interprets information and produces an output or action.
- Default CurrentStatus to "(2) Needs Review".
- Default HumanReviewRequired to true.
- Default HumanInTheLoopRequired to true.
- Default PrimaryDataSource to "Meeting Transcript".
- Default ScheduleHealth to "Not Started".
- Do not invent owners.
- Use suggested owner text fields when person fields are not part of MVP.
- Preserve source speaker, timestamp, and evidence summary.
- Use "Unknown / Needs Review" when uncertain.

MaturitySignal rules:
- Select the single best value from: Aspirational, In Progress / Piloting, Delivered / Active Today, Unknown
- Use the verbatim EvidenceSummary phrase to detect the signal:
  - **Aspirational**: "we should", "what if", "I'd love to see", "has anyone tried", "we need to build",
    "could we", "imagine if", future-tense proposals with no delivery confirmation
  - **In Progress / Piloting**: "we're currently", "we started", "proof of concept", "in evaluation",
    "we're testing", "we have a pilot", "we're exploring", "we're experimenting"
  - **Delivered / Active Today**: "we're already using", "this is live", "we deployed", "it's running",
    "we built this", "this is working today", "we have this today", "it's in production"
  - **Unknown**: evidence is ambiguous, mixed, or contains no clear maturity indicator
- Default to "Unknown" when uncertain — never force a signal that isn't supported by the text.

SubOrdinateFunction rules:
- Select the single best value from config/choice_values.json "SubOrdinateFunction" list.
- Choose the most specific function that describes what is being automated or improved.
- Examples: "NPD - New Product Development" for new product pipeline work, "Quoting" for quote-generation, "Engineering Change Orders (ECO)" for design change processes, "Root Cause Analysis" for failure investigation.
- If no value clearly fits, use "Other / Not Classified".
- Leave blank ("") only if the opportunity is purely cross-cutting with no dominant subordinate function.

Return only valid JSON.
