===提交一===
```python
def sum_positive(nums):
    total = 0
    for x in nums:
        if x > 0:
            total += x
    return total
```
预测：正确

===提交二===
```python
def sum_positive(nums):
    if max(nums) <= 0:
        return 0
    total = 0
    for n in nums:
        if n > 0:
            total = total + n
    return total
```
预测：错误
