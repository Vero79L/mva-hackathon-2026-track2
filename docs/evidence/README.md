# Evidence inputs

Gene-level literature material that the report draws on. No patient data.

## Pending drop-in
`BUB1B MVA 機制與治療證據.md` — the deep-research literature report produced in the
Track 2 research session (2026-10-13). It is a download from that session and is not yet
in this folder; drop it in here when convenient.

Its load-bearing findings have already been verified independently against PubMed and
folded into the report (2026-10-19), so the report does not block on this file:

| Finding | Where it landed | Verification |
|---|---|---|
| BubR1 is required for primary-cilium formation; PCS/MVA is also a ciliopathy (medaka knockdown → cerebellar defects, laterality) | REPORT §3 link 5b; endpoint caveat (ii); MVA_DECISION_TABLE "second branch" | Miyamoto 2011, Hum Mol Genet 20(10):2058-70, PMID 21389084 — verified 2026-10-19 |
| Aneuploidy proportion does not rank with severity → not a primary efficacy endpoint | REPORT §3 endpoint caveat (i); §6 readout table | Sieben 2020, PMID 31738183 — verified |
| CEP57-MVA fails at centrosome maturation, not SAC signalling → stratify by measured checkpoint function, not gene identity | MVA_DECISION_TABLE, CEP57 row + stratification section | Aziz 2018, J Clin Invest 128(8):3517-3534, PMID 30035751 — verified 2026-10-19 |
| TRIP13 biallelic → Wilms tumour and missegregation | MVA_DECISION_TABLE, TRIP13 row | Yost 2017, Nat Genet, PMID 28553959 — verified 2026-10-19 |
| The rescue in the SIRT2/BubR1 lifespan experiment was a transgene, not a drug; NMN is the only drug-like agent that raised BubR1 and it is not approved | REPORT §5 (C-NAD stays INELIGIBLE), canonical C-NAD note | North 2014, PMID 24825348 — verified |
| nicotinamide is both an NAD+ precursor and a sirtuin inhibitor → direction risk; not interchangeable with nicotinic acid | REPORT §9; SAFETY_ANNEX high-dose nicotinamide row | North 2014 Fig 1 — verified |
| Systemic NAD+ repletion is not uniform across tissues (blood rose far more than muscle); flushing/paraesthesia common above the lower dose range | REPORT §13 limitations; §9 counter-evidence | Pirinen 2020, PMID 32386566 — verified; the per-tissue ratio itself still to be read off the full text |

Anything in that file still marked UNVERIFIED must stay UNVERIFIED until
`scripts/phase1/16_verify_citations.py` resolves it on this machine.
