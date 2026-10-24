题目：第二大的不同值    LLM：deepseek-chat
  [生成器] 第 1 次生成: 'st.tuples(st.lists(st.integers(-1000, 1000), max_size=50))' -> 通过

== bug_init_zero.py: 判定 wrong（预期 wrong）✓  0.16s
   最小反例：second_largest([0, -1])  期望 -1  实际 0
   L1：当列表中所有不同的值都小于等于 0 时，代码会出错。
   L2：输入 [0, -1]：期望 -1，实际 0。手动模拟循环，看 first 和 second 如何变化。
   L3：first 和 second 初始化为 0，导致负数永远无法成为次大值，因为 x > second 不成立。
   提示来源：llm；泄题检查：通过

== bug_no_dedup.py: 判定 wrong（预期 wrong）✓  0.14s
   最小反例：second_largest([0, 0])  期望 None  实际 0
   L1：当列表里有重复元素、且重复值恰好占据最大位置时，代码会出错。
   L2：输入 [0, 0]：期望 None，实际返回 0。请手动排序后看看倒数第二个是什么。
   L3：sorted(nums)[-2] 没有去重；[0,0] 排序后仍是 [0,0]，倒数第二个是 0，但不同值只有一个。
   提示来源：llm；泄题检查：通过

== correct_one_pass.py: 判定 correct（预期 correct）✓  0.53s

全部判定与预期一致：是；结果已写入 results/first_check_p001_second_largest.json

[LLM 用量] 调用 3 次，prompt 1033 tokens，completion 213 tokens，合计 1246

---
命名口径（用户 2026-10-23 拍板）：模型一律按 API 实际返回写 deepseek-flash，不写 deepseek-chat。
