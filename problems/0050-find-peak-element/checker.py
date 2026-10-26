"""Accept any index that is a peak of nums."""


def check(case_input: dict, output: object, expected: object | None) -> str | None:
    nums = case_input["nums"]
    if not isinstance(output, int) or isinstance(output, bool):
        return f"expected an index, got {output!r}"
    if not 0 <= output < len(nums):
        return f"index {output} is outside the array of length {len(nums)}"
    value = nums[output]
    if output > 0 and nums[output - 1] >= value:
        return f"index {output} (value {value}) does not beat its left neighbor {nums[output - 1]}"
    if output < len(nums) - 1 and nums[output + 1] >= value:
        return f"index {output} (value {value}) does not beat its right neighbor {nums[output + 1]}"
    return None
