# 3-minute pitch script — MVA Track 2 (v2.0)

*Measured 2:52 spoken; the beat timings below are word counts at 2.6 words/second, which leaves 7 seconds of margin against the three-minute limit. That figure is not an assertion: `make_manifest.py` recomputes it from this file, blocks above 2:54, and blocks if the number written in this sentence disagrees with what it computes. On screen: report PDF pages, a live `./run.sh` / `--selftest` terminal, the three-scenario table, and the safety-annex decision table. Nothing identifying appears — say "the proband", never any coordinate, genotype, HPO term, sample name, or phenotype detail. The 0:19–0:50 segment shows the PRIMARY sentence on screen verbatim (below) so the video and report match; the consistency gate (`make_manifest.py`) checks this string appears here and in the report word-for-word.*

**On-screen caption, 0:19–0:50 (verbatim; the speaker reads the clauses, the full sentence is displayed):**

> PRIMARY: A repurposed medicine for BUB1B-related mosaic variegated aneuploidy earns its next experiment only if it acts in the compensating direction on the bottleneck the decisive experiment is built to measure — residual BubR1 abundance and checkpoint function, both of which are UNKNOWN in this child — passes this patient's constraint gates with every safety axis those gates cannot see declared rather than counted as clear, and rests on an approved product with a dated label. Under that rule the single named candidate is niacin (nicotinic acid), an approved NAD+ precursor acting through the SIRT2–BubR1 stabilization axis, carried as a conditional research hypothesis and not a recommendation: its oncology axis is contradictory and its growth axis unassessed. It is overturned if NAD+ repletion in patient-derived cells fails to raise BubR1 protein, fails to correct the checkpoint defect, or raises the aneuploid fraction of the surviving population — a fraction, never raw survival, because a real checkpoint rescue can raise overall survival.

**0:00–0:19 — The problem, and the decision we actually made.**
This child has biallelic BUB1B. The checkpoint runs weak, cells end up with wrong chromosome counts, and the cancer risk never leaves. We could have built a longer list. We asked a harder question. Is any hypothesis here worth one real experiment? So we wrote the rule first.

**0:19–0:50 — The rule.** *(full PRIMARY sentence on screen; speak only this)*
A medicine earns its next experiment only if it pushes the bottleneck we measure, residual BubR1, in the compensating direction. That amount is unknown, and we say so. It has to clear this patient's gates, with the risks those gates cannot see declared rather than assumed. And it has to be approved with a dated label. One candidate gets through. Niacin, conditional, not a recommendation. It dies if NAD+ repletion fails to lift BubR1, or lifts the aneuploid fraction.

**0:50–1:12 — The mechanism.**
So why BubR1? Because the defect is loss of function. A truncating allele and a kinase-domain missense allele leave too little working BubR1. The checkpoint slips, chromosomes go to the wrong cells. NAD+ lets SIRT2 keep BubR1 deacetylated and stable. A SIRT2 transgene extends the life of BubR1-low mice. In adults, niacin raised blood NAD+ eightfold.

**1:12–1:39 — Why niacin, and why only conditional.**
That eightfold is why niacin. It is the one approved prescription product there. NMN and NR are supplements. Nicotinamide runs backwards. But it has never been tested in MVA, or in this allele class. No paediatric label, and the tumour direction is unresolved. Our engine prints its oncology and growth axes as gate-silent, so it can never reach the top tier. The same discipline retired our earlier lead, 4-PBA.

**1:39–2:08 — The decisive experiment, which is also diagnostic.**
If mechanism retires a candidate, mechanism has to confirm one. The experiment is staged so different failures look different. Did NAD+ actually move inside the cells? If not, the problem is delivery. Does the K668-acetylated fraction fall, and does knocking SIRT2 down abolish that? Does function recover? Throughout, absolute counts and clonal fate, so killing sick cells never reads as repair. Whatever happens to the drug, this is the first functional characterisation of his BubR1.

**2:08–2:29 — The honest result, and the care team.**
Now the part we would rather not report. The strongest mechanistic target in the module has no approved drug. We report that gap as a finding. Because MVA families make treatment decisions now, not after our experiment, we ship a safety annex for a care team, pointed at the surveillance consensus naming MVA.

**2:29–2:56 — Scalability, and one test of the engine itself.**
That leaves the engine, which we attacked rather than vouch for. Unknown inputs block rather than pass quietly, and one table runs this rule across every MVA gene. Another disease is one case file. Blind the names and shuffle all seventeen candidates, and no verdict moves. Switch off any one safety gate, and niacin still cannot climb above conditional. The only perturbation that retires it goes after the biology.
