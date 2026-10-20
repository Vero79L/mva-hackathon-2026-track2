# 3-minute pitch script — MVA Track 2 (v2.0)

*Measured 2:53 spoken; the beat timings below are word counts at 2.6 words/second, which leaves seven seconds of margin against the three-minute limit. That figure is not an assertion: `make_manifest.py` recomputes it from this file, blocks above 2:54, and blocks if the number written in this sentence disagrees with what it computes. On screen: report PDF pages, a live `./run.sh` / `--selftest` terminal, the three-scenario table, and the safety-annex decision table. Nothing identifying appears — say "the proband", never any coordinate, genotype, HPO term, sample name, or phenotype detail. The 0:18–0:44 segment shows the PRIMARY sentence on screen verbatim (below) so the video and report match; the consistency gate (`make_manifest.py`) checks this string appears here and in the report word-for-word.*

**On-screen caption, 0:18–0:44 (verbatim; the speaker reads the clauses, the full sentence is displayed):**

> PRIMARY: A repurposed medicine for BUB1B-related mosaic variegated aneuploidy earns its next experiment only if it acts in the compensating direction on the bottleneck the decisive experiment is built to measure — residual BubR1 abundance and checkpoint function, both of which are UNKNOWN in this child — passes this patient's constraint gates with every safety axis those gates cannot see declared rather than counted as clear, and rests on an approved product with a dated label. Under that rule the single named candidate is niacin (nicotinic acid), an approved NAD+ precursor acting through the SIRT2–BubR1 stabilization axis, carried as a conditional research hypothesis and not a recommendation: its oncology axis is contradictory and its growth axis unassessed. It is overturned if NAD+ repletion in patient-derived cells fails to raise BubR1 protein, fails to correct the checkpoint defect, or raises the aneuploid fraction of the surviving population — a fraction, never raw survival, because a real checkpoint rescue can raise overall survival.

**0:00–0:18 — The problem, and the decision we actually made.**
This child has biallelic BUB1B: a weak spindle checkpoint, mosaic aneuploidy, lifelong cancer risk. The useful question isn't "which drug" — it's whether *any* repurposing hypothesis is strong enough to earn the next experiment. So we built a decision rule, and named the one candidate it picks out.

**0:18–0:44 — The rule.** *(full PRIMARY sentence on screen; speak only this)*
A medicine earns its next experiment only if it pushes the bottleneck we propose to measure — residual BubR1, unknown in this child — in the compensating direction, passes the patient's gates with every risk those gates *can't* see declared, and is an approved product with a dated label. One candidate survives: niacin — conditional, not recommended. It dies if NAD+ repletion fails to raise BubR1, or raises the aneuploid *fraction*.

**0:44–1:04 — The mechanism.**
Loss-of-function. A truncating allele plus a kinase-domain missense allele leave too little functional BubR1; the checkpoint slips; cells missegregate. The lever is measured in mice and cells: NAD+ lets SIRT2 keep BubR1 deacetylated and stable, and a SIRT2 transgene extends the lifespan of BubR1-low mice. In adults, niacin raised blood NAD+ eightfold.

**1:04–1:29 — Why niacin, and why only conditional.**
On that axis it's the one approved prescription product — NMN and NR are supplements, nicotinamide runs backwards. Every caveat is on the table: never tested in MVA or this allele class, no pediatric label, tumour direction unresolved. Our engine prints niacin's oncology and growth axes as gate-silent, so it can never reach the top tier. The same discipline retired our earlier lead, 4-PBA, on mechanism.

**1:29–2:02 — The decisive experiment, which is also diagnostic.**
One staged experiment decides it, staged so failures can be told apart. Did NAD+ actually move inside the cells? If not, that's delivery, not biology. Does the K668-acetylated *fraction* fall, and does knocking SIRT2 down abolish it? Does function recover? And throughout: absolute counts and clonal fate, so we never mistake killing the bad cells for repair. The same measurement is the first functional characterisation of this child's BubR1 — worth having whatever happens to the drug.

**2:02–2:22 — The honest result, and the care team.**
The strongest mechanistic target has no approved drug. We report that gap as a finding. And because MVA families face treatment decisions now, we ship a care-team safety annex — which drug classes behave differently when the checkpoint is already weak — pointed first at the published surveillance consensus that names MVA.

**2:22–2:55 — Scalability, and one test of the engine itself.**
The engine is case-driven: unknowns block rather than pass, and one table runs the same rule across every MVA gene — a new disease is one case file. And we perturbed it rather than vouch for it: blind and shuffle all seventeen candidates, no verdict moves; switch off any safety gate, niacin still cannot rise above conditional. The only perturbation that retires it is the one that attacks the biology.

The output isn't the longest drug list. It's the hypothesis built to survive being wrong.
