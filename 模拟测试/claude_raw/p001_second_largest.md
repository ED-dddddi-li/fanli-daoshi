===提交一===
```python
def second_largest(nums):
    distinct = sorted(set(nums), reverse=True)
    if len(distinct) < 2:
        return None
    return distinct[1]
```
预测：正确

===提交二===
```python
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
```
预测：错误
