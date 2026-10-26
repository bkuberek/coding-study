def rotate(matrix: list[list[int]]) -> None:
    n = len(matrix)
    for layer in range(n // 2):
        last = n - 1 - layer
        for offset in range(last - layer):
            top = matrix[layer][layer + offset]
            # left -> top, bottom -> left, right -> bottom, top -> right
            matrix[layer][layer + offset] = matrix[last - offset][layer]
            matrix[last - offset][layer] = matrix[last][last - offset]
            matrix[last][last - offset] = matrix[layer + offset][last]
            matrix[layer + offset][last] = top
