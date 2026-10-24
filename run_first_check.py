"""首验脚本：对一道题下的所有学生代码跑完整流程，并核对预期判定。

用法：python run_first_check.py problems/p001_second_largest
"""
import importlib.util
import json
import os
import sys
import time

from fanli import difftest, hints, llm, strategy


def load_fn(path, name):
    spec = importlib.util.spec_from_file_location("reference", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, name)


def main(problem_dir):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    meta = json.load(open(os.path.join(problem_dir, "meta.json"), encoding="utf-8"))
    problem_text = open(os.path.join(problem_dir, "problem.md"), encoding="utf-8").read()
    ref_path = os.path.join(problem_dir, "reference.py")
    reference_code = open(ref_path, encoding="utf-8").read()
    reference_fn = load_fn(ref_path, meta["func_name"])

    print(f"题目：{meta['title']}    LLM：{llm.model_name() if llm.available() else '未配置（离线降级）'}")
    strat, src, log = strategy.build(problem_text, meta, reference_fn)
    for line in log:
        print("  [生成器]", line)

    records, all_match = [], True
    sol_dir = os.path.join(problem_dir, "solutions")
    for name in sorted(os.listdir(sol_dir)):
        if not name.endswith(".py"):
            continue
        path = os.path.join(sol_dir, name)
        t0 = time.time()
        cex = difftest.find_counterexample(strat, reference_fn, path, meta["func_name"])
        verdict = "correct" if cex is None else "wrong"
        want = meta.get("expected_verdicts", {}).get(name)
        match = want is None or want == verdict
        all_match &= match
        rec = {"solution": name, "verdict": verdict, "expected_verdict": want, "match": match,
               "strategy_source": src, "seconds": round(time.time() - t0, 2), "counterexample": cex}
        print(f"\n== {name}: 判定 {verdict}（预期 {want}）{'✓' if match else '✗ 不符'}  {rec['seconds']}s")
        if cex:
            code = open(path, encoding="utf-8").read()
            h, hsrc, issues = hints.make_hints(problem_text, code, reference_code, cex, meta["func_name"])
            rec.update(hints=h, hint_source=hsrc, leak_issues=issues)
            print(f"   最小反例：{meta['func_name']}({', '.join(repr(a) for a in cex['args'])})"
                  f"  期望 {cex['expected']!r}  实际 {cex['actual']!r}")
            for k in ("L1", "L2", "L3"):
                print(f"   {k}：{h[k]}")
            print(f"   提示来源：{hsrc}；泄题检查：{'通过' if not issues else issues}")
        records.append(rec)

    os.makedirs("results", exist_ok=True)
    out = os.path.join("results", f"first_check_{meta['id']}.json")
    json.dump({"problem": meta["id"], "strategy_log": log, "records": records},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n全部判定与预期一致：{'是' if all_match else '否'}；结果已写入 {out}")
    return 0 if all_match else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "problems/p001_second_largest"))
