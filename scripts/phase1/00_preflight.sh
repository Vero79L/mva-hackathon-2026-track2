#!/usr/bin/env bash
# 第 00 步：第一階段開工前檢查（Spec 1 v1.1 第 A 節）。只讀不改，隨時可以跑。
# ✓ 通過　! 提醒（可以繼續，但要知道）　✗ 必須先修（結束代碼 1）
# 用法：bash scripts/phase1/00_preflight.sh
. "$(dirname "$0")/t2lib.sh"
set +eu    # 檢查腳本：某一項沒過也要繼續往下看
np=0; nw=0; nf=0
P() { ok "$*"; np=$((np + 1)); }
W() { warn "$*"; nw=$((nw + 1)); }
F() { printf '  ✗ %s\n' "$*" >&2; nf=$((nf + 1)); }
under() { case "$1" in "$2"/*|"$2") return 0 ;; *) return 1 ;; esac; }

say "1/9 這台電腦"
if [ "$(uname -s)" = Darwin ]; then
  info "macOS $(sw_vers -productVersion 2>/dev/null) · $(uname -m)"
  if fdesetup status 2>/dev/null | grep "On" >/dev/null; then P "FileVault 開啟"; else F "FileVault 沒開：系統設定 → 隱私權與安全性 → FileVault"; fi
else
  info "$(uname -s) $(uname -m)（不是 macOS：路徑與指令照 Linux 寫法調整）"
fi
if [ "${CLAUDECODE:-}" = 1 ]; then
  W "你正在 Claude Code 裡執行。第 10、11、11a 以外的步驟不讀病人資料；第 10、11 步讀座標：/status 必須是 Console（API）登入，否則請 Vero 在自己的終端機跑（Spec 1 第 B 節）"
fi

say "2/9 設定（config/local.env → Track 1 的 local.env + paths.env）"
for v in MVA_ROOT RES REF GTF VEP_VERSION VEP_CACHE T1_WORK T1_RESULTS T2_RESULTS T2_WORK REGISTERS CASE_ID VEP_DISTANCE; do
  eval "val=\${$v:-}"
  if [ -n "$val" ]; then info "$(printf '%-12s %s' "$v" "$val")"; else F "設定缺 $v（config/local.env）"; fi
done
case "$T2_RESULTS" in
  *"Library/Mobile Documents"*|*Claude-MyBrain-Professional*|*opportunity-quest*) F "T2_RESULTS 在 iCloud 樹裡：含座標的輸出不能放那裡，改成 ~/mva-hackathon/results/track2" ;;
  *) if under "$T2_RESULTS" "$ENGINE"; then F "T2_RESULTS 在 engine repo 裡"; else P "T2_RESULTS 不在 iCloud 樹也不在 repo"; fi ;;
esac
if under "$REGISTERS" "$ENGINE"; then F "REGISTERS 在 engine repo 裡：登錄表是工作檔，放 research/registers"; else P "REGISTERS 在 repo 外：$REGISTERS"; fi

say "3/9 參考資源（$RES）"
case "$RES" in
  /Volumes/*)
    vol="/Volumes/$(printf '%s' "${RES#/Volumes/}" | cut -d/ -f1)"
    if [ -d "$vol" ]; then P "外接碟 $vol 已接上"; else F "外接碟 $vol 沒接上：參考資源在那裡（Track 1 的 local.env 設定）"; fi ;;
esac
if [ -s "$REF" ]; then P "參考序列 $(basename "$REF")"; else F "找不到參考序列 $REF（Track 1：02_fetch_resources.sh fasta）"; fi
if [ -s "$REF.fai" ]; then P ".fai 索引"; else F "缺 $REF.fai"; fi
case "$REF" in *.gz) if [ -s "$REF.gzi" ]; then P ".gzi 索引（bgzip）"; else F "缺 $REF.gzi：samtools faidx $REF 會建立"; fi ;; esac
if [ -s "$GTF" ]; then
  case "$(basename "$GTF")" in *".${VEP_VERSION}."*) P "GTF $(basename "$GTF")（和 VEP 同版 ${VEP_VERSION}）" ;; *) W "GTF 檔名看不出版本 ${VEP_VERSION}：確認和 VEP cache 同一個 Ensembl release" ;; esac
else F "找不到 GTF $GTF（Track 1：02_fetch_resources.sh panel）"; fi
if [ -d "$VEP_CACHE/homo_sapiens/${VEP_VERSION}_GRCh38" ]; then
  if [ -f "$VEP_CACHE/homo_sapiens/${VEP_VERSION}_GRCh38/.mva_complete" ]; then P "VEP ${VEP_VERSION} cache 完整"
  else W "VEP cache 資料夾在，但沒有 .mva_complete 標記：Track 1 的 02 可能還沒下載完"; fi
else F "找不到 VEP ${VEP_VERSION} cache：$VEP_CACHE（Track 1：02_fetch_resources.sh vep）"; fi
cv="${CLINVAR:-$RES/clinvar.vcf.gz}"
if [ -s "$cv" ]; then P "ClinVar（11a 自我檢查用）"; else W "找不到 ClinVar：11a 自我檢查無法跑（Track 1：02_fetch_resources.sh clinvar）"; fi

say "4/9 工具"
if b="$(conda_base)"; then
  P "conda：$b"
  py="$b/envs/mva/bin/python"
  if [ -x "$py" ]; then
    if v="$("$py" -c 'import sys, yaml; print(sys.version.split()[0], "PyYAML", yaml.__version__)' 2>/dev/null)"; then P "mva 環境：Python $v"
    else F "mva 環境的 Python 沒有 PyYAML：conda install -n mva -c conda-forge pyyaml"; fi
  else F "沒有 mva 環境：先跑 Track 1 的 01_setup_mac.sh"; fi
  for t in bcftools samtools; do
    if [ -x "$b/envs/mva/bin/$t" ]; then P "$("$b/envs/mva/bin/$t" --version 2>/dev/null | head -1)"; else F "mva 環境沒有 $t"; fi
  done
  if [ -x "$b/envs/vep/bin/vep" ]; then
    if PATH="$b/envs/vep/bin:$PATH" vep --help 2>/dev/null | grep -E "ensembl-vep +: +$VEP_VERSION" >/dev/null; then P "VEP ${VEP_VERSION}"
    else W "vep --help 看不到版本 ${VEP_VERSION}：conda activate vep && vep --help | head"; fi
  else F "沒有 vep 環境：先跑 Track 1 的 01_setup_mac.sh"; fi
  if [ -x "$b/envs/mva/bin/dot" ] || command -v dot >/dev/null 2>&1; then P "graphviz（因果鏈 SVG）"
  else W "沒有 graphviz：因果鏈只會有 .mmd／.dot、沒有 SVG。安裝：conda install -n mva -c conda-forge graphviz"; fi
else
  F "找不到 conda：先跑 Track 1 的 01_setup_mac.sh"
fi

say "5/9 網路（只連公開資料庫：UniProt、AlphaFold、Europe PMC、Crossref）"
[ "${T2_PREFLIGHT_SKIP_NETWORK:-0}" = 1 ] && info "略過（T2_PREFLIGHT_SKIP_NETWORK=1）"
[ "${T2_PREFLIGHT_SKIP_NETWORK:-0}" = 1 ] || for u in "https://rest.uniprot.org/uniprotkb/P04637.json" "https://alphafold.ebi.ac.uk/api/prediction/P04637" \
         "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:24825348&format=json" \
         "https://api.crossref.org/works/10.15252/embj.201386907"; do
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$u" 2>/dev/null)"
  host="$(printf '%s' "$u" | cut -d/ -f3)"
  if [ "$code" = 200 ]; then P "$host"; else W "$host 回 ${code:-無回應}：第 12、16 步會失敗，可用 --offline 吃快取"; fi
done

say "6/9 Track 1 的輸入（第 10、11 步要用）"
if [ -s "$T1_WORK/norm.vcf.gz" ]; then
  P "norm.vcf.gz"
  if [ -s "$T1_WORK/norm.vcf.gz.tbi" ] || [ -s "$T1_WORK/norm.vcf.gz.csi" ]; then P "norm.vcf.gz 索引"; else F "norm.vcf.gz 沒有索引：conda activate mva && bcftools index -t \"$T1_WORK/norm.vcf.gz\""; fi
else F "還沒有 $T1_WORK/norm.vcf.gz：Track 1 的 run_phase1.sh（第 7 節）要先跑"; fi
if [ -s "$T1_RESULTS/run_manifest.tsv" ] && grep "08_draft" "$T1_RESULTS/run_manifest.tsv" >/dev/null 2>&1; then
  P "run_manifest.tsv 有 08_draft：$(grep 08_draft "$T1_RESULTS/run_manifest.tsv" | tail -1 | cut -f6)"
else W "run_manifest.tsv 沒有 08_draft：Track 1 還沒產生提交檔（第 10 步可用 --submission-csv 指定）"; fi
if [ -s "$T1_RESULTS/hpo_terms.tsv" ]; then P "hpo_terms.tsv"; else W "沒有 hpo_terms.tsv：第 15 步無法核對每個 HPO term 都有節點"; fi

say "7/9 engine repo（$ENGINE）"
if git -C "$ENGINE" rev-parse --git-dir >/dev/null 2>&1; then P "git repo（$(git -C "$ENGINE" log -1 --format='%h %s' 2>/dev/null | cut -c1-60)）"; else F "$ENGINE 不是 git repo"; fi
gi="$ENGINE/.gitignore"
missing=""
for pat in "config/local.env" "handoff_from_track1.yaml" "transcript_facts.yaml" "t2_variants.*" "*.vcf.gz"; do
  grep -Fx "$pat" "$gi" >/dev/null 2>&1 || missing="$missing $pat"
done
if [ -z "$missing" ]; then P ".gitignore 擋住第一階段的私有檔"; else F ".gitignore 缺：$missing（Spec 1 第 A4 步）"; fi
hook="$(git -C "$ENGINE" rev-parse --git-path hooks/pre-commit 2>/dev/null)"
case "$hook" in /*) ;; *) hook="$ENGINE/$hook" ;; esac
if [ -f "$hook" ] && grep 'mva-track2-guard' "$hook" >/dev/null 2>&1; then P "pre-commit 防護（19_public_safety.py）"
else W "還沒裝 pre-commit 防護（Spec 1 第 A4 步）"; fi
for t in fact_register.TEMPLATE.csv scenarios.TEMPLATE.yaml mechanism_graph.TEMPLATE.yaml; do
  [ -s "$ENGINE/templates/phase1/$t" ] || F "缺範本 templates/phase1/$t（bundle 沒複製完整）"
done
[ -s "$ENGINE/config/cases/$CASE_ID.yaml" ] && P "base case：config/cases/$CASE_ID.yaml" || F "找不到 config/cases/$CASE_ID.yaml"
if [ -s "$ENGINE/docs/PRIMARY_HYPOTHESIS.md" ]; then P "Spec 0 的 PRIMARY_HYPOTHESIS.md"
else W "還沒有 docs/PRIMARY_HYPOTHESIS.md（Spec 0）：第一階段可以先做，結束時再回填第 ③ 成分"; fi
if [ -f "$HOME/mva-hackathon/repo/src/triage.py" ] && [ "$ENGINE" != "$HOME/mva-hackathon/repo" ]; then
  W "~/mva-hackathon/repo 根目錄還有一份舊的 Track 2 引擎（src/、config/cases/）：以 $ENGINE 為準，不要改那份"
fi

say "8/9 資料安全"
if command -v tmutil >/dev/null 2>&1; then
  mkdir -p "$T2_RESULTS" 2>/dev/null
  if tmutil isexcluded "$T2_RESULTS" 2>/dev/null | grep Excluded >/dev/null; then P "Time Machine 不備份 $T2_RESULTS"
  else W "Time Machine 會備份 $T2_RESULTS（含座標）：tmutil addexclusion \"$T2_RESULTS\""; fi
fi
case "$MVA_ROOT" in
  "$HOME/Desktop"*|"$HOME/Documents"*|"$HOME/Library/Mobile Documents"*) F "$MVA_ROOT 在 iCloud 同步範圍" ;;
  *) P "$MVA_ROOT 不在 iCloud 同步範圍" ;;
esac

say "9/9 第一階段進度"
for f in "$T2_RESULTS/handoff_from_track1.yaml:10 交接檔" "$ENGINE/docs/transcript_facts_public.yaml:11 轉錄本事實" \
         "$T2_WORK/selftest/selftest_report.tsv:11a 自我檢查" "$ENGINE/docs/domain_map.yaml:12 結構域對映" \
         "$REGISTERS/fact_register.csv:13 事實登錄表" "$ENGINE/config/scenarios/$CASE_ID.scenarios.yaml:14 情境表" \
         "$ENGINE/docs/MECHANISM.md:15 因果鏈" "$REGISTERS/citation_check.csv:16 引用檢查"; do
  p="${f%%:*}"; label="${f#*:}"
  if [ -s "$p" ]; then info "✓ $label"; else info "· $label（還沒做）"; fi
done

echo
if [ "$nf" -gt 0 ]; then printf '✗ %s 項通過、%s 項提醒、%s 項必須先修。\n' "$np" "$nw" "$nf" >&2; exit 1; fi
printf '✓ %s 項通過、%s 項提醒。可以開始第一階段。\n' "$np" "$nw"
