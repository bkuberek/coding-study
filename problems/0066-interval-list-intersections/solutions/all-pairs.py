def interval_intersection(first_list: list[list[int]], second_list: list[list[int]]) -> list[list[int]]:
    # Both lists are sorted and separate, so pairs taken in this order yield sorted output.
    common = []
    for first_start, first_end in first_list:
        for second_start, second_end in second_list:
            start, end = max(first_start, second_start), min(first_end, second_end)
            if start <= end:
                common.append([start, end])
    return common
