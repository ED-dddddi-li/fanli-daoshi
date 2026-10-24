# AI 模拟提交（Claude 生成），仅用于功能测试，非真实学生作业
def count_unique(nums):
    nums.sort()
    count = 1
    for i in range(1, len(nums)):
        if nums[i] != nums[i - 1]:
            count += 1
    return count
