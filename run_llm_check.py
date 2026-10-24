"""真实 LLM 路径复跑（Harbor 追加的验证脚本，不属于原项目骨架）。

原项目的 fanli/llm.py 从 .env 读明文密钥；本次验证不使用明文密钥，而是把
llm.chat 换成通过 DeepSeek 连接器（custom.deepseek）发出的调用：凭证由连接
代理换入，本脚本和密钥互不可见。其余环节（生成器自校验、差分缩减、提示词、
泄题检查）全部走原项目代码，与在用户电脑上填 .env 后跑 run_first_check.py 等价。

用法（在项目根目录）：python run_llm_check.py problems/p001_second_largest
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fanli import llm  # noqa: E402

HELPER = os.path.expanduser("~/workspace/custom-connectors/custom.deepseek/bin/deepseek_chat.py")
_totals = {"prompt": 0, "completion": 0, "calls": 0}


def chat_via_connector(system, user, temperature=0.2):
    payload = {"system": system, "user": user, "temperature": temperature, "model": "deepseek-chat"}
    proc = subprocess.run(
        [sys.executable, HELPER],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True, text=True, timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"连接器调用失败: {proc.stderr.strip()[:300]}")
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
llm.chat = chat_via_connector
llm.model_name = lambda: "deepseek-chat"  # noqa: E731

import run_first_check  # noqa: E402

if __name__ == "__main__":
    rc = run_first_check.main(sys.argv[1] if len(sys.argv) > 1 else "problems/p001_second_largest")
    print(f"\n[LLM 用量] 调用 {_totals['calls']} 次，prompt {_totals['prompt']} tokens，"
          f"completion {_totals['completion']} tokens，合计 {_totals['prompt'] + _totals['completion']}")
    sys.exit(rc)
