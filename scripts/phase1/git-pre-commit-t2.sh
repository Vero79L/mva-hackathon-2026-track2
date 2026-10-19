#!/usr/bin/env bash
# mva-track2-guard：engine repo 的 pre-commit 防護（Spec 1 v1.1 第 A4 步安裝到 .git/hooks/pre-commit）。
# 每次 commit 前對暫存區跑 19_public_safety.py --staged：有基因體座標、VCF 列、私有檔、超過 5 MB 的檔就擋下。
# 確定要提交的特例：把完全相同的字串加進 config/public_safety_allow.txt（寫理由），不要用 --no-verify 繞過。
root="$(git rev-parse --show-toplevel)"
py=python3
for b in "$HOME/miniforge3" "$HOME/mambaforge" "$HOME/miniconda3" "$HOME/anaconda3"; do
  if [ -x "$b/envs/mva/bin/python" ]; then py="$b/envs/mva/bin/python"; break; fi
done
exec "$py" "$root/scripts/phase1/19_public_safety.py" --staged
