# Track 2 engine — runbook for Claude Code (local, on Vero's Mac)

You are helping Vero run Phase 1 ("lock the scientific base") of Track 2 of the Rare Disease, Real Kid: MVA
Hackathon 2026. Reply to Vero in Traditional Chinese. The full plan is Spec 1 v1.1 in her filing folder
(`mva track 2/specs/spec1-science-base-v1.1.md`); this file is the short operating version.

## 0. Check the account before touching any patient-derived data

The organizers' **final** guidance (Community discussion #2, ~2026-09-29, confirmed in #21) permits a
consumer tier — including a Claude Pro or Max login — for patient-specific or derived information when
model training is disabled in account settings and no feedback is given on any output. Both conditions
hold for this work, and `docs/METHODS_AND_AI.md` declares exactly that.

An earlier revision of this section said the opposite: that patient data could be processed by an LLM
only under business / API terms, and that a Pro or Max login does not qualify. That was the organizers'
interim answer and it was superseded; it is corrected here rather than left in place, because a runbook
that contradicts the submission's own AI disclosure on the one compliance question that matters reads
as an admission instead of a record. **Tier 3 below stays local-terminal-only regardless.** That is a
data-minimisation choice this project keeps, not a rule it is forced into.

| Tier | Steps | What they read | Login |
|---|---|---|---|
| 1 · no patient data | `tests/phase1/run_tests.sh`, `00_preflight.sh`, `11a_selftest_clinvar.sh`, `16_verify_citations.py` | code, public reference data, public ClinVar, PMIDs/DOIs | any |
| 2 · derived, public-safe | `12`–`15`, `18`, `19` | `docs/` outputs (HGVS of the two variants, HPO terms, mechanism text), the fact register, the case file | Claude Max with training opt-out and no feedback is permitted (organizers' final guidance #2); Console (API) is still the cleaner route. Keep this file, `docs/METHODS_AND_AI.md` and `registers/ai_usage_register.csv` identical on what was actually used |
| 3 · raw | `10_handoff.py`, `11_transcript_facts.sh` | Track 1 submission CSV and VCF (coordinates, genotypes) | **Console (API) only**, or Vero runs them herself in Terminal |

1. Run `/status` first. Tier 3 needs a Claude Console (API) credential (an Anthropic profile or an API key).
2. With a claude.ai subscription login, do not run tier 3 and do not open or print files under
   `~/mva-hackathon/{gated-data,work,results}`. Ask Vero to run tier 3 in her own Terminal and paste back only the
   ✓ / ✗ lines (the scripts print no coordinates by design).
3. Never send the child's data anywhere else (no web tools, no uploads, no pastes into other services).
4. Never rate or give feedback (thumbs) on a response that contains patient-derived data.

## 1. Run order

Start Claude Code in this folder (`research/engine`). Use the mva conda environment's Python.

| Step | Command | Typical time |
|---|---|---|
| tests | `bash tests/phase1/run_tests.sh` (expect 77 tests OK) | 5 s |
| 00 | `bash scripts/phase1/00_preflight.sh` (no ✗ allowed) | 1 min |
| 11a | `bash scripts/phase1/11a_selftest_clinvar.sh` (≥ 99 % concordance) | 3–5 min |
| 10 | `python3 scripts/phase1/10_handoff.py --match full --rank-points 100 --f-max 1` | 1 min |
| 11 | `bash scripts/phase1/11_transcript_facts.sh` | 2–5 min |
| 12 | `python3 scripts/phase1/12_domain_map.py` | 1 min |
| 13 | `python3 scripts/phase1/13_check_register.py [--init]` | seconds |
| 14 | `python3 scripts/phase1/14_build_scenarios.py --run-engine [--init]` | seconds |
| 15 | `python3 scripts/phase1/15_mechanism_graph.py [--init]` | seconds |
| 16 | `python3 scripts/phase1/16_verify_citations.py --include-uniprot` | 1 min |
| 18 | `python3 scripts/phase1/18_case_provenance.py --run-engine` | seconds |
| 19 | `python3 scripts/phase1/19_public_safety.py` | seconds |

`bash scripts/phase1/run_t2_phase1.sh day1` and `day2` run these in order and stop at the first failure.

## 2. Scientific content is Vero's

The scripts compute and check; they do not decide. Do not fill `fact_register.csv`, the scenario table, the causal
chain or the therapeutic objectives with your own conclusions. Draft wording only when Vero asks, mark every draft
cell `pending`, and never upgrade a `predicted` fact to `CONFIRMED`. Never invent a PMID or DOI; every citation must
pass step 16 and Vero checks titles marked `manual` herself.

## 3. Git and data safety

- Outputs with coordinates live only in `$T2_RESULTS` (`~/mva-hackathon/results/track2`). Never copy them into this
  repo or into the iCloud-synced `Claude-MyBrain-Professional` tree.
- `fact_register.csv` and `citation_check.csv` live in `../registers/`, not in this repo.
- Commit only the files listed in Spec 1 section 10.3. Never `git add .`. The pre-commit guard runs
  `19_public_safety.py --staged`; don't bypass it with `--no-verify`.
- Don't push and don't submit to the competition. Vero does both.
- The old copy of the engine at `~/mva-hackathon/repo` (root `src/`, `config/cases/`) is stale: don't edit it.

## 4. When something fails

- Read the error and the newest log in `$T2_RESULTS/logs/`, fix the cause, rerun the same step.
- Cross-check failures in step 11: follow Spec 1 section 2.7 in order (versions → strand → indel shift → real
  disagreement). Do not "fix" a mismatch by editing the VEP output or the GTF.
- Script bugs: smallest fix in `scripts/phase1`, keep macOS bash 3.2 / BSD compatibility (no `sed -i`, `grep -P`,
  `readlink -f`, `declare -A`, `mapfile`), then rerun `bash tests/phase1/run_tests.sh`.

## 5. Report back

After each step, tell Vero in Traditional Chinese what ran, how long it took, and what is next. For her claude.ai
project log, write a block titled `Status for claude.ai` that contains only step names, pass / fail, tool versions,
run times and error messages with every coordinate, genotype and sample-level value removed.
