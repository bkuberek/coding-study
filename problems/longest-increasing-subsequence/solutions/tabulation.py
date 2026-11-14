def length_of_lis(nums: list[int]) -> int:
    # ending[i] is the length of the longest increasing subsequence that ends at index i.
    ending = [1] * len(nums)
    for i in range(1, len(nums)):
        for j in range(i):
            if nums[j] < nums[i] and ending[j] + 1 > ending[i]:
                ending[i] = ending[j] + 1
    return max(ending)
