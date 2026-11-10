def find_missing_and_duplicates(nums: list[int]) -> list[list[int]]:
    n = len(nums)
    for i in range(n):
        # Swap nums[i] to its home index nums[i] - 1 until the home already holds that value.
        # Comparing with the home, not with i, is what stops the loop on a repeated value.
        while nums[nums[i] - 1] != nums[i]:
            home = nums[i] - 1
            nums[i], nums[home] = nums[home], nums[i]

    # Every value that occurs now sits at its home. A slot that holds another value is
    # either the home of a missing value or a spare copy of a value that is home elsewhere.
    # A negative sign on a home marks that its value has a spare copy.
    missing: list[int] = []
    for i in range(n):
        if abs(nums[i]) == i + 1:
            continue
        missing.append(i + 1)
        spare = nums[i]
        nums[spare - 1] = -spare

    # The marks are read in index order, so the duplicates come out sorted too.
    duplicated = [value for value in range(1, n + 1) if nums[value - 1] < 0]
    return [missing, duplicated]
