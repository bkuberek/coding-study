class StockSpanner:
    def __init__(self) -> None:
        self.prices: list[int] = []

    def span(self, price: int) -> int:
        self.prices.append(price)
        day = len(self.prices) - 1
        while day > 0 and self.prices[day - 1] <= price:
            day -= 1
        return len(self.prices) - day
