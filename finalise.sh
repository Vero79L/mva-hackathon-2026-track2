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
echo "=== regenerating the committed run snapshot ==="
# Order matters, and the first version of this script had it wrong. It ran the freeze gate before
# rebuilding these two artifacts, and the gate blocks precisely because they are older than
# docs/REPORT.md -- which they are BECAUSE the two slots were just filled. With set -e the script
# died at the gate and never reached the rebuild it needed. Regenerate first, check last.
PYTHON="$PY" sh run.sh >/dev/null
echo "  outputs/run.txt and outputs/manifest.json regenerated"

echo ""
echo "=== rebuilding the submitted PDF from the filled report ==="
sh make_pdf_chrome.sh
"$PY" - <<'PYEOF'
import re
PAT = rb"/Count\s+(\d+)"          # kept out of the f-string: a backslash cannot go inside one
d = open("docs/Vero7878_track2_report.pdf", "rb").read()
pages = max(int(m.group(1)) for m in re.finditer(PAT, d))
print("  {} pages, {:,} bytes".format(pages, len(d)))
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
echo "=== privacy scan, whole repo ==="
"$PY" scripts/phase1/19_public_safety.py 2>&1 | tail -2
echo ""
echo "=== freeze gate ==="
"$PY" make_manifest.py --freeze
echo ""
echo "=== what is left ==="
echo "  1. read the diff:   git diff --stat"
echo "  2. stage and commit the named paths, then push"
echo "  3. submit at the Space, and keep two attempts in hand"
echo "  (backup of the unfilled report: docs/REPORT.md.prefill-backup)"
