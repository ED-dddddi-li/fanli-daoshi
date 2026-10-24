# 错解：排序后直接取倒数第二个，没有去重（初学者常见错误）
def second_largest(nums):
    if len(nums) < 2:
        return None
    return sorted(nums)[-2]
