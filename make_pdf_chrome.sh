#!/bin/sh
# Build the submission PDF from docs/REPORT.md WITHOUT a TeX toolchain.
#
# Why this exists alongside make_pdf.sh. make_pdf.sh is the better typesetter and stays the
# reference build, but it needs pandoc plus a LaTeX install with xelatex, and on 2026-10-20 the
# submission machine had neither -- which meant the documented way to rebuild the one artifact the
# judges open did not run. A build path that is not installed is not a build path. This one needs
# only Node (for the Markdown parse) and Google Chrome (for the PDF), both already present, and it
# reproduces the one thing the LaTeX version exists for: the mechanism figure gets its own
# landscape page, because at portrait text width its node labels render around 6pt.
#
# Usage:  sh make_pdf_chrome.sh            (run from research/engine/)
#         sh make_pdf_chrome.sh out.pdf    (write somewhere else)
#
# First run fetches `marked` from npm; after that it is cached and the build is offline.
set -e
cd "$(dirname "$0")"
OUT="${1:-docs/Vero7878_track2_report.pdf}"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
[ -x "$CHROME" ] || { echo "Google Chrome not found at: $CHROME (set CHROME=/path/to/chrome)" >&2; exit 1; }
command -v npx >/dev/null 2>&1 || { echo "npx not found - install Node.js" >&2; exit 1; }

W="$(mktemp -d)"
trap 'rm -rf "$W"' EXIT
mkdir -p "$W/figures"
cp docs/figures/mechanism.png "$W/figures/"

# The submitted PDF carries the report plus three appendices. Three documents that answer the
# panel's own criteria -- the plain-language summary, the care-team safety annex and the nine-gene
# decision table -- lived only in the repository, while the file a judge opens is this PDF. A
# pointer to a file the reader cannot open is not a pointer, so they are bound in.
W="$W" python3 - <<'PY2'
import os, pathlib, re
w = pathlib.Path(os.environ["W"])
APPENDICES = [
    ("A", "docs/PLAIN_LANGUAGE_SUMMARY.md",
     "written for the child's family and for a care team that has not read the mitosis literature. "
     "Where it and the report disagree, the report is right."),
    ("B", "docs/SAFETY_ANNEX.md",
     "mechanism-derived recognition for a care team, useful independently of this submission's "
     "candidate, and pointed first at the published cancer-surveillance consensus that names MVA."),
    ("C", "docs/MVA_DECISION_TABLE.md",
     "the same decision rule applied across nine MVA-causing genes, with the first experiment for "
     "each and a per-gene statement of where the BUB1B-specific lever does not apply."),
]
parts = [pathlib.Path("docs/REPORT.md").read_text(encoding="utf-8")]
for letter, rel, why in APPENDICES:
    text = pathlib.Path(rel).read_text(encoding="utf-8")
    m = re.match(r"#\s+(.+?)\n", text)
    title = m.group(1).strip() if m else rel
    body = text[m.end():] if m else text
    parts.append(f'\n\n<div class="apxbreak"></div>\n\n# Appendix {letter} \u2014 {title}\n\n'
                 f'*Repository file `{rel}`, bound into this PDF so the panel does not have to browse '
                 f'the repository: {why}*\n{body}')
(w / "full.md").write_text("".join(parts), encoding="utf-8")
PY2
npx --yes marked@15.0.7 --gfm -i "$W/full.md" -o "$W/body.html"

W="$W" python3 - <<'PY'
import html, os, pathlib, re

w = pathlib.Path(os.environ["W"])
body = (w / "body.html").read_text(encoding="utf-8")

CSS = """
@page { size: A4; margin: 18mm 16mm 16mm 16mm; }
@page landscape { size: A4 landscape; margin: 12mm; }
html { -webkit-print-color-adjust: exact; }
body { font: 9.6pt/1.42 "Helvetica Neue", Helvetica, Arial, sans-serif; color:#111; margin:0; }
h1 { font-size: 19pt; line-height:1.2; margin:0 0 6pt; }
h2 { font-size: 13pt; margin:16pt 0 5pt; padding-bottom:2pt; border-bottom:0.6pt solid #bbb;
     break-after: avoid; page-break-after: avoid; }
h3 { font-size: 11pt; margin:11pt 0 3pt; break-after: avoid; }
p, li { orphans:3; widows:3; margin:0 0 5pt; }
ul, ol { margin:0 0 6pt 16pt; padding:0; }
li { margin-bottom:2pt; }
strong { font-weight:650; }
code { font: 8.6pt "SF Mono", Menlo, monospace; background:#f3f3f3; padding:0 2px;
       border-radius:2px; word-break: break-word; }
pre { background:#f6f6f6; padding:6pt 8pt; border-radius:3px; overflow-wrap:anywhere;
      white-space:pre-wrap; font-size:8.4pt; break-inside: avoid; }
pre code { background:none; padding:0; }
a { color:#14417a; text-decoration:none; }
blockquote { margin:6pt 0; padding:5pt 10pt; border-left:2.5pt solid #9ab;
             background:#f7f9fb; break-inside: avoid; }
blockquote p { margin:0 0 4pt; }
table { border-collapse:collapse; width:100%; margin:6pt 0 9pt; font-size:8.2pt; }
th, td { border:0.5pt solid #c4c4c4; padding:3pt 4pt; vertical-align:top; text-align:left; }
th { background:#eceff2; font-weight:650; }
tr { break-inside: avoid; }
img { max-width:100%; }
hr { border:none; border-top:0.6pt solid #ccc; margin:10pt 0; }
.figpage { page: landscape; break-before: page; break-after: page; text-align:center; }
.figpage img { max-width:100%; max-height:15.5cm; }
.figpage .cap { font-size:8pt; text-align:left; margin-top:6pt; color:#222; }
.apxbreak { break-before: page; page-break-before: always; }
"""


def inline_md(s):
    """The figure caption lives in the image's alt text, so its emphasis is still Markdown."""
    s = html.escape(html.unescape(s), quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s, flags=re.S)
    s = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", s, flags=re.S)
    s = re.sub(r"`([^`]+?)`", r"<code>\1</code>", s)
    return s


# Give the mechanism figure its own landscape page, for the same reason make_pdf.sh does.
m = re.search(r'<p>(<img src="figures/mechanism\.png"[^>]*>)(.*?)</p>', body, re.S)
if not m:
    raise SystemExit("mechanism figure not found in the rendered HTML - "
                     "did the image path in docs/REPORT.md change?")
alt = re.search(r'alt="(.*?)"', m.group(1), re.S)
cap = inline_md(alt.group(1)) if alt else m.group(2)
body = (body[:m.start()]
        + f'<div class="figpage">{m.group(1)}<div class="cap">{cap}</div></div>'
        + body[m.end():])

(w / "report.html").write_text(
    "<!doctype html><html><head><meta charset='utf-8'>"
    "<title>MVA Track 2 report</title>"
    f"<style>{CSS}</style></head><body>{body}</body></html>", encoding="utf-8")
PY

"$CHROME" --headless=new --disable-gpu --no-first-run --no-pdf-header-footer \
  --user-data-dir="$W/chrome" --virtual-time-budget=20000 \
  --run-all-compositor-stages-before-draw \
  --print-to-pdf="$W/out.pdf" "file://$W/report.html" 2>/dev/null || true

[ -s "$W/out.pdf" ] || { echo "Chrome produced no PDF" >&2; exit 1; }
cp "$W/out.pdf" "$OUT"
echo "PDF: $OUT"
