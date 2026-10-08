# A falsification-first repurposing screen for an MVA1 (BUB1B) patient
### MVA Hackathon 2026 — Track 2 (drug repurposing). Draft report, 2026-10-08.

## Executive decision
No screened candidate currently supports clinical use for this MVA1 patient, and there is no single clear leader. Under one consistent evidence standard, the reusable screen converts a broad candidate set into a small set of mechanism-plausible but unproven research branches, each with one unresolved risk and one decisive experiment. The most defensible primary hypothesis is **not a drug recommendation but a decision rule**: a repurposing hypothesis for this patient earns further development only by improving chromosome segregation at an achievable human exposure while being tested for adverse effects on abnormal-cell survival and growth. That rule survives a negative result for any individual candidate.

What would overturn the current disposition is stated per candidate below (each has a named decisive experiment).

## Patient basis — fact status separated
From the gated dataset (derived facts only; raw data held in a controlled environment):
- **CONFIRMED**: two BUB1B variants in the proband, both high-quality heterozygous — p.Leu737Ter (c.2210T>G, 15:40209701) and p.Asn1002Lys (c.3006T>G, 15:40220612); phenotype including a documented rhabdomyosarcoma history, nephrocalcinosis, growth restriction, prematurity.
- **ASSUMED**: phase (in trans) and the compound-heterozygous recessive model — the sample is a singleton with no parents and the variants are ~10.9 kb apart, so phase cannot be resolved here.
- **UNKNOWN**: N1002K functional consequence (stability vs function), L737X transcript fate (NMD predicted, not measured), residual BUBR1 function (carried as three scenarios), current malignancy status, current renal function.

Risk statements are classified as regulatory contraindication / known pharmacological risk / confirmed patient condition / team prudential rule. The oncology caution here is a prudential rule from a documented RMS history plus constitutional predisposition — not a claim of active malignancy or clinical contraindication.

## Mechanism and the therapeutic objective
Biallelic BUB1B reduces BUBR1 at the spindle-assembly checkpoint, weakening the delay of anaphase until kinetochores are correctly attached, which produces mis-segregation and mosaic aneuploidy. The BUBR1 pseudokinase domain promotes PP2A-B56 recruitment and checkpoint silencing (Gama Braga et al., Cell Reports 2020). The objective is therefore accurate chromosome segregation under appropriately regulated mitotic progression — not generic "more checkpoint." A direction that further weakens the checkpoint (MPS1/TTK, Aurora B, PLK1, KIF11 inhibitors) is the disease's own direction and serves only as a negative control.

## Candidate funnel (one denominator, generated from a single source)
All views derive from `candidates_canonical.json` via `build_views.py`: **5 interventions + 3 mechanism-branches + 2 negative-control groups = 10 entries.** Competition eligibility (ELIGIBLE / INELIGIBLE / UNKNOWN) is tracked separately from research judgment (SUPPORTED / CONDITIONAL / INSUFFICIENT / REJECTED).

| Branch / candidate | Eligibility | Research | Ev-dist | Why / decisive experiment |
|---|---|---|---|---|
| NAD+/SIRT2 (NMN/NR) | UNKNOWN | CONDITIONAL | 2 | On-mechanism (SIRT2-BubR1, North 2014), but NMN was tested in aging/WT/Sirt2-null contexts — not the MVA model; bridging hypothesis. Oncology direction contested. Test: NAD+ precursor in N1002K cells → BubR1-K668 acetylation + total BubR1 + aneuploidy + a clonal-fitness/transformation arm. |
| Readthrough of L737X | INELIGIBLE | CONDITIONAL | 2 | Product is near-full-length (old "truncated" reason withdrawn); blocked by predicted NMD and the absence of a renal-safe approved UGA agent. Test: allele-specific mRNA + full-length protein under NMD-inhibition / readthrough / combination with a SAC readout. |
| 4-PBA | ELIGIBLE | INSUFFICIENT | 1 | Mechanism is COPII/secretory (Ma & Goldberg 2017), not a cytosolic chaperone; achievable exposure overlaps the HDAC range; thresholds are not a measured N1002K ECx. Deprioritized ("rescue + exposure not established", not "no window proven"). Test: in-cell EC50 for N1002K stabilization vs HDAC readout. |
| NAC (downstream mitigation) | ELIGIBLE | CONDITIONAL | 2 | Rejected as a disease modifier (exposure); permitted as mitigation. Test: ROS + senescence markers + proliferative lifespan at achievable exposure. |
| AMPK deselection | UNKNOWN | CONDITIONAL | 3 | Tang 2011 is p53-RELATED (not independent); anti-proliferation is not repaired segregation; metformin limited by eGFR. Test: euploid-vs-aneuploid viability with a non-renal AMPK agent. |
| Dasatinib+Quercetin | ELIGIBLE | REJECTED | 1 | Acts downstream; the disease-model evidence is a genetic tool (INK-ATTAC), not the D+Q drug; endpoint mismatch + toxicity. |
| Folate+B12 | ELIGIBLE | INSUFFICIENT | 2 | Supportive/deficiency claim, not disease modification; oncology watch. |
| Rapamycin | ELIGIBLE | CONDITIONAL | 2 | Oncologic-protective axis only; the BubR1-model null is unpublished preliminary data (negative signal, not a powered experiment). |
| Mitotic/checkpoint inhibitors, proteasome, HSP90i | varies | REJECTED | 1 | Wrong direction (increase CIN) — negative controls. |
| Misc rejected (AICAR/17-AAG, HCQ, navitoclax, fisetin, aspirin, isotretinoin, nucleoside loading) | varies | REJECTED | 1 | Grouped; to be split per-agent before final submission. |

## Counter-evidence kept, bounded
Reducing chromosome mis-segregation is not unconditionally safe: Ertych et al. 2014 (Fig 7) show reduced CIN accelerated tumor growth in a colorectal model, and the CIN-cancer relationship is rate-dependent (Bakhoum & Compton 2012). This is bounded to those preclinical models and cannot be quantified into a clinical contraindication for this child; it is the reason every disease-modifying experiment co-measures clonal fitness.

## Reproducibility and scope
The gate engine validates inputs (unknown or malformed inputs BLOCK, never pass), passes a five-check regression suite, and runs in a clean environment from pinned dependencies (`run.sh`). It demonstrates gate logic; candidate generation and evidence appraisal remain curated. The synthetic gain-of-function case shows the directionality rule flipping with the input — a scalability demonstration of the logic, not a cross-disease discovery claim.

## Limitations
No drug has rescue data in MVA/BUB1B patient cells; the only intervention shown to lower aneuploidy at the source is genetic BubR1 restoration. Phase, N1002K function, NMD fate and residual function are unresolved. The strongest surviving rationale (NAD+/SIRT2) is unvalidated in the disease model and carries a contested oncology direction. Several global negatives ("no publication", "no trial") need dated search strategies before they are asserted.

## Methods and AI provenance
See `METHODS_AND_AI.md`. Raw patient data stayed in a controlled local environment; only derived facts (HPO, variant list, mechanism) appear here. Deletion within 30 days of close is scheduled.
