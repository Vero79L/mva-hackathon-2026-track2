# Builder task sheet — Track 2 奪冠衝刺 (2026-10-19)

For the Claude Code "Builder" session running locally on Vero's Mac, in
`~/Claude-MyBrain-Professional/opportunity-quest/mva/research/engine`. Reply to Vero in
Traditional Chinese. Full plan: `mva track 2/specs/spec-final-sprint-v2.0.md`.

## Ground rules (unchanged)
- This is the Track-2 submission repo — the only folder that goes public. Work only here.
- Do **not** `git add .`. Commit only the files listed per the spec. Do not push, do not
  submit — Vero does both.
- Do not read or print `config/cases/bub1b_mva.yaml`, `evidence/candidates.yaml`, or anything
  under `~/mva-hackathon/{gated-data,work,results}`. `docs/REPORT.md` and the case files carry
  patient phenotype/clinical constraints — treat as masked, don't restate.
- Patient-derived steps (handoff 10, transcript 11) are Vero's own terminal only; see §3.
- Reply blocks for Vero's claude.ai log must contain no coordinate, genotype, or sample value.

## What the claude.ai session already placed in the repo on 2026-10-19 (uncommitted)
These are staged into the repo from the cloud session. Your job is to **verify**, not rewrite:
- `src/triage.py` — Spec 0 §2.1 fixes: `PROPERTY_SAFETY_GATE`, `safety_state()`,
  `safety_input_conflicts()`, and self-tests 9–12 (now 12 total).
- `build_views.py` — Spec 0 §2.2 raw-type validation (no coercion), fixture pass-through, the
  `C-NA` EXPL entry, and an optional product-level eligibility-matrix view.
- `make_manifest.py` — the four-way consistency gate (denominator, verbatim PRIMARY line,
  no unfilled `{{F-...}}`, SHA-256 of deliverables). Hooked into `run.sh`.
- `run.sh` — now also runs S1/S2/S3 scenario cases (if present) and `make_manifest.py`.
- `docs/candidates_canonical.json` — now 17 entries: added `C-NA` (niacin, ELIGIBLE,
  CONDITIONAL), revised `C-NAD` note (NMN/NR stay INELIGIBLE), `C-PBA` demoted to INSUFFICIENT
  with a dated note. `updated` = 2026-10-19.
- `docs/PRIMARY_HYPOTHESIS.md`, `docs/REPORT_v2.md`, `docs/SAFETY_ANNEX.md`,
  `docs/MVA_DECISION_TABLE.md`, `docs/PITCH_v2.md`, `docs/METHODS_AND_AI.md` (updated AI line).
- `docs/eligibility_matrix.csv` (public regulatory data, committed; read by `build_views.py` into `docs/eligibility_matrix.md`).

## WP1 — engine verification (today → 10/20 morning)
```bash
cd ~/Claude-MyBrain-Professional/opportunity-quest/mva/research/engine
. .venv/bin/activate 2>/dev/null || true
python3 src/triage.py --selftest          # expect 12 PASS, "ALL PASS"
python3 build_views.py                    # expect "Generated 4 views from 17 canonical entries"
# prove the type guard really blocks (should exit 1, message naming the string type):
python3 - <<'PY'
import json, pathlib, subprocess
src = pathlib.Path("docs/candidates_canonical.json"); bak = src.read_text()
d = json.loads(bak); d["candidates"][0]["engine_inputs"]["rescue_in_relevant_cells"] = "false"
src.write_text(json.dumps(d, indent=2, ensure_ascii=False))
rc = subprocess.run(["python3","build_views.py"]).returncode
src.write_text(bak); print("exit", rc, "(expect 1)")
PY
```
`./run.sh` will only fully pass once the three scenario case files and the filled
`docs/REPORT.md` / `docs/PITCH.md` exist (WP2, WP4). Until then it runs selftest + views +
real + synthetic and skips scenarios with a note; `make_manifest.py` will BLOCK on the
`{{F-...}}` slots and the missing PRIMARY line — that is expected and is the gate working.

