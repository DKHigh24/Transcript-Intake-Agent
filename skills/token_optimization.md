# Skill: Token Optimization

Rules:
- Do not process full transcripts when chunks are available.
- Use output/transcript_chunks.json instead of raw DOCX text.
- Classify one candidate at a time when possible.
- Do not repeat large schemas in every response.
- Use config files as source of truth.
- Keep output as compact JSON.
- Let Python handle formatting, validation, Excel export, and payload mapping.
- Avoid long chat history for repeated runs.
- Save intermediate files so failed steps can be rerun without restarting.
