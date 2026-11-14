def interval_intersection(first_list: list[list[int]], second_list: list[list[int]]) -> list[list[int]]:
    common = []
    for first_start, first_end in first_list:
        # The first interval of second_list that ends at or after first_start.
        low, high = 0, len(second_list)
        while low < high:
            middle = (low + high) // 2
            if second_list[middle][1] >= first_start:
                high = middle
            else:
                low = middle + 1
        partner = low
        while partner < len(second_list) and second_list[partner][0] <= first_end:
            common.append([max(first_start, second_list[partner][0]), min(first_end, second_list[partner][1])])
            partner += 1
    return common
