#!/bin/sh
# One clean run: selftest -> generate views -> real case -> synthetic case.
# Any step failure exits non-zero (no pipeline masking).
cd "$(dirname "$0")" || exit 1
PY="${PYTHON:-python3}"
mkdir -p outputs
OUT=outputs/run.txt
: > "$OUT"
step() {
  name="$1"; shift
  echo "== $name ==" >> "$OUT"
  "$@" >> "$OUT" 2>&1
  rc=$?
  if [ "$rc" -ne 0 ]; then echo "STEP FAILED ($name) rc=$rc" >> "$OUT"; echo "STEP FAILED ($name) rc=$rc"; exit "$rc"; fi
}
step selftest "$PY" src/triage.py --selftest
step "generate views" "$PY" build_views.py
step "real case" "$PY" src/triage.py --case config/cases/bub1b_mva.yaml --candidates evidence/candidates_from_canonical.yaml
step "synthetic case" "$PY" src/triage.py --case config/cases/synthetic_gof_demo.yaml --candidates evidence/candidates_synthetic.yaml
echo "DONE" >> "$OUT"; echo "DONE (see $OUT)"
