# 错解：用 0 初始化最大值和次大值，全是负数时出错（初学者常见错误）
def second_largest(nums):
    if len(set(nums)) < 2:
        return None
    first = 0
    second = 0
    for x in nums:
        if x > first:
            second = first
            first = x
        elif x != first and x > second:
            second = x
    return second
