# Tractability of the checkpoint / segregation module and the NAD+ axis

*Dated snapshot, Open Targets GraphQL API, queried 2026-10-21 by `scripts/phase1/21_quant_checks.py tractability`. The query sends an Ensembl gene identifier and nothing else. Re-run the subcommand to refresh; the date above is the release this report cites.*

`SM` small molecule, `AB` antibody, `PR` PROTAC/degrader, `OC` other. Only buckets with `value = true` are listed.

| Protein | Role | Approved drug (any modality) | SM advanced clinical | Other true buckets |
|---|---|---|---|---|
| BUB1B | MCC core / SAC — the affected protein | no | no | SM:High-Quality Ligand, SM:Druggable Family, PR:Literature, PR:UniProt Ubiquitination, PR:Database Ubiquitination |
| BUB1 | SAC kinase | no | no | SM:Structure with Ligand, SM:High-Quality Ligand, SM:Med-Quality Pocket, SM:Druggable Family, PR:Literature, PR:UniProt Ubiquitination, PR:Database Ubiquitination, PR:Small Molecule Binder |
| BUB3 | SAC, BUB1/BUBR1 partner | no | no | PR:UniProt Ubiquitination, PR:Database Ubiquitination, PR:Half-life Data |
| MAD1L1 | SAC, MAD2 recruitment | no | no | PR:UniProt Ubiquitination, PR:Database Ubiquitination, PR:Half-life Data |
| MAD2L1 | MCC component | no | no | SM:Structure with Ligand, SM:High-Quality Pocket, PR:Database Ubiquitination, PR:Half-life Data |
| CDC20 | APC/C activator, MCC target | no | no | SM:Structure with Ligand, PR:Literature, PR:UniProt Ubiquitination, PR:Database Ubiquitination |
| TTK | MPS1 kinase, SAC signalling | no | **yes** | SM:Structure with Ligand, SM:High-Quality Ligand, SM:High-Quality Pocket, SM:Druggable Family, PR:Literature, PR:Database Ubiquitination, PR:Small Molecule Binder |
| AURKB | error correction | no | **yes** | SM:Structure with Ligand, SM:High-Quality Ligand, SM:Druggable Family, PR:Literature, PR:UniProt Ubiquitination, PR:Database Ubiquitination, PR:Small Molecule Binder |
| PLK1 | mitotic kinase | no | **yes** | SM:Structure with Ligand, SM:High-Quality Ligand, SM:High-Quality Pocket, SM:Druggable Family, PR:Literature, PR:UniProt Ubiquitination, PR:Database Ubiquitination, PR:Small Molecule Binder |
| KIF11 | spindle motor | no | **yes** | SM:Structure with Ligand, SM:High-Quality Ligand, SM:High-Quality Pocket, SM:Druggable Family, PR:UniProt Ubiquitination, PR:Database Ubiquitination, PR:Small Molecule Binder |
| CENPE | kinetochore motor | no | no | SM:Structure with Ligand, SM:High-Quality Ligand, SM:Med-Quality Pocket, PR:UniProt Ubiquitination, PR:Database Ubiquitination, PR:Small Molecule Binder |
| TRIP13 | MCC turnover (MVA3) | no | no | SM:Structure with Ligand, PR:Database Ubiquitination, PR:Half-life Data |
| CEP57 | centrosome maturation (MVA2) | no | no | PR:Database Ubiquitination, PR:Half-life Data |
| SIRT2 | NAD+-dependent deacetylase — the proposed lever | no | no | SM:Structure with Ligand, SM:High-Quality Ligand, SM:High-Quality Pocket, SM:Druggable Family, AB:GO CC high conf, PR:Literature, PR:UniProt Ubiquitination, PR:Database Ubiquitination, PR:Half-life Data, PR:Small Molecule Binder |
| NAMPT | NAD+ salvage | no | **yes** | SM:Structure with Ligand, SM:High-Quality Ligand, SM:High-Quality Pocket, SM:Druggable Family, AB:UniProt loc high conf, AB:GO CC med conf, PR:Database Ubiquitination, PR:Half-life Data, PR:Small Molecule Binder |

**Counted result.** Of the 15 proteins above, **0** carry an `Approved Drug` bucket in any modality, and **5** carry a small molecule in advanced clinical development: TTK, AURKB, PLK1, KIF11, NAMPT. Every one of those 5 is an **inhibitor** — four of mitotic or checkpoint machinery (TTK/MPS1, AURKB, PLK1, KIF11) and one of NAD+ synthesis (NAMPT, where the advanced agents are NAMPT inhibitors developed to *lower* NAD+ in tumours). Every druggable node in this module therefore points in the direction that makes a checkpoint-insufficient child worse, which is the quantitative form of the directionality prerequisite in §4 and the reason the candidate had to come from upstream metabolism rather than from the module itself.

**BUB1B specifically: undrugged, and the one modality with any evidence runs backwards.** Its true buckets are `SM:High-Quality Ligand`, `SM:Druggable Family`, `PR:Literature`, `PR:UniProt Ubiquitination`, `PR:Database Ubiquitination`. There is no approved drug, no clinical-stage small molecule, no ligand-bound structure and no qualifying pocket; the PROTAC row is positive on ubiquitination and literature evidence, and a degrader of BubR1 would lower the protein this hypothesis exists to raise. This is what §10's reportable gap looks like when it is counted rather than asserted.

**Bounds.** Tractability buckets are a database's assessment of *whether a modality looks feasible*, not a search for every compound with activity on these proteins, and `Approved Drug` is scoped to the target, not to the pathway — niacin is an approved product acting on NAD+ metabolism, and nothing in this table contradicts that. The panel is the module we reasoned over plus the two other MVA genes; it is not a genome-wide screen, so this table bounds the module we examined and does not establish coverage elsewhere.
