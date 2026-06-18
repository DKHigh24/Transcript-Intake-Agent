# Skill: Presentation Slide Content Generator

Generate concise, professional PowerPoint slide content for the Electronics AI Working Group weekly meeting.

## Purpose
Given the most recent session's AI opportunity data and session number, produce structured content
for three key slides in the upcoming session deck.

## Response format
Return ONLY valid JSON with this exact structure — no explanation, no markdown fences:
```
{
  "aligned_on": ["bullet 1", "bullet 2", ...],
  "agenda_items": ["item 1", "item 2", ...],
  "near_term_asks": ["ask 1", "ask 2", ...]
}
```

## Content rules

### aligned_on (4–6 bullets)
- Summarize what was discussed or decided in the PRIOR session
- Reference specific opportunities, tools, owners, or patterns when the data supports it
- Keep each bullet under 18 words
- Describe outcomes and decisions, not just topics
- Use past tense ("We aligned on...", "Identified...", "Confirmed...")

### agenda_items (6–8 items)
- List topics for the UPCOMING session
- Use action-oriented language ("Demo:", "Review:", "Align on:")
- Include a placeholder for the demo presenter
- Include KB article review and ownership alignment
- Use present/imperative tense

### near_term_asks (3–4 asks)
- Specific, actionable requests for all participants
- Each ask should be < 15 words
- Reference concrete actions: submit, identify, review, confirm

## Style
- Professional business tone
- Concise — bullets are talking points, not paragraphs
- Use first-person plural ("We aligned on...") only for aligned_on
- Do not repeat the same content across sections
