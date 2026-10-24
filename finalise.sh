#!/bin/sh
# The last mile, as one command. Run it after the pitch video is uploaded.
#
#   sh finalise.sh https://youtu.be/XXXXXXXXXXX
#
# It fills the two slots the release gate blocks on at freeze, re-runs every check, rebuilds the
# submitted PDF from the filled report, and prints what is left. It does not commit and does not
# push: the last edit before a deadline is the one most worth looking at before it leaves.
#
# Everything here is reversible. The pre-fill backup is written next to the report.
set -e
cd "$(dirname "$0")"
PY="${PYTHON:-/Users/veromacpro/miniforge3/envs/mva/bin/python3}"

URL="$1"
[ -n "$URL" ] || { echo "usage: sh finalise.sh <pitch video URL>" >&2; exit 1; }
case "$URL" in
  https://youtu.be/*|https://www.youtube.com/*|https://youtube.com/*|https://vimeo.com/*) ;;
  *) echo "That does not look like a YouTube or Vimeo URL: $URL" >&2
     echo "The submission form's own error text names those two." >&2; exit 1 ;;
esac

DATE=$(date -u +%Y-%m-%d)
echo "=== filling slots ==="
echo "  video: $URL"
echo "  date : $DATE (UTC)"
cp docs/REPORT.md docs/REPORT.md.prefill-backup
"$PY" - "$URL" "$DATE" <<'PYEOF'
import io, sys
url, date = sys.argv[1], sys.argv[2]
p = "docs/REPORT.md"
s = io.open(p, encoding="utf-8").read()
n_v, n_d = s.count("{{FILL:VIDEO}}"), s.count("{{FILL:DATE}}")
if n_v == 0 and n_d == 0:
    print("  both slots were already filled; nothing changed"); raise SystemExit(0)
s = s.replace("{{FILL:VIDEO}}", url).replace("{{FILL:DATE}}", date)
io.open(p, "w", encoding="utf-8").write(s)
print(f"  replaced {n_v} video slot(s) and {n_d} date slot(s)")
PYEOF

echo ""
echo "=== tests ==="
bash tests/phase1/run_tests.sh 2>&1 | tail -3
echo ""
echo "=== engine selftest ==="
"$PY" src/triage.py --selftest 2>&1 | tail -1
echo ""
echo "=== fact register ==="
"$PY" scripts/phase1/13_check_register.py 2>&1 | tail -3
echo ""
echo "=== freeze gate ==="
"$PY" make_manifest.py --freeze
echo ""
echo "=== rebuilding the submitted PDF from the filled report ==="
sh make_pdf_chrome.sh
"$PY" - <<'PYEOF'
import re
d = open("docs/Vero7878_track2_report.pdf", "rb").read()
print(f"  {max(int(m.group(1)) for m in re.finditer(rb'/Count\s+(\d+)', d))} pages, {len(d):,} bytes")
PYEOF
echo ""
echo "=== privacy scan, whole repo ==="
"$PY" scripts/phase1/19_public_safety.py 2>&1 | tail -2
echo ""
echo "=== what is left ==="
echo "  1. read the diff:   git diff --stat"
echo "  2. stage and commit the named paths, then push"
echo "  3. submit at the Space, and keep two attempts in hand"
echo "  (backup of the unfilled report: docs/REPORT.md.prefill-backup)"
