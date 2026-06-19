## MODIFIED Requirements

### Requirement: Extractor preserves maturity-signal language in evidence
The extraction skill (skills/extract_opportunities.md) SHALL instruct the LLM to preserve
the speaker's exact phrasing in `EvidenceSummary`, with particular attention to maturity-
signal language (delivery confirmations, piloting phrases, or aspirational proposals).

The extractor SHALL NOT itself classify maturity — it only captures the verbatim phrase
that will later allow the classifier to infer `MaturitySignal`.

#### Scenario: Delivery confirmation preserved in evidence
- **WHEN** a speaker says "we already have this working in our department"
- **THEN** the extractor SHALL include that exact phrase or a close paraphrase in
  `EvidenceSummary` so the classifier can detect the `Delivered / Active Today` signal

#### Scenario: Aspirational language preserved in evidence
- **WHEN** a speaker says "I'd love to see us build something that..."
- **THEN** `EvidenceSummary` SHALL reflect the future/aspirational framing rather than
  rephrasing it as a present-tense statement
