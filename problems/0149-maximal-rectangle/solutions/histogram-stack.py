def maximal_rectangle(matrix: list[list[str]]) -> int:
    # heights[c] counts the consecutive ones in column c ending at the current row.
    heights = [0] * len(matrix[0])
    best = 0
    for row in matrix:
        for c, cell in enumerate(row):
            heights[c] = heights[c] + 1 if cell == "1" else 0
        best = max(best, _largest_in_histogram(heights))
    return best


def _largest_in_histogram(heights: list[int]) -> int:
    best = 0
    # Indexes of bars whose heights strictly increase from bottom to top.
    rising: list[int] = []
    # One extra bar of height 0 at the end pops every bar still waiting.
    for index in range(len(heights) + 1):
        height = heights[index] if index < len(heights) else 0
        while rising and heights[rising[-1]] >= height:
            top = rising.pop()
            left = rising[-1] if rising else -1
            best = max(best, heights[top] * (index - left - 1))
        rising.append(index)
    return best
