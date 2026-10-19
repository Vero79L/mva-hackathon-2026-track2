PRIMARY: A repurposed medicine for BUB1B-related mosaic variegated aneuploidy earns its next experiment only if it acts on the measured bottleneck (residual BubR1 abundance and checkpoint function) in the compensating direction, passes this patient's four constraint gates — oncology, pediatric path and renal can reject, growth only flags — with every safety axis the gates cannot see declared rather than counted as clear, and rests on an approved product with a dated label; under that rule the single named candidate is niacin (nicotinic acid), an approved NAD+ precursor acting through the SIRT2–BubR1 stabilization axis, carried as a conditional research hypothesis rather than a recommendation and with its oncology axis contradictory and its growth axis unassessed, and it is overturned if NAD+ repletion in patient-derived cells fails to raise BubR1 protein or to correct the checkpoint defect, or improves the survival of aneuploid cells.

# The three required components

This one sentence is quoted verbatim in docs/REPORT.md (§1) and docs/PITCH.md; `make_manifest.py` blocks a submission if any copy drifts.

## 1. The decision rule
A repurposing hypothesis earns its next experiment only when all four hold:
1. **Direction** — its net effect is in the compensating direction for the characterized defect (for checkpoint insufficiency: strengthen the checkpoint / raise functional BubR1), never a mitotic or checkpoint inhibitor.
2. **Mechanism contact with the measured bottleneck** — it acts on residual BubR1 abundance or checkpoint function, the quantity the decisive experiment measures, not on a distal correlate.
3. **Four patient constraint gates, and an honest account of what they can and cannot see** — oncology, pediatric path and renal can reject a candidate; growth only raises a flag, so "four hard gates" would overstate it. The gates read a candidate's `properties[]` tags, so an axis assessed as *contradictory* or *not assessed* with no matching tag passes the gate without the gate ever seeing it. Rather than add a tag after the fact — that is rule-fitting — the engine computes those gate-silent axes and `build_views.py` refuses to build unless the canonical entry declares exactly them (`safety_gap_declared`). For niacin they are oncology (contradictory) and growth (not assessed).
4. **An approved product with a dated label** — eligibility is a property of a product (molecule × form/route × jurisdiction × indication × age range × status × date), not of a molecule.

## 2. The single named candidate
**Niacin (nicotinic acid)**, an approved prescription NAD+ precursor, acting through NAD+ → SIRT2 deacetylation of BubR1-K668 → BubR1 stabilization. Carried as a **conditional research hypothesis for follow-up, not a recommendation and not evidence that it works**. It is conditional, not supported: no NAD+ booster has been tested in an MVA model or in cells of this allele class; there is no pediatric label; the oncology direction is unresolved. It holds only under scenario S1 (a stabilizable hypomorph).

## 3. What overturns it
Any one of these negative results in patient-derived cells rejects the candidate:
- NAD+ repletion does not raise total BubR1 protein (or K668 acetylation), or
- the spindle-assembly checkpoint defect does not recover even if BubR1 abundance rises (scenario S2), or
- the aneuploid fraction of the surviving population, or the clonal dominance of an aneuploid lineage, increases — measured as a fraction of the population, not as raw survival, since a real checkpoint rescue can raise overall survival, or
- a truncated BubR1 product is present and rises with NAD+ repletion (scenario S3), which pauses every abundance-raising strategy.
