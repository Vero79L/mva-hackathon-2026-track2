# Methods and AI provenance

## Data handling
Raw genomic/clinical data were accessed under the challenge's gated terms and kept in a
controlled local environment (chmod 700, not synced, not committed). Only derived,
rules-permitted facts (HPO terms, the variant list at protein level, mechanism analysis,
candidate lists, code) appear in public materials. Variant coordinates were looked up from
ClinVar/literature and matched locally against the VCF; no patient variant data was sent to
any external service. Deletion of raw data within 30 days of Hackathon close is scheduled;
the deletion-execution record and confirmation email (to both cnb@sagebase.org and
RarediseaserealkidMVAhackathon2026@synapse.org) are drafted and pending the deadline
(owner: submitter).

## Data boundary — what reached an AI assistant, stated as it actually happened

We previously drafted this section as a clean "nothing beyond derived data ever reached an AI".
That was not accurate, and the accurate version is also compliant, so here is the accurate version.

- **Routinely provided** (derived, rules-permitted): HPO terms, protein-level variant
  representations (c./p. HGVS), the gene name, transcript identifiers, mechanism text, code, and
  public literature.
- **No raw data file was ever opened by an AI tool.** No VCF, BAM, CRAM, FASTQ or clinical source
  file was read by any assistant. Every pipeline step that reads patient data ran as a plain
  script started by the participant in her own terminal; in Track 1, Claude Code additionally ran
  under user-level deny rules and an OS sandbox covering the controlled folders.
- **Coordinate-level content did reach an assistant conversation, on two occasions we can identify:**
  (1) In Track 1, after the pipeline had finished, the participant pasted terminal output of the
  completed runs into the Claude Code conversation; this exposed candidate-level results including
  genomic coordinates and HGVS, gene-level ranks, the VCF sample identifier and inferred sex. This
  is disclosed in the Track 1 methods document, section 7, in the same terms.
  (2) In Track 2, during an internal audit of the working registers on 2026-10-19, a row of an
  early working evidence ledger containing genomic coordinates and a genotype field appeared in
  tool output read by the assistant. That file has since been excluded by construction from every
  generated artefact, and the generator that builds the published claim ledger refuses to emit any
  row matching a coordinate or genotype pattern.

**Why we disclose rather than minimise.** The organizers' final guidance permits a consumer tier
for patient-specific or derived information when model training is disabled and no feedback is
given — both of which hold here. Nothing above required a cleaner boundary than we had, so there
was never a reason to describe one. A statement that a panel can check against our own Track 1
document, and find consistent, is worth more than a tidier claim that does not survive comparison.

The three-layer model still describes our *intent* (tier 1 no patient data → any login; tier 2
derived, public-safe → the tier declared below; tier 3 raw coordinates/genotypes → local terminal
only), and keeping tier-3 files off every AI system is a data-minimisation choice rather than a
rule requirement. The two exposures above are where practice departed from that intent.

## Scientific method
Mechanism-first: the disease mechanism and therapeutic objective were frozen before
candidate reasoning. Candidates passed a directionality prerequisite and four patient
constraints (oncology / pediatric / renal / growth). Each lead was then sent to an
independent adversarial review instructed to refute it. A single-standard re-score removed
survivorship bias. Load-bearing citations were put through an independent verification pass;
corrections are logged in the evidence ledger. `registers/claim_ledger.csv` carries a per-claim `reviewed_by` column, populated **only** from
`registers/claim_signoff.csv` — a file a human edits. A claim nobody has signed off stays blank, and
the release manifest reports the unsigned count and blocks on it under `--freeze`.

We record two corrections here rather than quietly fixing them. This paragraph first described a
sign-off sheet the generated ledger had no column for. The column was then added — but the generator
stamped every row with the same "human adjudication" string, which proves nothing: it is exactly the
self-certification we criticise the hard gates for elsewhere in this report, and an external audit
caught it. The generator no longer writes that field at all. As of this writing the honest number is
**0 of 36 claims individually signed off**: the ledger can prove where each claim came from, and it
cannot prove that a person has read each one. The candidate set lives in one
canonical table (`candidates_canonical.json`) from which the engine fixture and all tables
are generated.

## Method validation (independent self-test against VEP)

Transcript-level facts (c./p. positions, consequence class, exon/intron number, strand,
transcript version, NMD call, distances) are computed twice by independent routes: **method A**
is Ensembl VEP 116 offline with its matching cache, and **method B** is our own arithmetic over
the Ensembl 116 GTF plus the reference sequence. Every fact used in the report must agree
between the two, and a disagreement blocks the pipeline rather than being resolved silently.

Before touching the case variants, method B is calibrated against **400 public ClinVar
pathogenic/likely-pathogenic variants** (SNVs and short indels, both strands, fixed random seed,
reproducible) — 1,320 variant x MANE-transcript pairs, each compared across eleven fields. The gate is
>= 99% of pairs agreeing on every applicable field.

