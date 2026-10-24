# AI 模拟提交（Claude 生成），仅用于功能测试，非真实学生作业
def second_largest(nums):
    first = -1
    second = -1
    for n in nums:
        if n > first:
            second = first
            first = n
        elif n > second and n != first:
            second = n
    if second == -1:
        return None
    return second
