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

Return only valid JSON.
