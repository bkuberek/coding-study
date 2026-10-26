def largest_rectangle_area(heights: list[int]) -> int:
    best = 0
    # Indexes of bars whose heights strictly increase from bottom to top.
    rising: list[int] = []
    # One extra bar of height 0 at the end pops every bar still waiting.
    for index in range(len(heights) + 1):
        height = heights[index] if index < len(heights) else 0
        while rising and heights[rising[-1]] >= height:
            top = rising.pop()
            # The bar below `top` on the stack is lower, and so is `index` (or it is equal and
            # a later pop covers the full width): the rectangle spans the bars between them.
            left = rising[-1] if rising else -1
            best = max(best, heights[top] * (index - left - 1))
        rising.append(index)
    return best
