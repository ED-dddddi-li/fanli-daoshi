# 正确解：手动维护已见列表，写法与参考解不同，用来检验工具不会误报
def count_unique(nums):
    seen = []
    for x in nums:
        if x not in seen:
            seen.append(x)
    return len(seen)
