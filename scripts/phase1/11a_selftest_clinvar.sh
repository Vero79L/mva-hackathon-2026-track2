#!/usr/bin/env bash
# 第 11a 步：用公開的 ClinVar 變異檢查「方法 B（GTF 算術）」和 VEP 是否一致（Spec 1 v1.1 第 2.6 節）。
# 不碰病人資料：只讀 Track 1 下載的 ClinVar VCF、GTF、參考序列。要在第 11 步之前跑一次。
# 預設抽 400 個致病／可能致病變異（SNV 與 indel，兩股都有），一致比例要 ≥ 99%。
# 用法：bash scripts/phase1/11a_selftest_clinvar.sh [抽樣數]
. "$(dirname "$0")/t2lib.sh"
N="${1:-400}"
mkdir -p "$T2_WORK/selftest"
mva_path
PY="$(mva_python)"
CV="${CLINVAR:-$RES/clinvar.vcf.gz}"
[ -s "$CV" ] || die "找不到 ClinVar：$CV（Track 1 的 02_fetch_resources.sh clinvar）"
command -v bcftools >/dev/null 2>&1 || die "找不到 bcftools：conda activate mva"
D="$T2_WORK/selftest"

say "1/3 抽樣：ClinVar 致病／可能致病、主要染色體、SNV + 短 indel（固定亂數種子，可重現）"
# awk 數到 N 個就停；上游 bcftools 因此收到 SIGPIPE 是預期的，所以這一段暫時關掉 pipefail，下面再檢查數量
set +o pipefail
bcftools view -H -i 'INFO/CLNSIG~"athogenic" && INFO/CLNSIG!~"onflicting"' -v snps,indels "$CV" 2>/dev/null \
  | awk -F'\t' -v n="$N" 'BEGIN{srand(20261014)} $1 ~ /^([0-9]+|X|Y)$/ && length($4) <= 20 && length($5) <= 20 && $5 !~ /,/ {
      if (rand() < 0.004) { print $1 "\t" $2 "\tCV" NR "\t" $4 "\t" $5 "\t.\t.\t."; if (++k >= n) exit } }' \
  > "$D/body.tsv"
set -o pipefail
{ printf '##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n'; cat "$D/body.tsv"; } > "$D/clinvar_sample.vcf"
n="$(grep -vc '^#' "$D/clinvar_sample.vcf" || true)"
[ "${n:-0}" -ge 100 ] || die "只抽到 ${n} 個變異：ClinVar 檔案或 bcftools 有問題"
ok "$n 個變異 → $D/clinvar_sample.vcf"

say "2/3 VEP ${VEP_VERSION} 離線"
run_vep "$D/clinvar_sample.vcf" "$D/clinvar_sample.vep.tsv"

say "3/3 方法 B 和 VEP 比對"
"$PY" "$P1/transcript_facts.py" selftest --vcf "$D/clinvar_sample.vcf" --vep "$D/clinvar_sample.vep.tsv" \
  --gtf "$GTF" --ref "$REF" --report "$D/selftest_report.tsv"
info "把上面那張一致率表貼進 docs/METHODS_AND_AI.md 的「驗證」段（只含公開變異的統計，可以公開）"
