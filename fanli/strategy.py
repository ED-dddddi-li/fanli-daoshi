"""第 2–3 步：AI 读题写 Hypothesis 输入策略，并用参考解自校验。"""
import ast
import copy
import re

from hypothesis import HealthCheck, Phase, given, settings
from hypothesis import strategies as st

from . import llm

STRATEGY_SYSTEM = """你是 Python 测试工程师。根据编程题描述，写一个 Hypothesis 输入策略。
只输出一个 Python 表达式，不要解释，不要 import，不要代码块标记。
表达式只能使用名字 st（即 hypothesis.strategies），结果必须生成「位置参数元组」，
例如题目函数只有一个列表参数时写：st.tuples(st.lists(st.integers(-10, 10), max_size=5))
要严格遵守题目中的长度、取值范围、是否可空等约束，并覆盖边界情况。"""


def from_template(t):
    """离线降级：根据 meta.json 里人工写的输入模板生成策略。"""
    if t["type"] == "int_list":
        inner = st.lists(st.integers(t["min_value"], t["max_value"]),
                         min_size=t["min_len"], max_size=t["max_len"])
        return st.tuples(inner), "template:int_list"
    raise ValueError(f"未知模板类型: {t['type']}")


_ALLOWED_NODES = (ast.Expression, ast.Call, ast.Attribute, ast.Name, ast.Load,
                  ast.Constant, ast.keyword, ast.Tuple, ast.List, ast.UnaryOp,
                  ast.USub, ast.UAdd)


def _check_ast(tree):
    """语法白名单：只允许 st 开头的调用、字面量与关键字参数。

    光靠空 builtins 不够：st.integers.__globals__ 这类属性链仍能拿回内置函数，
    所以这里先过一遍语法树，禁止一切下划线开头的属性与非 st 的名字。
    """
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(f"表达式含不允许的语法: {type(node).__name__}")
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("_"):
                raise ValueError(f"表达式含不允许的属性: {node.attr}")
        if isinstance(node, ast.Name) and node.id != "st":
            raise ValueError(f"表达式含不允许的名字: {node.id}")


def _compile(expr):
    expr = re.sub(r"^```(?:python)?|```$", "", expr.strip(), flags=re.M).strip()
    tree = ast.parse(expr, mode="eval")
    _check_ast(tree)
    # 只暴露 st，不给内置函数，降低执行 AI 生成代码的风险
    strat = eval(expr, {"__builtins__": {}, "st": st}, {})
    if not isinstance(strat, st.SearchStrategy):
        raise TypeError("表达式没有返回 Hypothesis 策略")
    return strat, expr


def validate(strat, reference_fn, template=None, n=200):
    """用参考解跑一批生成的输入；参考解报错或样本超出题面约束都判不通过。

    注意：参考解对任意整数列表都不会报错，所以只靠试跑发现不了“过窄”的
    生成器（例如只生成正数的策略会让负数相关的错解漏网）。这里额外按元数据
    核对样本的长度与取值范围；覆盖是否充分仍需人工抽查，不能只靠本函数。
    """
    problems = []

    @settings(max_examples=n, database=None, deadline=None,
              suppress_health_check=list(HealthCheck), phases=(Phase.generate,))
    @given(strat)
    def check(args):
        if not isinstance(args, tuple):
            problems.append(f"生成的不是参数元组: {args!r}")
            raise AssertionError
        if template and template.get("type") == "int_list" and len(args) == 1:
            xs = args[0]
            bad = (not isinstance(xs, list)
                   or not (template["min_len"] <= len(xs) <= template["max_len"])
                   or any(type(x) is not int
                          or not (template["min_value"] <= x <= template["max_value"])
                          for x in xs))
            if bad:
                problems.append(f"生成样本超出题面约束: {args!r}")
                raise AssertionError
        try:
            reference_fn(*copy.deepcopy(args))
        except Exception as e:  # noqa: BLE001
            problems.append(f"参考解在输入 {args!r} 上报错: {type(e).__name__}: {e}")
            raise

    try:
        check()
    except Exception:  # noqa: BLE001
        return problems[-1] if problems else "生成器校验失败"
    return None


def build(problem_text, meta, reference_fn, max_retries=2):
    """返回 (strategy, 来源说明, 日志列表)。"""
    log = []
    if not llm.available():
        strat, src = from_template(meta["input_template"])
        log.append("未配置 LLM_API_KEY，使用人工输入模板（离线降级）")
        return strat, src, log

    feedback = ""
    for attempt in range(max_retries + 1):
        user = f"题目：\n{problem_text}\n\n函数名：{meta['func_name']}\n{feedback}"
        expr = None
        try:
            expr = llm.chat(STRATEGY_SYSTEM, user)
            strat, expr = _compile(expr)
            err = validate(strat, reference_fn, meta.get("input_template"))
        except Exception as e:  # noqa: BLE001
            err = f"表达式无法使用: {type(e).__name__}: {e}"
            expr = expr if isinstance(expr, str) else "<LLM 调用失败，未返回表达式>"
        log.append(f"第 {attempt + 1} 次生成: {expr!r} -> {'通过' if err is None else err}")
        if err is None:
            return strat, f"llm:attempt{attempt + 1}", log
        feedback = f"\n上一次的表达式：{expr}\n问题：{err}\n请修正后重新输出表达式。"

    strat, src = from_template(meta["input_template"])
    log.append("LLM 生成器多次未通过校验，退回人工输入模板")
    return strat, src, log
