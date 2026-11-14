def interval_intersection(first_list: list[list[int]], second_list: list[list[int]]) -> list[list[int]]:
    common = []
    i = j = 0
    while i < len(first_list) and j < len(second_list):
        start = max(first_list[i][0], second_list[j][0])
        end = min(first_list[i][1], second_list[j][1])
        if start <= end:
            common.append([start, end])
        # The interval that ends first cannot meet anything later in the other list.
        if first_list[i][1] < second_list[j][1]:
            i += 1
        else:
            j += 1
    return common
