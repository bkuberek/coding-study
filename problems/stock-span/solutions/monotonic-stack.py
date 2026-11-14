class StockSpanner:
    def __init__(self) -> None:
        # (price, span) pairs; prices strictly decrease from bottom to top.
        self.stack: list[tuple[int, int]] = []

    def span(self, price: int) -> int:
        span = 1
        while self.stack and self.stack[-1][0] <= price:
            span += self.stack.pop()[1]
        self.stack.append((price, span))
        return span
