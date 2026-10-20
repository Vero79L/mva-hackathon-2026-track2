# All-MVA decision table — the same rule across the MVA genes

*Scalability output. The decision rule (report §1) is disease-agnostic; this table applies it to each MVA-causing gene to show that the method transfers, and to mark where the NAD+/SIRT2–BubR1 axis is and is not relevant. Candidate generation and evidence grading remain human-curated — this is a transfer of the rule, not an automated discovery.*

*Citations are cited by author/year/journal; every PMID marked `[verify]` is checked by `scripts/phase1/16_verify_citations.py` before this table is published. Entries without a strong per-gene mechanism cite are marked `pending citation` and are not asserted until verified.*

## How to read a row

For each gene: the complex it belongs to, the **defect direction** (what the biallelic loss does to the checkpoint / segregation), the **first experiment** that would characterize residual function in a patient's cells, and whether the **NAD+/SIRT2 axis** (the BUB1B-specific lever) is even applicable. The `scoring.yaml` directionality rule is the same for every checkpoint-insufficiency gene; only the molecular entry point changes.

| Gene (MVA type) | Complex / role | Defect direction | First experiment (characterize residual function) | NAD+/SIRT2 axis relevant? |
|---|---|---|---|---|
| **BUB1B / BubR1** (MVA1) | MCC core; SAC; KARD–PP2A error correction | checkpoint insufficiency (hypomorph ± allele-quality defect) | residual BubR1 abundance + K668 acetylation + SAC readout (report §6) | **Yes** — this is the only MVA gene where SIRT2–BubR1-K668 directly applies (North 2014) |
| **CEP57** (MVA2) | Centrosomal; centrosome maturation, PCM/centriole engagement | centrosome-maturation failure in G2 → premature centriole disjunction, centrosome amplification, aberrant spindle → missegregation (**distinct from SAC signalling**) | centrosome maturation in G2 + centriole engagement + aneuploidy rate in patient cells | No — the downstream endpoint (segregation fidelity) is shared, but the lever is centrosome biology, not BubR1 abundance. Aziz 2018 (PMID 30035751); a 2026 case report adds a novel CEP57 variant in MVA2 (PMID 41700350) |
| **TRIP13** (MVA3) | AAA+ ATPase; MAD2 conformational cycling / MCC turnover | checkpoint dysfunction (impaired MCC dynamics); biallelic variants predispose to Wilms tumour | MAD2 O↔C conversion / SAC strength + aneuploidy in patient cells | No — acts on MAD2 cycling, not BubR1 stability. Yost 2017 (PMID 28553959) |
| **CENATAC / CCDC84** | Minor (U12) spliceosome; intron retention | mis-splicing of cell-cycle/segregation transcripts → aneuploidy | minor-intron splicing readout + aneuploidy; which checkpoint transcripts are mis-spliced | Indirect at most — only if a mis-spliced target lies on the BubR1 axis (to be shown, not assumed) |
| **SLF2 / SMC5** | SMC5/6 complex; replication/segregation genome stability | genome-stability insufficiency → aneuploidy | SMC5/6-dependent replication-stress / segregation readout in patient cells | No |
| **TRIM37** (Mulibrey nanism) | Centrosome regulation; TRIM37 is a centrosomal E3 ligase | centrosome dysregulation → missegregation; MVA reported as a *novel* feature of Mulibrey nanism (aneuploidy in 7–36% of metaphases across patients) | karyotype / aneuploidy rate in fibroblasts + centrosome number | No — centrosome biology, not BubR1 abundance. Hakonen 2026 (PMID 41702694) |
| **MAD1L1 / MAD1** | SAC; MAD2 kinetochore recruitment | checkpoint insufficiency | SAC strength (MAD2 recruitment) + aneuploidy in patient cells | No — SAC-insufficiency direction is shared with BUB1B, but the lever is MAD1/MAD2, not BubR1 abundance |
| **BUB1** | SAC kinase; kinetochore scaffold | checkpoint insufficiency | SAC strength + aneuploidy in patient cells | No |
| **BUB3** | SAC; GLEBS-domain partner of BUB1/BUBR1 | checkpoint insufficiency | SAC strength + aneuploidy in patient cells | Possibly adjacent (BUB3 partners BubR1) — not asserted without a per-gene cite |

## One design consequence: stratify by measured checkpoint function, not by gene name

The genes above are grouped under one clinical label, but they do not produce the same checkpoint deficit. The SAC-component genes (BUB1B, MAD1L1, BUB1, BUB3) disable checkpoint *signalling* directly; CEP57 leaves checkpoint signalling largely intact and fails at centrosome maturation instead (Aziz 2018, PMID 30035751). The mechanistic expectation is that cancer risk in MVA tracks the severity of chromosome missegregation rather than the identity of the mutated gene, and on that expectation the defensible stratification axis for candidate selection is **measured checkpoint function and missegregation rate in the patient's own cells**, not the gene label. **We state this as a hypothesis for study design, not as an established fact, and it does not extend to clinical surveillance.** The human comparative data that would test it — matched cancer incidence across MVA genotypes against measured missegregation — do not exist at the numbers required. The AACR consensus (PMID 39264246) deliberately preserves gene-level distinctions, and a cell-based measurement does not displace the surveillance basis it sets out. Where the two differ, follow the consensus.

## A second branch that does not transfer from the mitotic story

For BUB1B specifically, part of the phenotype may be non-mitotic: BubR1 is required for primary-cilium formation, and PCS/MVA has been reframed as also a ciliopathy (Miyamoto 2011, PMID 21389084). Features plausibly in that branch — Dandy-Walker complex, polycystic kidneys, laterality defects — would not be expected to improve with any aneuploidy biomarker. Any all-MVA efficacy framework therefore needs a per-gene statement of which features are expected to track segregation and which are not, rather than one aneuploidy endpoint applied across the table. Whether the other MVA genes have an analogous non-mitotic branch is **not established** and is not assumed here.

## What transfers and what does not

- **Transfers:** the rule (direction → mechanism-contact → four patient gates → an approved product with a dated label), the three-layer fact discipline (CONFIRMED/ASSUMED/UNKNOWN), the input-validating engine, and the "measure residual function first" experimental logic. For every checkpoint-insufficiency gene the directionality rule in `scoring.yaml` is unchanged (`checkpoint_insufficiency → strengthen`).
- **Does not transfer automatically:** the *specific lever*. The NAD+/SIRT2–BubR1-K668 axis that gives BUB1B its named candidate is **BUB1B-specific**; for the other genes the first experiment characterizes a different molecular bottleneck, and the named-candidate step must be redone per gene. Claiming otherwise would be the over-reach the rule exists to prevent.
- **How a new MVA gene is added:** one case file (defect direction, patient constraints); if the defect direction is genuinely new (e.g. a gain-of-function spindle phenotype), one rule in `scoring.yaml`. The synthetic gain-of-function case already demonstrates the directionality flip.

## Citation status

Per-gene mechanism references (CEP57: Snape 2011; CENATAC: de Wolf 2021; SLF2/SMC5: Grange 2022; and the MVA-spectrum reviews Villarroya-Beltri 2022, Carvalhal 2022) are drawn from the Track 1 reference list and re-verified by step 16 before this table is published. The CEP57 (30035751), TRIP13 (28553959) and BUB1B-ciliogenesis (21389084) citations above were verified against PubMed on 2026-10-19; any gene row whose mechanism direction is not yet backed by a verified cite is held at `pending citation` and is not asserted in the report. BUB1B rows are backed by the verified citations in report §3.
