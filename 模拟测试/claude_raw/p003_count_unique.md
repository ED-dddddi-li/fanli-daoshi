===提交一===
```python
def count_unique(nums):
    return len(set(nums))
```
预测：正确

===提交二===
```python
def count_unique(nums):
    nums.sort()
    count = 1
    for i in range(1, len(nums)):
        if nums[i] != nums[i - 1]:
            count += 1
    return count
```
预测：错误
