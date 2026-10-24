"""离线自测：不调用真实 API，用假的 LLM 回复检验各环节。运行：python -m pytest -q tests"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fanli import difftest, hints, llm, strategy  # noqa: E402

PROBLEM = "problems/p001_second_largest"


def _ref(nums):
    d = sorted(set(nums))
    return None if len(d) < 2 else d[-2]


def test_strategy_retry_on_bad_generator(monkeypatch):
    replies = iter([
        "st.tuples(st.integers())",  # 参数不是列表，参考解 set(int) 报错，应被拦下
        "st.tuples(st.lists(st.integers(-1000, 1000), max_size=50))",
    ])
    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(llm, "chat", lambda *a, **k: next(replies))
    meta = {"func_name": "second_largest", "input_template": {"type": "int_list", "min_len": 0,
            "max_len": 50, "min_value": -1000, "max_value": 1000}}
    _, src, log = strategy.build("题目", meta, _ref, max_retries=2)
    assert src == "llm:attempt2"
    assert "参考解在输入" in log[0]


def test_generator_cannot_use_builtins():
    try:
        strategy._compile("__import__('os')")
    except Exception:  # noqa: BLE001
        return
    raise AssertionError("应当拒绝使用内置函数")


def test_timeout_is_reported_as_wrong():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write("def second_largest(nums):\n    while True:\n        pass\n")
    strat, _ = strategy.from_template({"type": "int_list", "min_len": 0, "max_len": 5,
                                       "min_value": -5, "max_value": 5})
    cex = difftest.find_counterexample(strat, _ref, f.name, "second_largest", max_examples=5)
    os.unlink(f.name)
    assert cex is not None and cex["kind"] == "timeout"


def test_leak_check_blocks_reference_code():
    ref = open(os.path.join(PROBLEM, "reference.py"), encoding="utf-8").read()
    bad = {"L1": "a", "L2": "b", "L3": "改成 distinct = sorted(set(nums)) 就行"}
    assert hints.leak_check(bad, ref)
    assert not hints.leak_check({"L1": "注意重复元素", "L2": "试试 [0, 0]", "L3": "排序后没去重"}, ref)
