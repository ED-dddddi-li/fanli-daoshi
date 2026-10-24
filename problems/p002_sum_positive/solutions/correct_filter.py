# 正确解：生成器表达式过滤，写法与参考解不同，用来检验工具不会误报
def sum_positive(nums):
    return sum(x for x in nums if x > 0)