## WP2 — Spec 1 bundle day2 (after Vero runs day1)
Vero installs the bundle and runs day1 (steps 00/11a/10/11/12) in her own terminal (§3). Once
`results/track2/handoff_from_track1.yaml` and the transcript facts exist, you run day2:
```bash
bash scripts/phase1/run_t2_phase1.sh day2        # 13 -> 14 (scenarios) -> 15 -> 16 -> 18 -> 19
```
Step 14 writes `config/cases/bub1b_mva_S1.yaml` / `_S2.yaml` / `_S3.yaml` and runs the engine
on each; copy the three verdict summaries into the report's `{{F-S1/S2/S3}}` slots (verdict
lists only, no patient values). Step 16 verifies every citation — including the per-gene
references in `MVA_DECISION_TABLE.md`; any row still marked `pending citation` stays out of
the final report until it passes.

Note: the bundle's `CLAUDE.md` §0 says a Pro/Max login does not qualify for patient data.
That predates the organizers' final guidance (#2, ~Sep 29), which permits a consumer tier
with training off and no feedback. Replace §0's tier table caveat with: "tier 2 derived,
public-safe → Claude Max with training opt-out and no feedback is permitted (organizers #2
final guidance); tier 3 raw coordinates/genotypes → local terminal only, as a
data-minimization choice." Do not weaken the tier-3 local-only rule.

## WP4 — reconcile and gate (10/21)
1. After Vero fills every `{{F-...}}` in `docs/REPORT_v2.md`, `mv docs/REPORT_v2.md
   docs/REPORT.md` and `mv docs/PITCH_v2.md docs/PITCH.md` (manifest expects those names).
2. Build `registers/claim_ledger.csv`: one row per result-bearing claim in the report, with
   `strength` matching the report's wording (measured/predicted/asserted) and an openable
   `source_url` + `source_locator`. Leave `counterevidence` = `searched_none_found` where a
   search found nothing. For every `global_negative` claim add a dated block to
   `registers/search_strategies.md`.
3. `python3 build_views.py && python3 make_manifest.py` — both clean. Fix the canonical
   source, never the generated files.

## WP5 — package (10/21 evening → 10/22)
```bash
python3 make_manifest.py && \
pandoc docs/REPORT.md -o docs/Vero7878_track2_report.pdf --pdf-engine=xelatex \
  -V mainfont="PingFang TC" -V geometry:margin=2cm -V fontsize=10.5pt --toc
grep -nioE '\\b(only (drug|option|candidate) (that|which|suitable)|uniquely|guarantee[sd]?|prove[sd]?|demonstrat(es|ed) efficacy|will (work|improve|rescue)|safe (and|for)|cheap experiment|definitiv[a-z]*)\\b' docs/REPORT.md docs/PITCH.md
```
Filename uses the HF username **Vero7878**. Every grep hit must map to a claim-ledger row with
`strength = measured`; otherwise soften the wording, not the source. If pandoc/xelatex is
missing: `brew install pandoc basictex`, or `python3 -m markdown docs/REPORT.md > /tmp/r.html`
and print to PDF from Safari.

## Commit (never push)
```bash
git add src build_views.py make_manifest.py run.sh \
  docs/REPORT.md docs/PITCH.md docs/PRIMARY_HYPOTHESIS.md docs/METHODS_AND_AI.md \
  docs/SAFETY_ANNEX.md docs/MVA_DECISION_TABLE.md docs/candidates_canonical.json \
  docs/candidate_table.md docs/candidate_table.html docs/computed_vs_human.md \
  docs/eligibility_matrix.csv docs/eligibility_matrix.md docs/Vero7878_track2_report.pdf \
  config/cases/bub1b_mva_S1.yaml config/cases/bub1b_mva_S2.yaml config/cases/bub1b_mva_S3.yaml \
  outputs/run.txt outputs/manifest.json outputs/REPRODUCIBILITY.md
# NOT: config/local.env, registers/*, results/*, docs/REPORT_v2.md, docs/PITCH_v2.md
git commit -m "Track 2 sprint: niacin named candidate, engine guards, manifest, safety annex, all-MVA table"
```
Run `python3 scripts/phase1/19_public_safety.py --all` before Vero pushes on 10/22.
