# 错解：去重后又多减了 1，结果总是少 1（差一错误）
def count_unique(nums):
    return len(set(nums)) - 1
