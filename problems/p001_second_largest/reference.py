def second_largest(nums):
    distinct = sorted(set(nums))
    if len(distinct) < 2:
        return None
    return distinct[-2]
