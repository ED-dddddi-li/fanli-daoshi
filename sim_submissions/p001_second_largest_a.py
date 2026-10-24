# AI 模拟提交（Claude 生成），仅用于功能测试，非真实学生作业
def second_largest(nums):
    distinct = sorted(set(nums), reverse=True)
    if len(distinct) < 2:
        return None
    return distinct[1]
