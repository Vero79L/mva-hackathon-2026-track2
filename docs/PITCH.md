# 3-minute pitch script — MVA Track 2 (v2.0)

*Target 2:55 spoken. On screen: report PDF pages, a live `./run.sh` / `--selftest` terminal, the three-scenario table, and the safety-annex decision table. Nothing identifying appears — say "the proband", never any coordinate, genotype, HPO term, sample name, or phenotype detail. The 0:20–0:50 segment shows the PRIMARY sentence on screen verbatim (below) so the video and report match; the consistency gate (`make_manifest.py`) checks this string appears here and in the report word-for-word.*

**On-screen caption, 0:20–0:50 (verbatim; the speaker reads the clauses, the full sentence is displayed):**

> PRIMARY: A repurposed medicine for BUB1B-related mosaic variegated aneuploidy earns its next experiment only if it acts on the measured bottleneck (residual BubR1 abundance and checkpoint function) in the compensating direction, passes this patient's four constraint gates — oncology, pediatric path and renal can reject, growth only flags — with every safety axis the gates cannot see declared rather than counted as clear, and rests on an approved product with a dated label; under that rule the single named candidate is niacin (nicotinic acid), an approved NAD+ precursor acting through the SIRT2–BubR1 stabilization axis, carried as a conditional research hypothesis rather than a recommendation and with its oncology axis contradictory and its growth axis unassessed, and it is overturned if NAD+ repletion in patient-derived cells fails to raise BubR1 protein or to correct the checkpoint defect, or improves the survival of aneuploid cells.

**0:00–0:20 — The problem, and the decision we actually made.**
This child has biallelic BUB1B: a weak spindle-assembly checkpoint, mosaic aneuploidy, and a lifelong cancer risk. The useful question is not "which drug" — it's whether *any* repurposing hypothesis is strong enough to earn the next experiment. So our deliverable is a decision rule, and one named candidate that the rule picks out.

**0:20–0:50 — The rule (quote the primary hypothesis).**
Our rule: a repurposed medicine earns its next experiment only if it acts on the measured bottleneck — residual BubR1 abundance and checkpoint function — in the compensating direction, passes this patient's four constraint gates — oncology, pediatric and renal can reject, growth only flags — with every safety axis those gates *cannot* see declared rather than counted as clear, and rests on an approved product with a dated label. Under that rule the single named candidate is niacin — an approved NAD+ precursor acting through the SIRT2–BubR1 axis — carried as a conditional research hypothesis, not a recommendation; and it's overturned if NAD+ repletion in the child's cells fails to raise BubR1 or fix the checkpoint, or helps aneuploid cells survive.

**0:50–1:15 — The mechanism, characterized.**
Loss-of-function, not gain: a truncating allele and a kinase-domain missense allele leave too little functional BubR1, the checkpoint slips, and cells missegregate. The lever is real and measured in mice and cells: NAD+ lets SIRT2 keep BubR1 deacetylated at K668 and stable; a SIRT2 transgene extends the lifespan of BubR1-low mice. In adults, niacin raised blood NAD+ up to eight-fold.

**1:15–1:45 — Why niacin, and why only conditional.**
Of the molecules on the strongest-biology axis, niacin is the one that is an approved prescription product — NMN and NR are supplements, and nicotinamide runs the wrong way. That is a claim about our eligibility matrix on a dated check, not about the world. But every caveat is on the table: it's never been tested with niacin in MVA or in cells of this allele class, there's no pediatric label, and the tumour direction is unresolved because NAD+ can fuel cancers — so our own engine prints niacin's oncology and growth axes as gate-silent, and it can never reach the top tier. That's why we name it conditional — and why we demoted our own earlier lead, 4-PBA, once its mechanism turned out to be secretory, not a BubR1 chaperone.

**1:45–2:15 — The decisive experiment, which is also diagnostic.**
One experiment decides it. In the proband's own cells: titrate NAD+ precursors, and read BubR1 abundance and K668 acetylation, checkpoint recovery, and the aneuploidy rate — while measuring cell death and clonal fitness in the same wells, so we never mistake "killed the bad cells" for "repair." The same measurement places residual BubR1 on the dose–phenotype map, so it's diagnostic for this child whatever we decide about the drug.

**2:15–2:40 — The honest result, and the care team.**
The strongest mechanistic target has no approved drug — we report that gap as a finding, not hide it. And because MVA kids face real treatment decisions now, we ship a care-team safety annex: which drug classes behave differently when the checkpoint is already weak, drawn from the mechanism and the published MVA case reports.

**2:40–2:55 — Scalability.**
The engine is case-driven and input-validating — unknowns block instead of passing — and the same rule runs across every MVA gene in one decision table. A new disease is one case file. The output isn't the longest drug list; it's the hypothesis that survives being wrong.
