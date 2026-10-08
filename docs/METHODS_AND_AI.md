# Methods and AI provenance

## Data handling
Raw genomic/clinical data were accessed under the challenge's gated terms and kept in a
controlled local environment (chmod 700, not synced, not committed). Only derived,
rules-permitted facts (HPO terms, the variant list at protein level, mechanism analysis,
candidate lists, code) appear in public materials. Variant coordinates were looked up from
ClinVar/literature and matched locally against the VCF; no patient variant data was sent to
any external service. Deletion of raw data within 30 days of hackathon close is scheduled,
with email confirmation to the organizers.

## Scientific method
Mechanism-first: the disease mechanism and therapeutic objective were frozen before
candidate reasoning. Candidates passed a directionality prerequisite and four patient
constraints (oncology / pediatric / renal / growth). Each lead was then sent to an
independent adversarial review instructed to refute it. A single-standard re-score removed
survivorship bias. All load-bearing citations were independently verified; corrections are
logged in the evidence ledger. The candidate set lives in one canonical table
(`candidates_canonical.json`) from which the engine fixture and all tables are generated.

## AI usage (provider / tier / data-handling)
- Provider: Anthropic (Claude Code, Max tier) for analysis, synthesis, code, and multi-agent
  adversarial review; a second provider (OpenAI Codex / ChatGPT) for independent review.
- Data-handling: model-training disabled per account setting; no feedback (thumbs up/down)
  on outputs; consumer/processor terms treated per the organizers' processor-vs-recipient
  guidance. Inputs to third-party AI were limited to derived, non-genotype-scale information
  (HPO terms, two public variant identifiers, mechanism text) — never raw genotype-scale data.
- Human adjudication: every AI conclusion was reviewed and reconciled by a human; conflicting
  agent outputs were adjudicated with the basis stated (see the P0 decision record). AI
  agents are not treated as independent evidence.
- Separation: discovery, falsification, and citation-audit ran as separate contexts.

## Reproducibility
`run.sh` executes the selftest plus the real and synthetic cases from pinned dependencies in
a clean environment. The engine demonstrates gate logic only; scientific judgment is in the
canonical table and the decision record, not in the code.
