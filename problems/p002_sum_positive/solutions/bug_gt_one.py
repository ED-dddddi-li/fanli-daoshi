# 错解：条件写成大于 1，把正数 1 漏掉了（边界条件写错）
def sum_positive(nums):
    total = 0
    for x in nums:
        if x > 1:
            total += x
    return total
