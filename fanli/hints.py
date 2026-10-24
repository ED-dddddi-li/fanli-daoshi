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
    if cex["kind"] == "timeout":
        return {
            "L1": "当输入让代码运行时间过长时，你的代码结果不对。",
            "L2": f"调用 {call} 时运行超时（未缩减），期望返回 {repr(cex['expected'])}。",
            "L3": "检查循环的退出条件和输入规模，看它在这个反例上是否会一直跑下去。",
        }
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


def leak_check(hints, reference_code, student_code=""):
    """返回发现的问题列表；空列表表示通过。

    规则：参考解逐行去空白后长度不少于 8 字符的行、以及参考解里连续
    20 字符的片段，出现在提示里即判泄题；但学生代码里已经出现的片段
    不算（例如学生代码本身就写着 len(set(nums))，提示引用它不等于泄题）。
    改写后的解法、短于阈值的片段仍可能漏网，本检查只能拦原样照抄。
    """
    issues = []
    student_norm = re.sub(r"\s+", "", student_code)
    ref_lines = {re.sub(r"\s+", "", ln) for ln in reference_code.splitlines()}
    ref_lines = {ln for ln in ref_lines if len(ln) >= 8 and not ln.startswith("#")
                 and ln not in student_norm}
    ref_norm = re.sub(r"\s+", "", reference_code)
    for level, text in hints.items():
        compact = re.sub(r"\s+", "", text)
        if "```" in text or re.search(r"\bdef\s+\w+\s*\(", text):
            issues.append(f"{level} 含代码块或函数定义")
        for ln in ref_lines:
            if ln in compact:
                issues.append(f"{level} 含参考解原句: {ln}")
        for start in range(0, max(0, len(ref_norm) - 19), 6):
            frag = ref_norm[start:start + 20]
            if frag and frag in compact and frag not in student_norm:
                issues.append(f"{level} 含参考解连续片段")
                break
    return issues


def make_hints(problem_text, student_code, reference_code, cex, func_name):
    """返回 (hints, 来源, 泄题问题列表, 被拦截的 LLM 原文或 None)。

    LLM 输出泄题时退回离线提示，但被拦截的原文会随运行记录保存，
    不再像以前那样直接丢弃。
    """
    if llm.available():
        try:
            hints = llm_hints(problem_text, student_code, cex, func_name)
            issues = leak_check(hints, reference_code, student_code)
            if not issues:
                return hints, "llm", [], None
            return offline_hints(cex, func_name), "offline(llm 泄题被拦截)", issues, hints
        except Exception as e:  # noqa: BLE001
            return offline_hints(cex, func_name), f"offline(llm 失败: {type(e).__name__})", [], None
    return offline_hints(cex, func_name), "offline", [], None
