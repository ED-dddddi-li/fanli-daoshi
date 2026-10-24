def sum_positive(nums):
    if max(nums) <= 0:
        return 0
    total = 0
    for n in nums:
        if n > 0:
            total = total + n
    return total
