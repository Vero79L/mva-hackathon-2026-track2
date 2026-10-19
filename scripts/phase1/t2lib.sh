# shellcheck shell=bash
# Track 2 第一階段（Spec 1 v1.1）共用函式。每支 bash 腳本第一行：. "$(dirname "$0")/t2lib.sh"
# 相容 macOS 內建 bash 3.2 與 BSD 指令（不用 sed -i、grep -P、readlink -f、declare -A）。

set -euo pipefail

P1="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"     # engine/scripts/phase1
ENGINE="$(cd "$P1/../.." && pwd -P)"                       # engine/
RESEARCH="$(cd "$ENGINE/.." && pwd -P)"                    # mva/research/
CONF2="$ENGINE/config"

# ---------- 訊息（和 Track 1 同一套符號） ----------
say()  { printf '\n==> %s\n' "$*"; }
ok()   { printf '  ✓ %s\n' "$*"; }
info() { printf '    %s\n' "$*"; }
warn() { printf '  ! %s\n' "$*" >&2; }
die()  { printf '\n✗ %s\n' "$*" >&2; exit 1; }

# ---------- 設定：engine/config/local.env 會先讀 Track 1 的 local.env + paths.env ----------
if [ ! -f "$CONF2/local.env" ]; then
  die "缺 $CONF2/local.env。第一次先執行：cp \"$CONF2/local.env.example\" \"$CONF2/local.env\"（Spec 1 第 A3 節）"
fi
set -a
# shellcheck disable=SC1091
. "$CONF2/local.env"
: "${REGISTERS:=$RESEARCH/registers}"
: "${CASE_ID:=bub1b_mva}"
: "${PROBAND:=PROBAND01}"
: "${VEP_DISTANCE:=100000}"
set +a
export P1 ENGINE RESEARCH CONF2

# ---------- conda（和 Track 1 lib.sh 相同的搜尋順序） ----------
conda_base() {
  local d
  if [ -n "${CONDA_BASE:-}" ] && [ -f "$CONDA_BASE/etc/profile.d/conda.sh" ]; then echo "$CONDA_BASE"; return 0; fi
  for d in "$HOME/miniforge3" "$HOME/mambaforge" "$HOME/miniconda3" "$HOME/anaconda3" \
           /opt/homebrew/Caskroom/miniforge/base /usr/local/Caskroom/miniforge/base /opt/miniconda3 /opt/anaconda3; do
    if [ -f "$d/etc/profile.d/conda.sh" ]; then echo "$d"; return 0; fi
  done
  if command -v conda >/dev/null 2>&1; then conda info --base 2>/dev/null && return 0; fi
  return 1
}
has_env() { local b; b="$(conda_base)" || return 1; [ -d "$b/envs/$1" ]; }

# 用 mva 環境的 Python（PyYAML、pandas、bcftools、samtools 都在裡面）
mva_python() {
  local b
  if b="$(conda_base)" && [ -x "$b/envs/mva/bin/python" ]; then echo "$b/envs/mva/bin/python"; return 0; fi
  if python3 -c 'import yaml' >/dev/null 2>&1; then command -v python3; return 0; fi
  die "找不到有 PyYAML 的 Python：先跑 Track 1 的 01_setup_mac.sh（建立 mva 環境）"
}

# mva 環境的 bin 放到 PATH 前面（bcftools、samtools、dot）
mva_path() {
  local b
  if b="$(conda_base)" && [ -d "$b/envs/mva/bin" ]; then PATH="$b/envs/mva/bin:$PATH"; export PATH; fi
}

# ---------- 執行紀錄：log 可能含座標，所以寫在 $T2_RESULTS/logs，不在 repo ----------
start_log() {
  mkdir -p "$T2_RESULTS/logs"
  LOGFILE="$T2_RESULTS/logs/$1_$(date +%Y%m%d-%H%M%S).log"
  exec > >(tee -a "$LOGFILE") 2>&1
  say "$1 開始於 $(date '+%Y-%m-%d %H:%M:%S')（紀錄：${LOGFILE}）"
}

# fresh <輸出> <輸入...>：輸出存在、非空、而且比所有輸入新 → 回傳 0（可以跳過）。FORCE=1 一律重做。
fresh() {
  local out="$1" f
  shift
  [ "${FORCE:-0}" = 1 ] && return 1
  [ -s "$out" ] || return 1
  for f in "$@"; do
    if [ -e "$f" ] && [ "$f" -nt "$out" ]; then return 1; fi
  done
  return 0
}

# ---------- VEP（離線；和 Track 1 同一個 cache 與版本） ----------
# run_vep <輸入 VCF> <輸出 TSV>：輸出欄位固定，transcript_facts.py 依欄名讀取
VEP_FIELDS="Uploaded_variation,Location,Allele,Feature_type,Feature,BIOTYPE,SYMBOL,STRAND,MANE_SELECT,CANONICAL,Consequence,IMPACT,EXON,INTRON,cDNA_position,CDS_position,Protein_position,Amino_acids,Codons,HGVSc,HGVSp,HGVSg,DISTANCE,SIFT,PolyPhen,SWISSPROT,UNIPROT_ISOFORM"
run_vep() {
  local in="$1" out="$2" b vepbin
  b="$(conda_base)" || die "找不到 conda：先跑 Track 1 的 01_setup_mac.sh"
  vepbin="$b/envs/vep/bin"
  [ -x "$vepbin/vep" ] || die "找不到 VEP（conda 環境 vep）：先跑 Track 1 的 01_setup_mac.sh"
  [ -d "$VEP_CACHE/homo_sapiens/${VEP_VERSION}_GRCh38" ] || die "找不到 VEP ${VEP_VERSION} cache：$VEP_CACHE（外接碟 DISK-2 有接上嗎？）"
  set -- --offline --cache --dir_cache "$VEP_CACHE" --cache_version "$VEP_VERSION" --assembly GRCh38 --fasta "$REF" \
    -i "$in" -o "$out" --tab --force_overwrite --no_stats \
    --symbol --biotype --hgvs --hgvsg --mane --canonical --numbers --protein --transcript_version --uniprot \
    --sift b --polyphen b --distance "$VEP_DISTANCE" --fields "$VEP_FIELDS"
  if PATH="$vepbin:$PATH" vep "$@" --regulatory; then
    ok "VEP ${VEP_VERSION}（含調控區）→ $(basename "$out")"
  else
    warn "VEP 加 --regulatory 失敗（cache 可能沒有調控區資料），改成不含調控區再跑一次"
    PATH="$vepbin:$PATH" vep "$@" || die "VEP 執行失敗：看上面的錯誤訊息"
    ok "VEP ${VEP_VERSION}（不含調控區）→ $(basename "$out")"
  fi
}
