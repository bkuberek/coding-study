def spiral_order(matrix: list[list[int]]) -> list[int]:
    top, bottom = 0, len(matrix) - 1
    left, right = 0, len(matrix[0]) - 1
    order: list[int] = []
    while top <= bottom and left <= right:
        order.extend(matrix[top][left : right + 1])
        order.extend(matrix[r][right] for r in range(top + 1, bottom + 1))
        if top < bottom and left < right:
            # Only a ring with two rows and two columns has a bottom row and left column of its own.
            order.extend(matrix[bottom][c] for c in range(right - 1, left - 1, -1))
            order.extend(matrix[r][left] for r in range(bottom - 1, top, -1))
        top, bottom, left, right = top + 1, bottom - 1, left + 1, right - 1
    return order
