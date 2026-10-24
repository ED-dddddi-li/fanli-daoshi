# 正确解：一次遍历，写法与参考解不同，用来检验工具不会误报
def second_largest(nums):
    first = None
    second = None
    for x in nums:
        if first is None or x > first:
            if first is not None:
                second = first
            first = x
        elif x != first and (second is None or x > second):
            second = x
    return second
