# MVA safety annex — drug classes to weigh carefully in a weakened spindle-assembly checkpoint

*A care-team-facing output, derived from the variant mechanism, not a treatment plan. Everything here is hypothesis-level and based on published class behavior; it names no doses and makes no recommendation for any individual. The treating clinicians decide, with the full clinical picture this document does not have. "Approved" status is a product property; confirm current labels and local formulary at the point of care.*

## Why this annex exists

A mosaic-variegated-aneuploidy cell has a **weak spindle-assembly checkpoint (SAC)** and a low abundance of BubR1 (§3 of the report). Several widely used drug classes act on exactly the machinery that is already compromised, so their *class behavior can differ* in these cells from the general population. The purpose here is recognition — to put the mechanism-level reasoning and the published MVA case experience in front of the care team — not to direct therapy. A competing brief in the community (#29) is assembling MVA chemotherapy safety evidence; this annex is built from the same literature but organized as a mechanism-to-class decision table so the reasoning is auditable.

## Start here, not with this annex: there is a published surveillance consensus that names MVA

Before anything below, a care team should have **Nakano et al., "Update on Recommendations for Cancer Screening and Surveillance in Children with Genomic Instability Disorders", *Clin Cancer Res* 2024;30(22):5009–5020 (PMID 39264246)** — the second AACR Childhood Cancer Predisposition Workshop (July 2023). It names mosaic variegated aneuploidy explicitly and attributes it to "biallelic germline pathogenic variants in *BUB1B* (MVA1), *CEP57* (MVA2) and *TRIP13* (MVA3)", and it carries actual surveillance recommendations:

- **Wilms tumour** — renal ultrasound **every 3 months from birth until age 7**, stated to apply across MVA including genetically unexplained cases; the AACR study group endorses this. (Note a minor internal discrepancy in the source: Table 2 says "starting at diagnosis" where the body text says "from birth".)
- **Rhabdomyosarcoma** — regular clinical assessment including review of systems; **clinical only**, with no imaging and no stated frequency or age range.
- **Leukaemia** — **no surveillance recommended**; MDS / AML / ALL appear only as cancers reported in MVA1.
- **Radiation exposure should be avoided.**
- Family awareness of abnormal mass or swelling, haematuria, hypertension, pain and discomfort.

**One thing that consensus does *not* say.** Its sentence about "exquisite sensitivity to anticancer treatments such as ionizing radiation and chemotherapy" and consequent second-cancer risk is a **class-level statement about genomic instability disorders**, and the dose-reduction and treatment-sensitivity guidance in that paper belongs to ataxia-telangiectasia, Nijmegen breakage syndrome and Bloom syndrome. In the MVA section, **chemotherapy sensitivity is not discussed at all**. That claim is commonly attributed to MVA on the strength of this citation. We checked the source, found it unsupported for MVA specifically, and record that here rather than adopting the stronger wording.

**What this annex adds, and does not replace.** The consensus above is screening guidance. The table below is a mechanism-to-drug-class reading for situations the guidance does not cover — which classes behave differently when the checkpoint is already weak. It is a supplement to that paper, not a substitute for it.

## The reasoning, by class

Each row: the class, the mechanism concern in a weak-SAC / low-BubR1 cell, the evidence strength, and the disposition. Grades: *measured* (in a relevant model), *predicted* (mechanistic inference), *case* (published MVA/aneuploidy case experience).

| Drug class | Mechanism concern in weak-SAC / low-BubR1 cells | Strength | Disposition |
|---|---|---|---|
| **Microtubule-targeting agents** (vinca alkaloids e.g. vincristine; taxanes) | These act by provoking a SAC-dependent mitotic arrest. With a weak checkpoint, cells can undergo **mitotic slippage** — exiting mitosis without proper segregation instead of arresting/dying — which can blunt the intended effect and add missegregation. Checkpoint-slippage via cyclin-B destruction under an active checkpoint is an established phenomenon | predicted + measured (slippage biology: Brito 2006, PMID 16782009; Gascoigne 2008, 18656424) | **Case-by-case**; flag for the care team that class response may differ; not a contraindication |
| **SAC / mitotic-kinase inhibitors** (MPS1/TTK, Aurora B, PLK1, KIF11/Eg5 inhibitors) | Directly further *weaken* the checkpoint that is already deficient — the disease's own direction; raises missegregation | predicted (directional, from mechanism) | **Avoid as repurposing candidates**; these are the engine's wrong-direction negative controls |
| **Proteasome inhibitors** (bortezomib) and **HSP90 inhibitors** (17-AAG) | Perturb the degradation/chaperone balance that sets residual BubR1 abundance; effect on a misfolded missense BubR1 is unpredictable (could raise or lower functional protein) | predicted | **Weigh carefully**; unpredictable on BubR1 abundance; would need the §6 abundance readout before any inference |
| **Niacin formulation substitution** | Immediate-release and sustained/extended-release niacin are **not interchangeable**. The IR label warns that SR preparations must not be substituted for equivalent IR doses, and that severe hepatic toxicity including **fulminant hepatic necrosis** has occurred when they were | measured (label; post-marketing cases) | **Formulation must be specified.** This is a product-level hazard independent of any MVA reasoning, and it applies to the named candidate in this report |
| **High-dose nicotinamide** | A sirtuin *inhibitor* at high concentration; **lowered BubR1** in North 2014 (Fig 1) — directionally opposite to the niacin hypothesis; not interchangeable with other B3 vitamers | measured (cell; North 2014, PMID 24825348) | **Directionally wrong** for raising BubR1; distinguish from nicotinic acid |
| **NAD+ precursors** (the niacin hypothesis itself) | Raising BubR1 is anti-aneuploidy, but NAD+ supply is pro-tumour in some models — unresolved given MVA's cancer predisposition | measured, *contradictory* (Baker 2013, PMID 23242215 vs tumour-model literature) | The decisive experiment's clonal-fitness arm (§6) exists to resolve this before any inference |
| **GSK3 inhibitors, including lithium** | GSK3 is required for *optimal* kinetochore localisation of Mad2, BubR1 and Bub1 and for MCC assembly; GSK3 inhibitors SB 415286, RO 318220 and lithium chloride **relieve** spindle-toxin-induced mitotic arrest, and GSK3β knockout or RNAi shortens Taxol-induced arrest. Directionally this is the disease's own direction: weakening an already-weak checkpoint and reducing kinetochore BubR1 | measured (cell; Rashid 2018, PMID 30250048) — **but see the dose bound** | **Class-level signal only; NOT a statement about therapeutic lithium.** The lithium chloride concentrations in that work were 20, 50 and 60 mM, against a therapeutic serum lithium of roughly 0.6–1.2 mM — 17- to 100-fold higher. Nothing here supports a clinical inference about lithium at therapeutic levels, and the paper reports nothing about raising BubR1 protein. Listed because it is an approved, pediatrically labelled drug class whose mechanism runs the wrong way, so a care team should know the question exists |
| **Radiation / radiomimetics and strongly genotoxic agents** | Add DNA damage/missegregation load to cells already prone to aneuploidy and with cancer predisposition | predicted | **Weigh carefully**; general principle, defer to oncology |

## Published MVA treatment experience (case-level)

These are individual case reports in MVA or MVA-spectrum patients. They are experience, not evidence of a rule, and are included so the care team can see what has been reported.

- **Reduced-intensity chemotherapy in PCS/MVA.** Nishitani-Isa et al., *Pediatr Int* 2019;61(6):613–616 (PMID 31184400): rhabdomyosarcoma in premature-chromatid-separation (PCS)/MVA managed with a reduced-intensity approach.
- **Severe toxicity from a single agent.** Ochiai et al., *Pediatr Blood Cancer* 2019;66(8):e27804 (PMID 31081598): bilateral Wilms tumour with biallelic BUB1B; dactinomycin monotherapy was followed by a severe adverse reaction, leading to bilateral nephrectomy and peritoneal dialysis.
- **Sequential malignancies.** Vempuluru et al., *Orbit* 2026 (PMID 42595739): a TRIP13 (MVA3) patient with Wilms tumour at age 3 and orbital rhabdomyosarcoma at 12 — a reminder that cancer risk in MVA is lifelong and multiplex.

The common thread the care team may find useful: in reported MVA cases, intensity and single-agent toxicity have been concerns, consistent with the mechanism-level expectation that a checkpoint-deficient, aneuploidy-prone organism may tolerate genotoxic and antimitotic stress differently.

## What this annex is not

It does not recommend, rank, or dose any therapy; it does not claim any listed class is contraindicated; and it does not substitute for oncology, clinical genetics, or the treating team's judgment. Every item is a hypothesis for follow-up and clinical evaluation. Every PMID cited above was resolved against PubMed on 2026-10-19 and checked against the claim it is cited for; the PMIDs are written inline so a reader can repeat that check directly. The PMIDs in this annex are not rows of `registers/claim_ledger.csv` unless they are also mechanism-chain or eligibility sources (24825348 and 23242215 are) — that ledger is generated from those two sources only. Every PMID here is nonetheless covered by the automated check in `registers/citation_check.csv`, which reads this file directly. See `registers/search_strategies.md` for the dated searches behind every "we did not find" statement.
