#!/usr/bin/env bash
# 用合成資料測試 Track 2 第一階段的程式（不需要比賽資料、VEP、網路；約 5 秒）。
# 用法：bash tests/phase1/run_tests.sh        預期：Ran 79 tests … OK
# 需要 PyYAML：有 conda 的 mva 環境就自動用它。graphviz 有裝的話會順便測 SVG。
set -euo pipefail
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1
here="$(cd "$(dirname "$0")" && pwd -P)"
py=python3
for b in "$HOME/miniforge3" "$HOME/mambaforge" "$HOME/miniconda3" "$HOME/anaconda3"; do
  if [ -x "$b/envs/mva/bin/python" ]; then py="$b/envs/mva/bin/python"; PATH="$b/envs/mva/bin:$PATH"; break; fi
done
"$py" -c 'import yaml' >/dev/null 2>&1 || { echo "需要 PyYAML：先跑 Track 1 的 01_setup_mac.sh（或 conda activate mva）" >&2; exit 1; }
cd "$here"
exec "$py" -m unittest -v test_transcript_facts test_phase1_steps test_robustness test_manifest_gate
