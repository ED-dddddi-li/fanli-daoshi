"""开发验证脚本（可选），不是评审入口。

评审入口是 run_first_check.py：填好 .env 后它自动走 LLM 路径，否则离线运行。
本脚本只用于开发环境里把 llm.chat 换成另一个调用实现：把环境变量
DEEPSEEK_CHAT_HELPER 指向一个可执行脚本，该脚本从 stdin 读 JSON
{"system", "user", "temperature", "model"}，向 stdout 输出 JSON
{"content", "usage": {"prompt_tokens", "completion_tokens"}}。
未设置该变量时本脚本直接退出并说明原因。

用法（在项目根目录）：DEEPSEEK_CHAT_HELPER=/path/to/helper.py python run_llm_check.py problems/p001_second_largest
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fanli import llm  # noqa: E402

HELPER = os.environ.get("DEEPSEEK_CHAT_HELPER", "")
if not HELPER:
    raise SystemExit("未设置 DEEPSEEK_CHAT_HELPER：本脚本为开发验证用，评审请直接用 run_first_check.py + .env。")
_totals = {"prompt": 0, "completion": 0, "calls": 0}


def chat_via_helper(system, user, temperature=0.2):
    payload = {"system": system, "user": user, "temperature": temperature, "model": "deepseek-chat"}
    proc = subprocess.run(
        [sys.executable, HELPER],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True, text=True, timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"调用失败: {proc.stderr.strip()[:300]}")
    data = json.loads(proc.stdout)
    usage = data.get("usage") or {}
    _totals["calls"] += 1
    _totals["prompt"] += usage.get("prompt_tokens", 0)
    _totals["completion"] += usage.get("completion_tokens", 0)
    os.makedirs("results", exist_ok=True)
    with open(os.path.join("results", "token_usage.csv"), "a", encoding="utf-8") as f:
        f.write(f"deepseek-chat,{usage.get('prompt_tokens', 0)},{usage.get('completion_tokens', 0)}\n")
    return data["content"]


llm.available = lambda: True  # noqa: E731
llm.chat = chat_via_helper
llm.model_name = lambda: "deepseek-chat"  # noqa: E731

import run_first_check  # noqa: E402

if __name__ == "__main__":
    rc = run_first_check.main(sys.argv[1] if len(sys.argv) > 1 else "problems/p001_second_largest")
    print(f"\n[LLM 用量] 调用 {_totals['calls']} 次，prompt {_totals['prompt']} tokens，"
          f"completion {_totals['completion']} tokens，合计 {_totals['prompt'] + _totals['completion']}")
    sys.exit(rc)
