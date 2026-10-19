#!/usr/bin/env bash
# Track 2 第一階段的執行順序（Spec 1 v1.1）。分成兩天：
#   day1：00 檢查 → 11a 自我檢查（公開 ClinVar）→ 10 交接 → 11 轉錄本事實 → 12 結構域對映
#         之後停下來：你填 fact_register.csv（第 4 節）
#   day2：13 規則檢查 → 14 三情境 → 15 因果鏈 → 16 引用驗證 → 18 case 檔 v2 → 19 公開安全
# 任一步失敗就停；修好後重跑同一個指令（已完成而輸入沒變的步驟，各腳本自己會跳過或可安全重跑）。
# 第 10 步會讀 Track 1 的提交檔與 VCF：在你自己的終端機跑 day1，或用 Console（API）登入的 Claude Code。
# 用法：bash scripts/phase1/run_t2_phase1.sh day1 [-- 10_handoff 的參數，例如 --match full --rank-points 100 --f-max 1]
#       bash scripts/phase1/run_t2_phase1.sh day2
. "$(dirname "$0")/t2lib.sh"
which="${1:-}"
shift || true
[ "${1:-}" = "--" ] && shift
mva_path
PY="$(mva_python)"
run() {   # run <名稱> <指令...>
  local name="$1"
  shift
  say "$name"
  "$@" || die "$name 失敗：修好後重跑 run_t2_phase1.sh $which"
}

case "$which" in
  day1)
    run "00 開工前檢查" bash "$P1/00_preflight.sh"
    if [ -s "$T2_WORK/selftest/selftest_report.tsv" ] && [ "${FORCE:-0}" != 1 ]; then
      ok "11a 自我檢查已做過（FORCE=1 重做）"
    else
      run "11a 自我檢查：方法 B vs VEP（公開 ClinVar 變異）" bash "$P1/11a_selftest_clinvar.sh"
    fi
    if [ -s "$T2_RESULTS/handoff_from_track1.yaml" ] && [ "${FORCE:-0}" != 1 ]; then
      ok "10 交接檔已存在（要重做：FORCE=1，或 python3 scripts/phase1/10_handoff.py --force …）"
    else
      force_arg=""
      if [ "${FORCE:-0}" = 1 ]; then force_arg="--force"; fi
      # ${@+"$@"}：macOS 內建 bash 3.2 在 set -u 下沒有參數時的安全寫法
      run "10 Track 1 → Track 2 交接" "$PY" "$P1/10_handoff.py" $force_arg ${@+"$@"}
    fi
    run "11 轉錄本層事實（VEP + GTF 交叉檢查）" bash "$P1/11_transcript_facts.sh"
    run "12 蛋白質結構域對映" "$PY" "$P1/12_domain_map.py"
    run "19 公開安全檢查（第一階段輸出）" "$PY" "$P1/19_public_safety.py"
    say "day1 完成。接下來是人工的部分（Spec 1 第 4 節）："
    info "1) $PY scripts/phase1/13_check_register.py --init     ← 建立 fact_register.csv（在 research/registers）"
    info "2) 依第 4.3 節填登錄表；寫完跑 13，直到 R1–R6 全部通過"
    info "3) 明天：bash scripts/phase1/run_t2_phase1.sh day2"
    ;;
  day2)
    run "13 事實登錄表規則檢查" "$PY" "$P1/13_check_register.py"
    run "14 三情境 case 檔" "$PY" "$P1/14_build_scenarios.py" --run-engine
    run "15 因果鏈" "$PY" "$P1/15_mechanism_graph.py"
    run "13 再檢查一次（因果鏈與情境表引用的 fact_id）" "$PY" "$P1/13_check_register.py"
    run "16 引用驗證" "$PY" "$P1/16_verify_citations.py" --include-uniprot
    run "18 case 檔 v2 核對與來源雜湊" "$PY" "$P1/18_case_provenance.py" --run-engine
    run "19 公開安全檢查（第一階段輸出）" "$PY" "$P1/19_public_safety.py"
    say "day2 完成。最後兩件人工的事（Spec 1 第 10 節）："
    info "1) 打開 research/registers/citation_check.csv，title_check = manual 的逐列對標題"
    info "2) 回頭改 docs/PRIMARY_HYPOTHESIS.md 第 ③ 成分，然後 git add（只加第 10.3 節列的檔案）"
    ;;
  *)
    die "用法：bash scripts/phase1/run_t2_phase1.sh day1|day2"
    ;;
esac
