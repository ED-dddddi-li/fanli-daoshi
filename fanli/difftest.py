"""第 4 步：Hypothesis 差分测试，发现不一致后自动缩减到最小反例。"""
import copy
import json

from hypothesis import HealthCheck, given, settings

from .sandbox import StudentRunner


def _norm(x):
    return json.loads(json.dumps(x, default=repr))


class _Timeout(BaseException):
    """超时不参与缩减：每次重试都要等满超时，缩减会拖很久，所以直接停止并报告当前输入。"""


def find_counterexample(strat, reference_fn, student_path, func_name, max_examples=500, attempts=3):
    """返回 None（未发现问题）或反例字典 {args, expected, actual, kind}。

    随机搜索有漏检概率（实测：只在输入含元素 1 时才出错的解，单轮 300 个
    样本曾漏检），所以默认独立跑 attempts 轮，任一轮发现不一致即返回；
    全部轮次都通过才判未发现问题。超时不重试（每轮都要等满超时，代价太高）。
    """
    runner = StudentRunner(student_path, func_name)
    try:
        for _ in range(attempts):
            last = {}

            @settings(max_examples=max_examples, database=None, deadline=None,
                      suppress_health_check=list(HealthCheck))
            @given(strat)
            def prop(args):
                expected = _norm(reference_fn(*copy.deepcopy(args)))
                status, actual = runner.call(args)
                if status == "ok" and actual == expected:
                    return
                if status == "timeout":
                    last.clear()
                    last.update(args=_norm(list(args)), expected=expected, kind="timeout",
                                actual="运行超时（未缩减）")
                    raise _Timeout
                # Hypothesis 缩减结束后会最后重放一次最小反例，所以 last 里留下的就是最小反例
                last.clear()
                last.update(args=_norm(list(args)), expected=expected, kind=status, actual=actual)
                raise AssertionError("mismatch")

            try:
                prop()
            except (AssertionError, _Timeout):
                return dict(last)
        return None
    finally:
        runner.close()
