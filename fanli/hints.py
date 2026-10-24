"""第 5 步：以最小反例为依据生成三层提示，并做泄题检查。

参考解不进入提示词：LLM 只看到题目、学生代码和已经实际运行验证过的反例。
"""
import json
import re

from . import llm

HINT_SYSTEM = """你是耐心的编程助教，面对 Python 初学者。学生的代码在一个已验证的反例上出错。
请给出三层递进提示，输出 JSON：{"L1": "...", "L2": "...", "L3": "..."}
- L1：只说明哪一类输入会让代码出错（比如空列表、全是负数、有重复），不提具体数值。
- L2：给出具体反例，对比期望输出和实际输出，引导学生自己手动模拟。
- L3：指出最可疑的代码行或逻辑，说明为什么在这个反例上出错。
严禁给出修改后的代码、完整解法或任何代码块。每层不超过 60 字。只输出 JSON。"""


def _features(args):
    """离线降级用：从反例里提取初学者能理解的输入特征。"""
    feats = []
    for a in args:
        if isinstance(a, list):
            if not a:
                feats.append("空列表")
                continue
            if len(a) == 1:
                feats.append("只有一个元素")
            if len(set(map(repr, a))) < len(a):
                feats.append("有重复元素")
            nums = [x for x in a if isinstance(x, (int, float))]
            if nums and all(x < 0 for x in nums):
                feats.append("全是负数")
            elif any(x < 0 for x in nums):
                feats.append("含有负数")
            if nums and all(x == 0 for x in nums):
                feats.append("全是 0")
    return feats or ["某些特殊输入"]


def _fmt_args(args):
    return ", ".join(repr(a) for a in args)


def offline_hints(cex, func_name):
    feats = "、".join(_features(cex["args"]))
    call = f"{func_name}({_fmt_args(cex['args'])})"
    if cex["kind"] == "error":
        l2 = f"调用 {call} 时程序报错：{cex['actual']}，而期望返回 {repr(cex['expected'])}。"
    else:
        l2 = (f"调用 {call}，期望返回 {repr(cex['expected'])}，"
              f"你的代码返回 {repr(cex['actual'])}。试着手动走一遍。")
    return {
        "L1": f"当输入{feats}时，你的代码结果不对。",
        "L2": l2,
        "L3": "检查变量的初始值，以及处理这类输入的条件分支，看它们在这个反例上是否成立。",
    }


def llm_hints(problem_text, student_code, cex, func_name):
    user = (f"题目：\n{problem_text}\n\n学生代码：\n{student_code}\n\n"
            f"已验证反例：{func_name}({_fmt_args(cex['args'])})\n"
            f"期望输出：{repr(cex['expected'])}\n"
            f"实际结果（{cex['kind']}）：{repr(cex['actual'])}")
    raw = llm.chat(HINT_SYSTEM, user, temperature=0.3)
    m = re.search(r"\{.*\}", raw, flags=re.S)
    data = json.loads(m.group(0))
    return {k: str(data[k]) for k in ("L1", "L2", "L3")}


def leak_check(hints, reference_code):
    """返回发现的问题列表；空列表表示通过。"""
    issues = []
    ref_lines = {re.sub(r"\s+", "", ln) for ln in reference_code.splitlines()}
    ref_lines = {ln for ln in ref_lines if len(ln) >= 12 and not ln.startswith("#")}
    for level, text in hints.items():
        compact = re.sub(r"\s+", "", text)
        if "```" in text or re.search(r"\bdef\s+\w+\s*\(", text):
            issues.append(f"{level} 含代码块或函数定义")
        for ln in ref_lines:
            if ln in compact:
                issues.append(f"{level} 含参考解原句: {ln}")
    return issues


def make_hints(problem_text, student_code, reference_code, cex, func_name):
    """返回 (hints, 来源, 泄题问题列表)。LLM 输出泄题时退回离线提示。"""
    if llm.available():
        try:
            hints = llm_hints(problem_text, student_code, cex, func_name)
            issues = leak_check(hints, reference_code)
            if not issues:
                return hints, "llm", []
            return offline_hints(cex, func_name), "offline(llm 泄题被拦截)", issues
        except Exception as e:  # noqa: BLE001
            return offline_hints(cex, func_name), f"offline(llm 失败: {type(e).__name__})", []
    return offline_hints(cex, func_name), "offline", []
