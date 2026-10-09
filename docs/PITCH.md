# 3-minute pitch script — MVA Track 2

**0:00–0:25 — The problem and the decision.** This child has biallelic BUB1B — a broken
spindle-assembly checkpoint, aneuploidy, and a rhabdomyosarcoma history. The decision is
not "which drug", but whether any repurposing hypothesis is strong enough to earn the next
experiment. We built a screen whose output is a decision rule, not a drug list.

**0:25–0:55 — Why the obvious search fails and what we hold fixed.** Databases rank mitotic
and checkpoint inhibitors first — the disease's own direction. We fix the therapeutic
objective to accurate chromosome segregation, apply directionality and four patient
constraints as hard gates, and validate every input so unknowns block instead of passing.

**0:55–1:20 — The screen result.** From one canonical candidate table — ten entries, one
denominator — no candidate reaches clinical support. We demoted our own earlier lead
(4-PBA) once its mechanism turned out to be secretory, not a cytosolic chaperone, and its
achievable exposure overlapped its HDAC-inhibitory range.

**1:20–2:05 — The surviving set and the named primary.** After verifying what is actually
an approved medication, the strongest biology — raising BUBR1 via SIRT2 — has no approved
drug. Among approved, pediatric-feasible options the single most defensible candidate is
glycerol phenylbutyrate, aimed at stabilizing the patient's residual BUBR1. We name it as a
research hypothesis, not a recommendation: its mechanism is contested, and one experiment
decides it. Backup is N-acetylcysteine as downstream mitigation.

**2:05–2:40 — The decisive experiment.** First characterize N1002K — abundance and
function — because that single measurement tells us whether a rescuable protein exists.
Then test the surviving candidate within a justified exposure range, separating restored
fidelity from cell death and from selection of surviving clones, with a clonal-fitness arm.

**2:40–3:00 — Reproducibility and reuse.** The engine runs clean from pinned dependencies,
passes its regression tests, and is case-driven: a new case file changes the gate logic.
We kept the counter-evidence that reducing instability can, in some models, favor tumors —
so the screen rewards hypotheses that survive being wrong, not the longest drug list.
