# Candidate table (generated from candidates_canonical.json, 2026-10-08)

Denominator: 12 interventions + 3 mechanism-branches + 1 negative-control groups = 16 entries.
Research judgment: CONDITIONAL=5, INSUFFICIENT=2, REJECTED=9

| ID | Candidate | Type | Eligibility | Research | Dir | Ev-dist | Reason |
|---|---|---|---|---|---|---|---|
| C-NAD | NAD+ precursor (NMN / NR) | mechanism_branch | INELIGIBLE | CONDITIONAL | compensate | 2 | On-mechanism rationale is real, but the NMN/NR drug step is a bridging hypothesis unvalidated in the MVA model and in N1002K; oncology direction contested (raise BubR1 suppresses vs NAD+ fuels tumors). |
| C-RT | PTC readthrough of L737X (DAP / ELX-02; aminoglycoside & ataluren rejected) | mechanism_branch | INELIGIBLE | CONDITIONAL | compensate | 2 | Corrected: readthrough gives a near-full-length product (old 'truncated' reason withdrawn). Coordinates recomputed (readthrough_coordinates_2026-10-08.md): stop UGA at c.2209-2211 (g.40209700-702), +1 context base = c.2212 = g.40209703 (raw log's c.2213 was off by one). Blocker = NMD (PREDICTED, not measured; needs allele-specific mRNA) + no renal-safe approved UGA agent. One-allele rescue judged by functional threshold, not allele count. |
| C-PBA | Sodium / glycerol phenylbutyrate (4-PBA) | intervention | ELIGIBLE | INSUFFICIENT | compensate (intended) | 1 | Mechanism mismatch (BUBR1 is cytosolic/mitotic) + achievable exposure (0.2-1.3 mM total) overlaps the HDAC range. Thresholds are NOT a measured N1002K ECx -> 'direct rescue and exposure feasibility not established' (deprioritized), NOT 'no window proven'. |
| C-NAC | N-acetylcysteine | intervention | ELIGIBLE | CONDITIONAL | mitigate | 2 | Conditional as downstream mitigation (a lane the strategy permits), NOT a disease modifier; exposure for the mitigation endpoint unproven; keep tumor-promotion watch. |
| C-AMPK | AMPK aneuploid-deselection (metformin; non-renal AMPK agent needed) | mechanism_branch | ELIGIBLE | CONDITIONAL | deselect | 3 | Research question: under what cell + exposure does a selective effect exceed normal-tissue loss? Anti-proliferation is not repaired segregation. Euploid cells in constitutional BUB1B deficiency still carry the defect. |
| C-DQ | Dasatinib + Quercetin (senolytic) | intervention | ELIGIBLE | REJECTED | deselect (downstream) | 1 | Acts downstream; genetic-tool validation != D+Q drug evidence; endpoint mismatch (senescence markers, not aneuploidy) + toxicity on this child's organs. |
| C-FOL | Folate (folinic/5-MTHF) + B12 | intervention | ELIGIBLE | INSUFFICIENT | mitigate (partial) | 2 | Supportive/deficiency-correction claim distinct from disease modification; dose only to the genome-stability threshold; oncology watch. |
| C-RAPA | Rapamycin / sirolimus | intervention | ELIGIBLE | CONDITIONAL | oncologic-protective only | 2 | Keep as conditional on the oncologic-protective axis; the 'genome-stabilizing' story is not supported; the null is an unpublished preliminary signal, not proof of equivalence or inefficacy. |
| N-MITOTIC | MPS1/TTK, Aurora B, PLK1, KIF11 inhibitors; microtubule destabilizers; bortezomib; HSP90i (17-AAG) | negative_control | UNKNOWN | REJECTED | worsen | 1 | Negative controls with clear reasons; proven wrong-direction for checkpoint insufficiency. Kept to show the system says no, not scored by a string rule alone. |
| N-CQ | Chloroquine / hydroxychloroquine | intervention | ELIGIBLE | REJECTED | n/a | 1 | Eligible+aneuploidy-selective in principle, but research-rejected: hypothesis-only, chronic pediatric toxicity (retinopathy/QT). |
| N-ASA | Aspirin | intervention | ELIGIBLE | REJECTED | n/a | 1 | Off-target tumor spectrum; Reye contraindication in pediatric viral illness. |
| N-ISO | Isotretinoin | intervention | ELIGIBLE | REJECTED | n/a | 1 | Benefit is neuroblastoma-MRD-specific; off-target for MVA; iPLEDGE REMS. |
| N-AICAR | AICAR / 17-AAG | intervention | INELIGIBLE | REJECTED | n/a | 1 | Aneuploidy-selective research tools; p53-dependent killing in a cancer-prone child; not approved. |
| N-NAVI | Navitoclax | intervention | INELIGIBLE | REJECTED | n/a | 1 | Senolytic but investigational; on-target thrombocytopenia hazardous in a cytopenia-prone child. |
| N-FIS | Fisetin | intervention | INELIGIBLE | REJECTED | n/a | 1 | Supplement; no approved drug pathway; no proven clinical senolytic benefit. |
| N-NUC | Bulk nucleoside loading | intervention | INELIGIBLE | REJECTED | n/a | 1 | Feeds nucleotide-dependent aneuploid clones; uridine triacetate (Xuriden) approved only for orotic aciduria. |
