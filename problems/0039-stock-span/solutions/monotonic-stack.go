package stock_span

// entry is a price and the number of consecutive days, ending on it, that it covers.
type entry struct {
	price, span int
}

type StockSpanner struct {
	// Prices strictly decrease from bottom to top.
	stack []entry
}

func NewStockSpanner() *StockSpanner {
	return &StockSpanner{}
}

func (s *StockSpanner) Span(price int) int {
	span := 1
	for len(s.stack) > 0 && s.stack[len(s.stack)-1].price <= price {
		span += s.stack[len(s.stack)-1].span
		s.stack = s.stack[:len(s.stack)-1]
	}
	s.stack = append(s.stack, entry{price, span})
	return span
}
