def sum_positive(nums):
    total = 0
    for x in nums:
        if x > 0:
            total += x
    return total