The first run scored 98.4% (1,299/1,320) and **failed the gate**. Diagnosis: 20 of the 21 failures were
in one field, `distance`, and all 20 were multi-base variants upstream of a transcript; the 21st is the
residual `protein_first_changed` disagreement described below, which the fix did not touch. Our code was
reporting the distance from the first base of the variant *in transcription direction* — which is
the correct base for the c. position, but on the far edge for an upstream variant — whereas VEP
measures from the edge **nearest** the transcript. Downstream variants happened to be correct on
both strands, which is why single-point tests had not caught it. The error equals the variant's
span length, so SNVs were unaffected. Fixed (nearest-edge rule) and pinned with two regression
tests covering all four strand x direction combinations; the synthetic test suite went from 57 to
59 tests, and the new test is verified to fail against the pre-fix code. Any residual
disagreement after the rerun is listed field-by-field in the self-test report and carried as a
known, bounded limitation rather than suppressed.

We report this because it is the point of the self-test: a two-method cross-check that only ever
agrees is not evidence of anything. The concordance figure quoted in the report is the post-fix
rerun, not the first attempt.

Post-fix rerun (2026-10-19, VEP 116 offline, Ensembl 116 GTF, 400 ClinVar variants, seed fixed):

| Field | agree | disagree |
|---|---|---|
| c_position | 410 | 0 |
| consequence_class | 1296 | 0 |
| distance | 910 | 0 |
| exon_number | 361 | 0 |
| frameshift_ter_n | 92 | 0 |
| intron_number | 49 | 0 |
| protein_alt_aa | 158 | 0 |
| protein_first_changed | 333 | 1 |
| strand | 1320 | 0 |
| synonymous | 20 | 0 |
| transcript_version | 1320 | 0 |
| **pairs agreeing on every field** | **1,319 / 1,320 = 99.9%** | |

One residual disagreement remains, in `protein_first_changed` (333/334). It is carried as a known
limitation rather than suppressed; it does not involve a single-nucleotide substitution, which is
the class both case variants belong to.

**Read the denominator carefully, because two of these fields cannot disagree.** The headline 99.9%
counts variant x transcript *pairs*: 1,319 of 1,320 pairs agreed on every field that applied to them.
Counted instead as individual field comparisons the table holds 6,270 of them, 6,269 agreeing
(99.98%) — but `strand` and `transcript_version` contribute 2,640 of those and are identical by
construction, so quoting the field-level figure would flatter the method. The field that actually
discriminates is `protein_first_changed`, at 333/334, and that is the number to judge the
cross-check by. We state all three rather than the most favourable one.

The same two-method cross-check is then applied to the case variants themselves, and every field
must agree before a fact enters the report (both variants passed: 6/6 and 7/7 checks).

## AI usage (provider / tier / data-handling), per organizers' final guidance (#2, ~Sep 29)
- **Provider / tier / setting:** Claude Max (claude.ai and Claude Code), training opt-out
  enabled in account settings, no feedback (thumbs) provided on any output; Anthropic
  Consumer Terms. A second provider (OpenAI, ChatGPT/Codex) was used for independent review
  under the same no-feedback, training-off handling.
- **Permitted use:** the organizers' final guidance (Community #2, confirmed #21) permits a
  consumer tier (e.g. Claude Max) for patient-specific or derived information when (1)
  model-training is disabled in account settings and (2) no feedback is given on outputs and
  content is not flagged into safety review. This submission meets both conditions; settings
  evidence (account screenshot, dated) is archived in `registers/ai_usage_evidence/` (not in
  the public repo) and is available on request.
- **Inputs to AI were limited** to derived, non-genotype-scale information (see Data boundary
  above); no raw genotype-level FILE was ever opened by an AI system; see the data-boundary section above for the two occasions on which coordinate-level content nevertheless reached a conversation.
- **Safety-classifier events (disclosed):** **two** responses were interrupted by the provider's
  safety classifier — one in a literature-only session (2026-10-14..18) and one on 2026-10-19
  while summarising tool output. Neither session contained genotype-level data, and no feedback
  was given on any output. Both are logged in `registers/ai_usage_register.csv`, and the count
  here is kept identical to the count there. Disclosing them is consistent with condition (2)
  above: an interruption is not a content flag against the submission, and we would rather the
  organizers see it from us.
- **Human adjudication:** AI conclusions were reviewed and reconciled by a human; items not
  signed off are marked "pending human confirmation"; AI agents are not treated as
  independent evidence. Discovery, falsification, and citation-audit ran as separate contexts.

## Reproducibility
`run.sh` executes the self-test, generates all views from the canonical source, runs the real
and synthetic cases and the three residual-function scenarios, and ends with
`make_manifest.py` (the consistency gate: the denominator, the verbatim PRIMARY sentence, unfilled
slots, five counts recomputed from their source files, the safety-classifier cross-check and the
deliverable hashes), all from pinned dependencies in a clean environment. Twenty-eight regression self-tests pin the gate logic: five cover the scenario-aware objective gate
that makes the three scenarios give different answers, six cover malformed scenario blocks, and five
run against this patient's own constraint levels so that the gates' reject, require and flag branches
are exercised rather than assumed. The engine demonstrates gate logic only; scientific judgment is in the canonical
table and the report, not in the code.
