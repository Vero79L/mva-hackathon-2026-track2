"""Track 2 第一階段（Spec 1 v1.1）共用工具：讀設定、路徑、YAML、雜湊、訊息。

只用 Python 標準函式庫 + PyYAML，Python 3.9 以上（Track 1 的 mva 環境是 3.11）。
所有腳本都從 engine 根目錄的相對位置找檔案，從哪個資料夾執行都可以。
"""
# Make stdout/stderr UTF-8 regardless of the machine's locale: this repo is read and run by
# reviewers on systems where the preferred encoding may be ASCII, and a crash while *printing*
# a result is still a failed reproduction.
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

import datetime
import hashlib
import os
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - 只有在錯的 Python 執行時才會發生
    sys.exit("需要 PyYAML：先 conda activate mva（或 pip install pyyaml==6.0.3）再跑。")

SCRIPTS = Path(__file__).resolve().parent          # engine/scripts/phase1
ENGINE = SCRIPTS.parents[1]                         # engine/
RESEARCH = ENGINE.parent                            # mva/research/

# 會出現在 os.environ 的設定（給 --show-config 用）
CONFIG_KEYS = ["MVA_ROOT", "RES", "REF", "GTF", "VEP_VERSION", "VEP_CACHE", "CLINVAR", "T1_WORK", "T1_RESULTS",
               "T2_RESULTS", "T2_WORK", "REGISTERS", "CASE_ID", "GENE", "VEP_DISTANCE", "PROBAND"]


# ---------- 訊息（和 Track 1 的 lib.sh 同一套符號） ----------
def say(msg):
    print(f"\n==> {msg}", flush=True)


def ok(msg):
    print(f"  ✓ {msg}", flush=True)


def info(msg):
    print(f"    {msg}", flush=True)


def warn(msg):
    print(f"  ! {msg}", file=sys.stderr, flush=True)


def die(msg, code=1):
    print(f"\n✗ {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


# ---------- 設定 ----------
def load_env(required=(), envfile=None):
    """讀 engine/config/local.env（它會先讀 Track 1 的 local.env + paths.env），寫進 os.environ 並回傳 dict。

    用 bash 讀檔（set -a），所以 `: "${X:=...}"` 的寫法、Track 1 的外接碟設定都會生效；
    執行前已經 export 的同名變數優先（bash 子程序繼承目前的環境）。
    """
    envfile = Path(envfile or os.environ.get("T2_ENV_FILE") or ENGINE / "config" / "local.env")
    if not envfile.exists():
        die(f"缺 {envfile}。第一次先執行：cp config/local.env.example config/local.env（見 Spec 1 第 A3 節）")
    # 讀完設定後由同一個 Python 把環境用 NUL 分隔印出來（不用 `env -0`：macOS 的 BSD env 不一定支援）
    dump = "import os, sys; sys.stdout.buffer.write(b'\\0'.join(k + b'=' + v for k, v in os.environb.items()))"
    proc = subprocess.run(["bash", "-c", 'set -a; . "$1" >/dev/null || exit 3; exec "$2" -c "$3"', "_", str(envfile),
                           sys.executable, dump], capture_output=True)
    if proc.returncode != 0:
        die(f"讀 {envfile} 失敗：{proc.stderr.decode(errors='replace').strip()}")
    env = {}
    for item in proc.stdout.decode(errors="replace").split("\0"):
        if "=" in item:
            k, v = item.split("=", 1)
            env[k] = v
    env.setdefault("ENGINE", str(ENGINE))
    env.setdefault("RESEARCH", str(RESEARCH))
    env.setdefault("REGISTERS", str(RESEARCH / "registers"))
    env.setdefault("CASE_ID", "bub1b_mva")
    env.setdefault("PROBAND", "PROBAND01")
    os.environ.update(env)
    missing = [k for k in required if not env.get(k)]
    if missing:
        die("設定缺這些變數：" + "、".join(missing) + f"（檢查 {envfile}）")
    return env


def path(key, env=None):
    """設定裡的路徑（展開 ~ 與變數）。"""
    v = (env or os.environ).get(key, "")
    if not v:
        die(f"設定缺 {key}")
    return Path(os.path.expandvars(os.path.expanduser(v)))


# ---------- 檔案 ----------
def read_yaml(p):
    p = Path(p)
    if not p.exists():
        die(f"找不到 {p}")
    try:
        with open(p, encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except yaml.YAMLError as ex:
        die(f"{p} 不是合法的 YAML：{ex}")


def write_yaml(p, doc, header=None):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=120)
    with open(p, "w", encoding="utf-8") as fh:
        if header:
            fh.write(header.rstrip("\n") + "\n")
        fh.write(text)
    return p


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def today():
    return datetime.date.today().isoformat()


def is_under(child, parent):
    try:
        Path(child).resolve().relative_to(Path(parent).resolve())
        return True
    except ValueError:
        return False


ICLOUD_MARKERS = ("Library/Mobile Documents", "Claude-MyBrain-Professional", "opportunity-quest")


def assert_private_location(p, what):
    """含座標或基因型的輸出只能放在 ~/mva-hackathon 底下，不能在 iCloud 樹或 engine repo 裡。"""
    s = str(Path(p).resolve())
    if is_under(p, ENGINE) or any(m in s for m in ICLOUD_MARKERS):
        die(f"{what} 不能寫到 {p}：這個位置會進 git 或被 iCloud 同步。把 T2_RESULTS 設在 ~/mva-hackathon/results/track2。")
