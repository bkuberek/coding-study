pub struct StockSpanner {
    /// `(price, span)` pairs; prices strictly decrease from bottom to top.
    stack: Vec<(i32, i32)>,
}

impl StockSpanner {
    pub fn new() -> Self {
        StockSpanner { stack: Vec::new() }
    }

    pub fn span(&mut self, price: i32) -> i32 {
        let mut span = 1;
        while let Some(&(top_price, top_span)) = self.stack.last() {
            if top_price > price {
                break;
            }
            span += top_span;
            self.stack.pop();
        }
        self.stack.push((price, span));
        span
    }
}
