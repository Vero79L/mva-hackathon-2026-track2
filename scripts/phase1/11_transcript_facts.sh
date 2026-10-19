#!/usr/bin/env bash
# 第 11 步：轉錄本層事實（Spec 1 v1.1 第 2 節）。讀交接檔的座標 → VEP 116 離線 + GTF 算術交叉檢查。
# 讀病人資料（變異座標）：在你自己的終端機跑，或用 Console（API）登入的 Claude Code 跑。全部離線。
# 輸出：$T2_RESULTS/{t2_variants.vcf, t2_variants.vep.tsv, transcript_facts.yaml}（含座標）
#       docs/transcript_facts_public.yaml（公開安全）
# 用法：bash scripts/phase1/11_transcript_facts.sh        （FORCE=1 重做）
. "$(dirname "$0")/t2lib.sh"
start_log 11_transcript_facts
mva_path
PY="$(mva_python)"

H="$T2_RESULTS/handoff_from_track1.yaml"
[ -s "$H" ] || die "缺 $H：先跑 10_handoff.py"
for f in "$REF" "$GTF"; do [ -s "$f" ] || die "找不到 $f（外接碟 DISK-2 有接上嗎？跑 00_preflight.sh 看哪一項沒過）"; done
[ -s "$REF.fai" ] || die "缺 $REF.fai：Track 1 的 02_fetch_resources.sh fasta 會建立"
command -v samtools >/dev/null 2>&1 || die "找不到 samtools：Track 1 的 mva 環境應該有（conda activate mva）"

VCF_OUT="$T2_RESULTS/t2_variants.vcf"
VEP_OUT="$T2_RESULTS/t2_variants.vep.tsv"
FACTS="$T2_RESULTS/transcript_facts.yaml"
PUBLIC="$ENGINE/docs/transcript_facts_public.yaml"

say "1/3 迷你 VCF（交接檔的變異）"
"$PY" "$P1/transcript_facts.py" mini-vcf --handoff "$H" --out "$VCF_OUT"

say "2/3 方法 A：VEP ${VEP_VERSION} 離線（上下游距離 ${VEP_DISTANCE} bp）"
if fresh "$VEP_OUT" "$VCF_OUT"; then ok "已是最新：$(basename "$VEP_OUT")"; else run_vep "$VCF_OUT" "$VEP_OUT"; fi

say "3/3 方法 B：GTF 算術 + 參考序列轉譯，並和 VEP 逐項比對"
set +e
"$PY" "$P1/transcript_facts.py" facts --handoff "$H" --vep "$VEP_OUT" --gtf "$GTF" --ref "$REF" \
  --out "$FACTS" --public "$PUBLIC" --protein-cache "$T2_WORK/public_cache"
rc=$?
set -e
if [ "$rc" = 3 ]; then
  die "交叉檢查有不一致（上面 ✗ 的項目）。依 Spec 1 第 2.7 節的順序排查；不一致沒解決前，不要用這份結果寫報告。"
elif [ "$rc" != 0 ]; then
  die "transcript_facts.py 失敗（代碼 $rc）"
fi
ok "完成。公開安全版：docs/transcript_facts_public.yaml（commit 前先跑 19_public_safety.py）"
info "下一步：python3 scripts/phase1/12_domain_map.py"
