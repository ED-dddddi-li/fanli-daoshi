# AI 模拟提交（Claude 生成），仅用于功能测试，非真实学生作业
def sum_positive(nums):
    if max(nums) <= 0:
        return 0
    total = 0
    for n in nums:
        if n > 0:
            total = total + n
    return total
