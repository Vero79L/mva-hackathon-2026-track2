# Clean-environment reproducibility (verified 2026-10-08)
Procedure: fresh copy of the repo → `python3 -m venv .venv` → `pip install -r requirements.txt`
(pyyaml==6.0.3) → `./run.sh`. Result: selftest ALL PASS; real case Summary
{STRONG:0, CONDITIONAL:3, REJECT:7, BLOCKED:0}; synthetic GoF case {STRONG:1, REJECT:1}.
No patient data is present or required; the engine fixture is generated from the
canonical candidate table. Git: committed, `.gitignore` excludes VCF/FASTQ/docx/tokens.
