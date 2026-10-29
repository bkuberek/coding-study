package stock_span

type StockSpanner struct {
	prices []int
}

func NewStockSpanner() *StockSpanner {
	return &StockSpanner{}
}

func (s *StockSpanner) Span(price int) int {
	s.prices = append(s.prices, price)
	day := len(s.prices) - 1
	for day > 0 && s.prices[day-1] <= price {
		day--
	}
	return len(s.prices) - day
}
