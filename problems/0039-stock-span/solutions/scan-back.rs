pub struct StockSpanner {
    prices: Vec<i32>,
}

impl StockSpanner {
    pub fn new() -> Self {
        StockSpanner { prices: Vec::new() }
    }

    pub fn span(&mut self, price: i32) -> i32 {
        self.prices.push(price);
        let mut day = self.prices.len() - 1;
        while day > 0 && self.prices[day - 1] <= price {
            day -= 1;
        }
        (self.prices.len() - day) as i32
    }
}
