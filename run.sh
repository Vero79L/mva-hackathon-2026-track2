#!/bin/sh
# Single clean-run command: real case + synthetic case + selftest, snapshot to outputs/
set -e
cd "$(dirname "$0")"
mkdir -p outputs
PY="${PYTHON:-python3}"
echo "== selftest ==" | tee outputs/run.txt
$PY src/triage.py --selftest 2>&1 | tee -a outputs/run.txt
echo "\n== real case (bub1b_mva) ==" | tee -a outputs/run.txt
$PY src/triage.py --case config/cases/bub1b_mva.yaml --candidates evidence/candidates_from_canonical.yaml 2>&1 | tee -a outputs/run.txt
echo "\n== synthetic case (gof demo) ==" | tee -a outputs/run.txt
$PY src/triage.py --case config/cases/synthetic_gof_demo.yaml --candidates evidence/candidates_synthetic.yaml 2>&1 | tee -a outputs/run.txt
echo "\nDONE. Snapshot in outputs/run.txt"
