"""模拟提交复跑：对 sim_submissions/ 下的 6 份 AI 模拟提交重新跑差分判定，
并与 模拟测试/判定结果.json 里记录的判定逐份比对。

用法（在项目根目录）：python run_sim_check.py
"""
import importlib.util
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fanli import difftest, strategy  # noqa: E402


def load_fn(path, name):
    spec = importlib.util.spec_from_file_location("reference", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, name)


def main():
    problems = {}
    for pid in sorted(os.listdir("problems")):
        meta_path = os.path.join("problems", pid, "meta.json")
        if os.path.exists(meta_path):
            with open(meta_path, encoding="utf-8") as f:
                problems[json.load(f)["id"]] = os.path.join("problems", pid)
    expected = {}
    jpath = os.path.join("模拟测试", "判定结果.json")
    if os.path.exists(jpath):
        with open(jpath, encoding="utf-8") as f:
            data = json.load(f)
        for pid, rows in data.items():
            if isinstance(rows, list):
                for r in rows:
                    expected[r["file"]] = r["tool_verdict"]
    ok = True
    for name in sorted(os.listdir("sim_submissions")):
        if not name.endswith(".py"):
            continue
        pid = name.rsplit("_", 1)[0]
        pdir = problems.get(pid)
        if pdir is None:
            print(f"{name}: 找不到对应题目 {pid}")
            ok = False
            continue
        with open(os.path.join(pdir, "meta.json"), encoding="utf-8") as f:
            meta = json.load(f)
        ref = load_fn(os.path.join(pdir, "reference.py"), meta["func_name"])
        strat, _ = strategy.from_template(meta["input_template"])
        cex = difftest.find_counterexample(strat, ref, os.path.join("sim_submissions", name),
                                           meta["func_name"])
        verdict = "correct" if cex is None else "wrong"
        want = expected.get(name)
        match = want is None or want == verdict
        ok &= match
        cex_str = "" if cex is None else f" 反例 {cex['args']} 期望 {cex['expected']!r} 实际 {cex['actual']!r}"
        print(f"{name}: 判定 {verdict}（记录 {want}）{'✓' if match else '✗ 不符'}{cex_str}")
    print(f"\n模拟提交复跑与记录一致：{'是' if ok else '否'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
