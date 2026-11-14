def three_sum(nums: list[int]) -> list[list[int]]:
    values = sorted(nums)
    n = len(values)
    triples = []
    for i in range(n - 2):
        if values[i] > 0:
            break
        if i > 0 and values[i] == values[i - 1]:
            continue
        left, right = i + 1, n - 1
        while left < right:
            total = values[i] + values[left] + values[right]
            if total < 0:
                left += 1
            elif total > 0:
                right -= 1
            else:
                triples.append([values[i], values[left], values[right]])
                left += 1
                right -= 1
                while left < right and values[left] == values[left - 1]:
                    left += 1
    return triples
