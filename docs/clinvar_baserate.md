# ClinVar base rates for *BUB1B*, by consequence class

*Dated snapshot, NCBI E-utilities, queried 2026-10-21 by `scripts/phase1/21_quant_checks.py clinvar-baserate`. The query is the gene symbol `BUB1B[gene]` and nothing else; every record is then classified locally from its own summary. One row per ClinVar VariationID, so the columns are a partition and the rows sum to the denominator — unlike the advanced-search significance filters, which match any submitted classification and therefore double-count records with conflicts.*

Denominator: **2,504** ClinVar records for *BUB1B* (2,504 summaries retrieved).

| Consequence | Pathogenic | Pathogenic/Likely pathogenic | Likely pathogenic | Conflicting | Uncertain significance | Likely benign | Benign/Likely benign | Benign | (none) | Pathogenic; Affects | not provided | total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| missense | 0 | 0 | 1 | 29 | 1426 | 28 | 3 | 4 | 5 | 0 | 2 | **1498** |
| nonsense | 29 | 5 | 4 | 0 | 2 | 0 | 0 | 0 | 1 | 0 | 0 | **41** |
| frameshift | 25 | 2 | 7 | 1 | 4 | 0 | 0 | 0 | 0 | 1 | 1 | **41** |
| splice site | 0 | 0 | 10 | 0 | 3 | 0 | 0 | 0 | 1 | 1 | 1 | **16** |
| other / not stated | 12 | 0 | 0 | 16 | 61 | 748 | 11 | 55 | 4 | 1 | 0 | **908** |

**What this bounds, for report §2.** Among *BUB1B* **missense** records, 1,426 of 1,498 (95.2%) are classified Uncertain significance and 1 is Pathogenic or Likely pathogenic. Curated classification therefore carries almost no discriminating information for *any* BUB1B missense allele, which is why the absence of a curated record for this child's missense allele is uninformative rather than reassuring, and why §3's two-class model and the predictors carry that allele instead. Among **truncating** records (nonsense, frameshift, splice site) the picture reverses: 82 of 98 (83.7%) are Pathogenic or Likely pathogenic, so the two-star Pathogenic/Likely pathogenic classification of this child's truncating allele sits with the class base rate rather than standing out from it.

**Review status across the whole gene.** 1,884 criteria provided, single submitter; 544 criteria provided, multiple submitters, no conflicts; 46 criteria provided, conflicting classifications; 15 no assertion criteria provided; 11 (none); 4 no classification provided.

**Bounds.** A base rate across a gene is not evidence about one allele: it says what a classification of that class usually is, not what this variant is. Counts move with each ClinVar release, so the date above is part of the claim. Consequence class is read from each record's own summary; records whose summary states no consequence fall in `other / not stated` and are not redistributed.
