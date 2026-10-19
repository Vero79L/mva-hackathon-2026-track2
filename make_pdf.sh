#!/bin/sh
# Build the submission PDF from docs/REPORT.md.
#
# REPORT.md stays clean so GitHub renders it correctly. The one thing only the PDF needs is
# injected into a temporary copy here: the mechanism figure gets its own landscape page, because
# at portrait text width its node labels come out around 6pt and a judge cannot read them.
# Usage:  sh make_pdf.sh      (run from research/engine/)
set -e
cd "$(dirname "$0")"
OUT=docs/Vero7878_track2_report.pdf
TMP="$(mktemp)".md
HDR="$(mktemp)".tex
# graphicx, not graphics: the plain graphics package reads [width=...] as coordinates and fails
printf '%s\n' '\usepackage{graphicx}' '\usepackage{pdflscape}' '\usepackage{float}' '\usepackage{caption}' > "$HDR"

TMP="$TMP" python3 - <<'PY'
import os, re, pathlib
src = pathlib.Path("docs/REPORT.md").read_text(encoding="utf-8")
m = re.search(r'^!\[(.+?)\]\(figures/mechanism\.png\)[^\n]*$', src, re.M | re.S)
if m:
    cap = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', m.group(1), flags=re.S)
    cap = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'\\emph{\1}', cap, flags=re.S)
    cap = cap.replace('§', r'\S{}').replace('`', '').replace('_', r'\_')
    cap = ' '.join(cap.split())
    block = ("\n\\begin{landscape}\n\\begin{figure}[H]\n\\centering\n"
             "\\includegraphics[width=\\textwidth,height=0.80\\textheight,keepaspectratio]"
             "{" + str(pathlib.Path("docs/figures/mechanism.png").resolve()) + "}\n"
             "\\captionsetup{labelformat=empty}\n\\caption{\\footnotesize " + cap + "}\n"
             "\\end{figure}\n\\end{landscape}\n")
    src = src[:m.start()] + block + src[m.end():]
pathlib.Path(os.environ["TMP"]).write_text(src, encoding="utf-8")
PY

pandoc "$TMP" -o "$OUT" \
  --pdf-engine=xelatex --resource-path=docs --include-in-header="$HDR" \
  -V mainfont="DejaVu Serif" -V sansfont="DejaVu Sans" -V monofont="DejaVu Sans Mono" \
  -V geometry:margin=2cm -V fontsize=9.5pt -V colorlinks=true -V linkcolor=NavyBlue \
  --toc --toc-depth=2
rm -f "$TMP" "$HDR"
echo "PDF: $OUT"
